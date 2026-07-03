"""
SMS reader — pure-Python transaction capture from the SMS inbox.

No Java is needed here: on Android we query the system SMS content provider
(content://sms/inbox) through pyjnius on a timer and feed new messages into
the notification/transaction pipeline. Bank and UPI apps send transaction
alerts by SMS, so this catches them without any custom service.

On desktop this is inert.
"""

from kivy.utils import platform
from kivy.clock import Clock


POLL_INTERVAL_SECONDS = 5


class SmsReader:

    def __init__(self, notification_service):
        self.notification_service = notification_service
        self._event = None
        self._last_id = -1
        self._resolver = None
        self._uri = None

    def start(self):
        if platform != "android":
            print("[SmsReader] Not on Android — SMS reading disabled")
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            self._resolver = activity.getContentResolver()
            self._uri = Uri.parse("content://sms/inbox")
            # Skip the existing history: record the current newest id so we
            # only process messages that arrive after the app starts.
            self._last_id = self._current_max_id()
            self._event = Clock.schedule_interval(self._poll, POLL_INTERVAL_SECONDS)
            print("[SmsReader] Started (last_id=%s)" % self._last_id)
        except Exception as e:
            print("[SmsReader] Failed to start: %s" % e)

    def stop(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _current_max_id(self):
        cursor = None
        try:
            cursor = self._resolver.query(self._uri, None, None, None, "_id DESC")
            if cursor is not None and cursor.moveToFirst():
                idx = cursor.getColumnIndex("_id")
                if idx >= 0:
                    return cursor.getInt(idx)
        except Exception:
            pass
        finally:
            if cursor is not None:
                cursor.close()
        return -1

    def _poll(self, dt):
        cursor = None
        try:
            # _last_id is an int we control, so inlining it is injection-safe.
            selection = "_id > %d" % self._last_id
            cursor = self._resolver.query(self._uri, None, selection, None, "_id ASC")
            if cursor is None:
                return
            idx_id = cursor.getColumnIndex("_id")
            idx_body = cursor.getColumnIndex("body")
            idx_addr = cursor.getColumnIndex("address")
            while cursor.moveToNext():
                mid = cursor.getInt(idx_id) if idx_id >= 0 else 0
                body = cursor.getString(idx_body) if idx_body >= 0 else ""
                addr = cursor.getString(idx_addr) if idx_addr >= 0 else ""
                if mid > self._last_id:
                    self._last_id = mid
                if body:
                    # Reuse the same pipeline as notifications; the sender is
                    # passed as the "package" so the source is recorded.
                    self.notification_service.on_notification_received(body, addr)
        except Exception as e:
            # Most commonly READ_SMS not granted yet — try again next tick.
            print("[SmsReader] poll skipped: %s" % e)
        finally:
            if cursor is not None:
                cursor.close()
