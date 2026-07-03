"""
Notification bridge — receives UPI app notifications captured by the Java
NotificationListenerService and feeds them into the transaction pipeline.

How it works:
  Android only lets the OS instantiate a NotificationListenerService, so a
  tiny Java class (java/com/expensetracker/NotificationListener.java)
  is required. That class does nothing but append each relevant notification
  to a queue file in the app's private files dir. This Python bridge polls
  that file on a timer and processes new lines — this avoids Android 13+
  runtime-broadcast-receiver restrictions entirely.

  Queue line format (one per notification):  <package>\t<body>

On desktop this is inert; use the dashboard "Simulate" button instead.
"""

import os

from kivy.utils import platform
from kivy.clock import Clock


QUEUE_FILENAME = "notif_queue.txt"
POLL_INTERVAL_SECONDS = 2


class NotificationBridge:

    def __init__(self, notification_service):
        self.notification_service = notification_service
        self._event = None
        self._queue_path = None

    def start(self):
        if platform != "android":
            print("[NotificationBridge] Not on Android — use Simulate for testing")
            return
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            files_dir = activity.getFilesDir().getAbsolutePath()
            self._queue_path = os.path.join(files_dir, QUEUE_FILENAME)
            self._event = Clock.schedule_interval(self._drain_queue, POLL_INTERVAL_SECONDS)
            print("[NotificationBridge] Started, watching %s" % self._queue_path)
        except Exception as e:
            print("[NotificationBridge] Failed to start: %s" % e)

    def stop(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _drain_queue(self, dt):
        if not self._queue_path or not os.path.exists(self._queue_path):
            return
        # Atomically claim the queue: rename it aside so the Java service keeps
        # appending to a fresh file while we process this batch (no lost lines).
        claim = self._queue_path + ".processing"
        try:
            os.rename(self._queue_path, claim)
        except OSError:
            return
        try:
            with open(claim, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            lines = []
        finally:
            try:
                os.remove(claim)
            except OSError:
                pass

        for line in lines:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            package_name, _, body = line.partition("\t")
            if body:
                self.notification_service.on_notification_received(body, package_name)

    def simulate_notification(self, text, package_name="com.phonepe.app"):
        """Desktop/testing helper — inject a notification directly."""
        self.notification_service.on_notification_received(text, package_name)
