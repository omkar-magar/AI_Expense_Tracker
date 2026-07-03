"""Limit screen — allows user to set daily spending limit."""

from math import sin, cos, radians

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty, ListProperty
from kivy.graphics import Color, Line, Triangle
from kivy.metrics import dp
from kivy.factory import Factory


class ResetButton(Button):
    """A borderless button that draws a circular 'reset' arrow with the
    canvas (vector), so it renders reliably on Android without relying on a
    font that has the Unicode glyph."""

    icon_color = ListProperty([0.8, 0.8, 0.9, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self._redraw, size=self._redraw, icon_color=self._redraw)

    def _redraw(self, *args):
        self.canvas.after.clear()
        cx, cy = self.center
        r = min(self.width, self.height) * 0.26
        end = 300.0  # degrees, clockwise from top; leaves a gap for the arrow
        with self.canvas.after:
            Color(*self.icon_color)
            Line(circle=(cx, cy, r, 20, end), width=dp(1.6))
            # Arrowhead at the arc's end, pointing along the clockwise tangent.
            th = radians(end)
            ex, ey = cx + r * sin(th), cy + r * cos(th)
            tx, ty = cos(th), -sin(th)      # clockwise tangent direction
            nx, ny = -ty, tx                # normal
            h, w = dp(7), dp(4.5)
            Triangle(points=[
                ex + tx * h, ey + ty * h,   # tip
                ex + nx * w, ey + ny * w,   # base corner
                ex - nx * w, ey - ny * w,   # base corner
            ])


Factory.register("ResetButton", cls=ResetButton)


class LimitScreen(Screen):

    current_limit = StringProperty("")

    def on_enter(self):
        app = App.get_running_app()
        self.current_limit = str(int(app.budget_service.get_daily_limit()))

    def save_limit(self, value_text: str):
        try:
            amount = float(value_text)
            if amount <= 0:
                return
        except (ValueError, TypeError):
            return

        app = App.get_running_app()
        app.budget_service.set_daily_limit(amount)
        self.current_limit = str(int(amount))
        self.manager.current = "dashboard"

    def reset_limit(self):
        """Reset the daily limit back to zero."""
        app = App.get_running_app()
        app.budget_service.set_daily_limit(0)
        self.current_limit = "0"
