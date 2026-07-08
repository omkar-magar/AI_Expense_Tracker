"""
SMS reader — pure-Python transaction capture from the SMS inbox.

No Java is needed here: on Android we query the system SMS content provider
(content://sms/inbox) through pyjnius on a timer and feed new messages into
the notification/transaction pipeline. Bank and UPI apps send transaction
alerts by SMS, so this catches them without any custom service.

The last-seen message id is PERSISTED (settings key 'sms_last_id'), so messages
that arrive while the app is closed are picked up on the next launch instead of
being skipped. Only the very first run skips pre-existing history.

On desktop this is inert.
"""

from kivy.utils import platform
from kivy.clock import Clock

from database.queries import get_setting, set_setting


POLL_INTERVAL_SECONDS = 5
LAST_ID_SETTING = "sms_last_id"


class SmsReader:

    def __init__(self, notification_service, db=None):
        self.notification_service = notification_service
        self.db = db
        self._event = None
        self._last_id = -1
        self._resolver = None
        self._uri = None

    def setup(self) -> bool:
        """Initialise the content-resolver + resume point. Shared by the
        in-app Clock loop (start) and the background service loop. Returns
        True if ready to poll."""
        if platform != "android":
            print("[SmsReader] Not on Android — SMS reading disabled")
            return False
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            self._resolver = activity.getContentResolver()
            self._uri = Uri.parse("content://sms/inbox")

            persisted = self._load_last_id()
            if persisted is None:
                # First ever run: skip existing history so we don't import the
                # whole inbox — but remember where we started.
                self._last_id = self._current_max_id()
                self._save_last_id(self._last_id)
            else:
                # Resume from where we left off; messages received while the app
                # was closed (_id > persisted) get processed on this poll.
                self._last_id = persisted
            return True
        except Exception as e:
            print("[SmsReader] setup failed: %s" % e)
            return False

    def poll_once(self):
        """Run one poll pass (for the headless background service loop)."""
        self._poll(0)

    def start(self):
        """Set up and schedule polling on Kivy's Clock (in-app, foreground)."""
        if not self.setup():
            return
        self._event = Clock.schedule_interval(self._poll, POLL_INTERVAL_SECONDS)
        print("[SmsReader] Started (last_id=%s)" % self._last_id)

    def stop(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _load_last_id(self):
        if self.db is None:
            return None
        val = get_setting(self.db, LAST_ID_SETTING)
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _save_last_id(self, value):
        if self.db is not None:
            set_setting(self.db, LAST_ID_SETTING, str(value))

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
        advanced = False
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
                    advanced = True
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
        # Persist progress so a restart resumes instead of skipping messages.
        if advanced:
            self._save_last_id(self._last_id)
