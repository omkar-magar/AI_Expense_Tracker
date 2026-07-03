"""
Android notification bridge — connects Android's NotificationListenerService
to the Python notification_service.

On Android:
  A Java/Kotlin NotificationListenerService captures notifications and sends
  them to this bridge via pyjnius / android.broadcast. This module registers
  a BroadcastReceiver to receive that data.

On desktop (dev mode):
  Provides a simulate_notification() function for manual testing.

Integration point:
  The Java service (to be placed in the buildozer android project) should
  broadcast an intent with extras:
    - "package_name": str (e.g. "com.phonepe.app")
    - "title": str
    - "body": str (the notification text)
"""

from kivy.utils import platform


class NotificationBridge:

    def __init__(self, notification_service):
        self.notification_service = notification_service
        self._receiver = None

    def start(self):
        if platform == "android":
            self._start_android_listener()
        else:
            print("[NotificationBridge] Running on desktop — use simulate_notification() for testing")

    def _start_android_listener(self):
        """Register a BroadcastReceiver for notification intents from Java service."""
        try:
            from jnius import autoclass
            from android import activity

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            IntentFilter = autoclass("android.content.IntentFilter")
            BroadcastReceiver = autoclass("android.content.BroadcastReceiver")

            # The Java NotificationListenerService should broadcast
            # "com.expensetracker.NOTIFICATION" with extras
            intent_filter = IntentFilter()
            intent_filter.addAction("com.expensetracker.NOTIFICATION")

            def on_broadcast(context, intent):
                package_name = intent.getStringExtra("package_name")
                body = intent.getStringExtra("body")
                if body:
                    self.notification_service.on_notification_received(body, package_name)

            activity.bind(on_new_intent=on_broadcast)
            print("[NotificationBridge] Android listener started")

        except ImportError:
            print("[NotificationBridge] pyjnius not available — Android listener not started")

    def simulate_notification(self, text: str, package_name: str = "com.phonepe.app"):
        """For desktop testing — simulate a notification arriving."""
        print(f"[SIMULATE] Notification: {text}")
        self.notification_service.on_notification_received(text, package_name)

    def stop(self):
        self._receiver = None
