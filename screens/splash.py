"""Splash screen — loading, initialization, and permission checks on Android."""

from kivy.uix.screenmanager import Screen
from kivy.utils import platform


class SplashScreen(Screen):

    def on_enter(self):
        if platform == "android":
            self._request_android_permissions()

    def _request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.VIBRATE,
            ])
        except ImportError:
            pass
