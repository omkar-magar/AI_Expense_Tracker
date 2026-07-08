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
from kivy.uix.button import Button
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import ListProperty, NumericProperty


class FlatButton(Button):
    """Button whose fill color is a real ListProperty (`bg`), so the kv canvas
    rule can reference `self.bg` safely from the first frame — a kv-declared
    dynamic-class property defaults to None and would crash Color.rgba.

    `radius` controls the corner rounding (set to self.height/2 for a pill)."""

    bg = ListProperty([0.408, 0.353, 0.949, 1])
    radius = NumericProperty(12)


# Register so `FlatButton:` / `<FlatButton>:` resolve in kv (must run before kv load).
Factory.register("FlatButton", cls=FlatButton)

# Premium UI toolkit (aurora bg, gradient button, circular progress, pulse dot).
from premium_ui import (  # noqa: E402
    AuroraBackground, GradientButton, CircularProgress, PulseDot,
)
Factory.register("AuroraBackground", cls=AuroraBackground)
Factory.register("GradientButton", cls=GradientButton)
Factory.register("CircularProgress", cls=CircularProgress)
Factory.register("PulseDot", cls=PulseDot)

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
from screens.review import ReviewScreen
from screens.settings import SettingsScreen


class ExpenseTrackerApp(App):
    """Main Kivy application class."""

    title = "AI Expense Tracker"

    # --- Theme palette: single source of truth for colors. Reference these in
    # any .kv as `app.color_*` so the whole app can be re-skinned in one place.
    # Premium fintech scheme: near-black ground, indigo→violet gradient accent,
    # cyan highlight (CRED / Jupiter / Revolut territory).
    color_bg = ListProperty([0.035, 0.035, 0.043, 1])       # #09090B ground
    color_surface = ListProperty([0.094, 0.094, 0.106, 1])  # #18181B cards
    color_surface_alt = ListProperty([0.137, 0.137, 0.153, 1])  # #232327 rows/nav
    color_glass = ListProperty([1, 1, 1, 0.05])             # rgba(255,255,255,.05) glass
    color_card_info = ListProperty([0.043, 0.145, 0.176, 1])    # cyan-tinted
    color_card_insight = ListProperty([0.114, 0.075, 0.200, 1])  # violet-tinted
    color_accent = ListProperty([0.388, 0.400, 0.945, 1])   # #6366F1 indigo (primary)
    color_secondary = ListProperty([0.486, 0.227, 0.929, 1])  # #7C3AED violet
    color_cyan = ListProperty([0.024, 0.714, 0.831, 1])     # #06B6D4 cyan accent
    color_good = ListProperty([0.133, 0.773, 0.369, 1])     # #22C55E success
    color_warning = ListProperty([0.961, 0.620, 0.043, 1])  # #F59E0B warning
    color_text = ListProperty([1, 1, 1, 1])                 # white primary text
    color_text_muted = ListProperty([0.631, 0.631, 0.667, 1])  # #A1A1AA secondary
    color_danger = ListProperty([0.937, 0.267, 0.267, 1])   # #EF4444 danger (over/delete)

    # Category → dot color (keys match services.ai_service.CATEGORIES).
    CATEGORY_COLORS = {
        "Food": [0.976, 0.451, 0.086, 1],          # orange
        "Travel": [0.024, 0.714, 0.831, 1],        # cyan
        "Shopping": [0.388, 0.400, 0.945, 1],      # indigo
        "Recharge": [0.133, 0.773, 0.369, 1],      # green
        "Bills": [0.925, 0.286, 0.600, 1],         # pink
        "Entertainment": [0.545, 0.361, 0.965, 1],  # violet
    }

    def category_color(self, category):
        """rgba dot color for a category (falls back to neutral grey)."""
        return self.CATEGORY_COLORS.get(category, [0.50, 0.55, 0.65, 1])

    def build(self):
        self._configure_keyboard()
        self._load_kv_files()
        self._init_services()

        self.sm = ScreenManager(transition=FadeTransition())
        self.sm.add_widget(SplashScreen(name="splash"))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(LimitScreen(name="limit"))
        self.sm.add_widget(TransactionsScreen(name="transactions"))
        self.sm.add_widget(ReviewScreen(name="review"))
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
        self.sms_reader = SmsReader(self.notification_service, self.db)

    def _request_android_permissions(self):
        """Request runtime permissions needed for automatic capture."""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_SMS, Permission.RECEIVE_SMS])
        except Exception:
            pass

    def _start_capture(self):
        # In-app (foreground) pollers — instant capture while the UI is open.
        self.notification_bridge.start()
        self.sms_reader.start()
        # Background service — keeps capturing when the app is closed. Safe to
        # run alongside the in-app pollers (atomic queue + persisted sms_last_id
        # prevent double processing).
        self._start_background_service()

    def _start_background_service(self):
        """Start the p4a foreground capture service (service/capture.py).

        p4a generates a service class named Service<Name> in the app package;
        for `services = capture:...` that is `<domain>.<name>.ServiceCapture`.
        """
        try:
            from jnius import autoclass
            pkg = "com.expensetracker.expensetracker"  # package.domain + package.name
            service = autoclass("%s.ServiceCapture" % pkg)
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            service.start(activity, "")
            print("[App] Background capture service started")
        except Exception as e:
            # Non-fatal: in-app pollers still work while the app is open.
            print("[App] Could not start background service: %s" % e)

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
