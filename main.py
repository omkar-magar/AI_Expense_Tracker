"""
AI Expense Tracker — Main Application Entry Point

Initializes the Kivy app, sets up the database, starts the notification
listener bridge, and manages screen navigation.
"""

import os
import sys

# python-for-android sets ANDROID_ARGUMENT; use it to detect Android without
# importing kivy yet (env vars below must be set before kivy initializes).
ON_ANDROID = "ANDROID_ARGUMENT" in os.environ

if ON_ANDROID:
    try:
        from jnius import autoclass
        _activity = autoclass("org.kivy.android.PythonActivity").mActivity

        # Kivy's SDL2 backend opens the soft keyboard via `from android import
        # mActivity`, but this python-for-android's `android` module no longer
        # exposes that name — so focusing any TextInput raises
        # `ImportError: cannot import name mActivity` and crashes the app.
        # Inject the activity (which we already have via jnius) so Kivy's
        # import succeeds and the keyboard can open.
        import android
        if not hasattr(android, "mActivity"):
            android.mActivity = _activity

        # Route Kivy's logs (which capture the last events before a crash) to
        # the app's external files dir — readable with any file manager at
        # Android/data/<package>/files/.kivy/logs, no USB/adb or permission.
        _ext = _activity.getExternalFilesDir(None)
        if _ext is not None:
            os.environ.setdefault("KIVY_HOME", os.path.join(_ext.getAbsolutePath(), ".kivy"))
    except Exception:
        pass
elif sys.platform == "win32":
    # Windows-only desktop fixes — ANGLE avoids a native SDL2/TextInput crash on
    # older Intel GPU drivers, directsound avoids a WASAPI audio crash, and
    # disabling the SDL IME UI avoids a Windows text-entry quirk. None apply on
    # Android, where setting them crashes the app.
    os.environ.setdefault("KIVY_GL_BACKEND", "angle_sdl2")
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
    os.environ.setdefault("SDL_IME_SHOW_UI", "0")

# Force the system (native) soft keyboard on Android instead of Kivy's managed
# virtual keyboard — must be set via Config before the Window is created.
from kivy.config import Config
if ON_ANDROID:
    Config.set("kivy", "keyboard_mode", "system")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.clock import Clock

import glob

from database.db_manager import DatabaseManager
from services.notification_service import NotificationService
from services.budget_service import BudgetService
from services.alert_service import AlertService
from services.ai_service import AIService
from services.transaction_service import TransactionService

from capture.notification_bridge import NotificationBridge
from capture.sms_reader import SmsReader

from screens.splash import SplashScreen
from screens.dashboard import DashboardScreen
from screens.limit import LimitScreen
from screens.transactions import TransactionsScreen
from screens.settings import SettingsScreen


class ExpenseTrackerApp(App):
    """Main Kivy application class."""

    title = "AI Expense Tracker"

    def build(self):
        self._configure_keyboard()
        self._load_kv_files()
        self._init_services()

        self.sm = ScreenManager(transition=FadeTransition())
        self.sm.add_widget(SplashScreen(name="splash"))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(LimitScreen(name="limit"))
        self.sm.add_widget(TransactionsScreen(name="transactions"))
        self.sm.add_widget(SettingsScreen(name="settings"))

        Clock.schedule_once(self._after_init, 2)
        return self.sm

    def _configure_keyboard(self):
        """Pan the layout so the focused field sits just above the soft keyboard
        ('below_target'), instead of resizing the GL surface (a TextInput crash
        trigger on Android) or over-panning it off the top of the screen."""
        from kivy.core.window import Window
        from kivy.utils import platform
        if platform == "android":
            Window.softinput_mode = "below_target"

    def _load_kv_files(self):
        kv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kv")
        for kv_file in sorted(glob.glob(os.path.join(kv_dir, "*.kv"))):
            Builder.load_file(kv_file)

    def _init_services(self):
        self.db = DatabaseManager()
        self.db.initialize()

        from database.queries import get_setting
        ai_enabled = get_setting(self.db, "ai_enabled") == "1"
        api_key = get_setting(self.db, "gemini_api_key") or ""

        self.ai_service = AIService(use_llm=ai_enabled, api_key=api_key)
        self.transaction_service = TransactionService(self.db, self.ai_service)
        self.budget_service = BudgetService(self.db)
        self.alert_service = AlertService()
        self.notification_service = NotificationService(
            transaction_service=self.transaction_service,
            budget_service=self.budget_service,
            alert_service=self.alert_service,
        )

        # Automatic transaction capture (Android only; inert on desktop).
        self.notification_bridge = NotificationBridge(self.notification_service)
        self.sms_reader = SmsReader(self.notification_service)

    def _request_android_permissions(self):
        """Request runtime permissions needed for automatic capture."""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_SMS, Permission.RECEIVE_SMS])
        except Exception:
            pass

    def _start_capture(self):
        self.notification_bridge.start()
        self.sms_reader.start()

    def _after_init(self, dt):
        from kivy.utils import platform
        if platform == "android":
            self._request_android_permissions()
            self._start_capture()
        self.sm.current = "dashboard"

    def get_app(self):
        return self


if __name__ == "__main__":
    try:
        ExpenseTrackerApp().run()
    except Exception:
        # Make sure any fatal Python error lands in the (now accessible) Kivy
        # log instead of vanishing silently on the device.
        from kivy.logger import Logger
        Logger.exception("FATAL: uncaught exception in app")
        raise
