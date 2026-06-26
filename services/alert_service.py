"""
Alert service — buzzer and visual alerts when daily limit is exceeded.

On Android, this will use platform-specific vibration / sound APIs.
On desktop (dev mode), it falls back to a Kivy sound or console warning.
"""

from kivy.utils import platform

if platform == "android":
    try:
        from jnius import autoclass
    except ImportError:
        autoclass = None
else:
    autoclass = None


BUZZER_DURATION_MS = 5000


class AlertService:

    def __init__(self):
        self._buzzer_active = False

    def trigger_buzzer(self):
        """Play a 5-second buzzer alert."""
        if self._buzzer_active:
            return

        self._buzzer_active = True

        if platform == "android" and autoclass:
            self._android_buzzer()
        else:
            self._fallback_buzzer()

    def _android_buzzer(self):
        """Vibrate on Android for BUZZER_DURATION_MS."""
        try:
            Context = autoclass("android.content.Context")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
            vibrator.vibrate(BUZZER_DURATION_MS)
        except Exception:
            self._fallback_buzzer()
        finally:
            self._buzzer_active = False

    def _fallback_buzzer(self):
        """Desktop fallback — try playing a sound file, else print warning."""
        try:
            from kivy.core.audio import SoundLoader

            sound = SoundLoader.load("assets/sounds/buzzer.wav")
            if sound:
                sound.play()
        except Exception:
            pass

        print(f"[ALERT] Daily spending limit exceeded!")
        self._buzzer_active = False

    def stop_buzzer(self):
        self._buzzer_active = False
