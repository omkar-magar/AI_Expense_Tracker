"""
Premium UI toolkit (pure Kivy — no KivyMD, no new dependencies).

Lightweight, mobile-friendly building blocks for the fintech-style redesign:
  - AuroraBackground : slow-drifting soft color blobs over the dark ground.
  - GradientButton   : rounded button with a horizontal gradient fill + press
                       feedback (a subtle inset "squish").
  - CircularProgress : an animated ring (budget used) with rounded caps.
  - PulseDot         : a softly pulsing dot for the "AI" badge.

All effects are a handful of textured/vector canvas instructions animated with
Kivy's Clock/Animation, so they stay cheap on mid-range Android GPUs.
"""

import math

from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty, ListProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp


# --- texture helpers (built once, cached) -------------------------------------

_radial_tex = None


def radial_blob_texture(size=128):
    """A soft white radial blob (alpha fades to 0 at the edge) for aurora glow."""
    global _radial_tex
    if _radial_tex is not None:
        return _radial_tex
    buf = bytearray(size * size * 4)
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            a = max(0.0, 1.0 - d)
            a = a * a * a  # soft, concentrated falloff
            i = (y * size + x) * 4
            buf[i] = buf[i + 1] = buf[i + 2] = 255
            buf[i + 3] = int(a * 255)
    tex = Texture.create(size=(size, size), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    tex.mag_filter = tex.min_filter = "linear"
    _radial_tex = tex
    return tex


_grad_cache = {}


def h_gradient_texture(left, right, w=256):
    """Horizontal gradient (left→right rgb) as a 256x1 texture."""
    key = (tuple(left), tuple(right))
    if key in _grad_cache:
        return _grad_cache[key]
    buf = bytearray(w * 4)
    for x in range(w):
        t = x / (w - 1)
        for k in range(3):
            buf[x * 4 + k] = int((left[k] * (1 - t) + right[k] * t) * 255)
        buf[x * 4 + 3] = 255
    tex = Texture.create(size=(w, 1), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    tex.mag_filter = tex.min_filter = "linear"
    _grad_cache[key] = tex
    return tex


# --- widgets ------------------------------------------------------------------

class AuroraBackground(Widget):
    """Four large, low-opacity color blobs drifting slowly — an aurora wash.
    Cheap: 4 textured quads updated at 30fps along smooth sine paths."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._t = 0.0
        self._blobs = []
        tex = radial_blob_texture()
        tints = [
            (0.388, 0.400, 0.945),  # indigo
            (0.486, 0.227, 0.929),  # violet
            (0.024, 0.714, 0.831),  # cyan
            (0.20, 0.28, 0.85),     # blue
        ]
        with self.canvas:
            for tint in tints:
                col = Color(tint[0], tint[1], tint[2], 0.0)
                rect = Rectangle(texture=tex, pos=(0, 0), size=(10, 10))
                self._blobs.append((col, rect))
        self.bind(pos=self._relayout, size=self._relayout)
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def _relayout(self, *a):
        self._update()

    def _tick(self, dt):
        self._t += dt
        self._update()

    def _update(self):
        w, h = self.size
        if w <= 1 or h <= 1:
            return
        R = max(w, h) * 0.85
        t = self._t
        for i, (col, rect) in enumerate(self._blobs):
            fx = 0.5 + 0.30 * math.sin(t * 0.05 + i * 1.7)
            fy = 0.5 + 0.30 * math.cos(t * 0.04 + i * 2.3)
            cx = self.x + fx * w
            cy = self.y + fy * h
            rect.size = (R, R)
            rect.pos = (cx - R / 2, cy - R / 2)
            col.a = 0.20


class GradientButton(Button):
    """Rounded button with a horizontal gradient fill and a press 'squish'."""

    grad_left = ListProperty([0.388, 0.400, 0.945, 1])   # indigo
    grad_right = ListProperty([0.486, 0.227, 0.929, 1])  # violet
    radius = NumericProperty(dp(18))
    press_inset = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self._draw, size=self._draw, press_inset=self._draw,
                  grad_left=self._draw, grad_right=self._draw)

    def on_press(self):
        Animation(press_inset=dp(3), d=0.08, t="out_quad").start(self)

    def on_release(self):
        Animation(press_inset=0, d=0.22, t="out_back").start(self)

    def _draw(self, *a):
        self.canvas.before.clear()
        tex = h_gradient_texture(self.grad_left[:3], self.grad_right[:3])
        ins = self.press_inset
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(
                texture=tex,
                pos=(self.x + ins, self.y + ins),
                size=(self.width - 2 * ins, self.height - 2 * ins),
                radius=[self.radius],
            )


class CircularProgress(Widget):
    """Ring showing a 0..1 fraction; animate `progress` for a smooth sweep."""

    progress = NumericProperty(0.0)
    thickness = NumericProperty(dp(9))
    track_color = ListProperty([1, 1, 1, 0.10])
    fg_color = ListProperty([0.388, 0.400, 0.945, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, progress=self._draw,
                  fg_color=self._draw, thickness=self._draw)

    def _draw(self, *a):
        self.canvas.after.clear()
        cx, cy = self.center
        r = min(self.width, self.height) / 2 - self.thickness
        if r <= 0:
            return
        with self.canvas.after:
            Color(*self.track_color)
            Line(circle=(cx, cy, r, 0, 360), width=self.thickness, cap="round")
            frac = max(0.0, min(1.0, self.progress))
            if frac > 0:
                Color(*self.fg_color)
                Line(circle=(cx, cy, r, 0, 360 * frac), width=self.thickness, cap="round")


class PulseDot(Widget):
    """A small dot whose glow pulses — used in the AI badge."""

    glow = NumericProperty(0.4)
    dot_color = ListProperty([0.024, 0.714, 0.831, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, glow=self._draw, dot_color=self._draw)
        anim = Animation(glow=1.0, d=1.1, t="in_out_sine") + Animation(glow=0.35, d=1.1, t="in_out_sine")
        anim.repeat = True
        anim.start(self)

    def _draw(self, *a):
        self.canvas.after.clear()
        r = min(self.width, self.height) / 2
        cx, cy = self.center
        c = self.dot_color
        with self.canvas.after:
            # soft halo
            Color(c[0], c[1], c[2], 0.25 * self.glow)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            # core
            Color(c[0], c[1], c[2], self.glow)
            cr = r * 0.5
            Ellipse(pos=(cx - cr, cy - cr), size=(2 * cr, 2 * cr))
