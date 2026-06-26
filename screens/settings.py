"""Settings screen — Gemini AI configuration, API key, and toggle."""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty

from database.queries import get_setting, set_setting


class SettingsScreen(Screen):

    api_key_display = StringProperty("")
    ai_enabled = BooleanProperty(False)
    status_text = StringProperty("")

    def on_enter(self):
        app = App.get_running_app()
        key = get_setting(app.db, "gemini_api_key") or ""
        self.api_key_display = self._mask_key(key)
        self.ai_enabled = get_setting(app.db, "ai_enabled") == "1"
        self._update_status(app)

    def save_api_key(self, key_text: str):
        key_text = key_text.strip()
        if not key_text:
            return
        app = App.get_running_app()
        set_setting(app.db, "gemini_api_key", key_text)
        self.api_key_display = self._mask_key(key_text)
        app.ai_service.configure(use_llm=self.ai_enabled, api_key=key_text)
        self._update_status(app)

    def toggle_ai(self, is_active: bool):
        app = App.get_running_app()
        self.ai_enabled = is_active
        set_setting(app.db, "ai_enabled", "1" if is_active else "0")
        api_key = get_setting(app.db, "gemini_api_key") or ""
        app.ai_service.configure(use_llm=is_active, api_key=api_key)
        self._update_status(app)

    def _update_status(self, app):
        if app.ai_service.is_active:
            self.status_text = "Gemini Flash Pro: ACTIVE"
        elif self.ai_enabled:
            self.status_text = "AI enabled but no API key set"
        else:
            self.status_text = "AI disabled (using rule-based mode)"

    def _mask_key(self, key: str) -> str:
        if not key:
            return "Not set"
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]
