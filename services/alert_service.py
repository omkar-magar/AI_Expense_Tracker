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
        self._audio_available = None
        self._sound = None

    def _check_audio(self):
        """Probe audio once; cache the result to avoid repeated native crashes."""
        if self._audio_available is not None:
            return self._audio_available
        try:
            from kivy.core.audio import SoundLoader
            self._sound = SoundLoader.load("assets/sounds/buzzer.mp3")
            self._audio_available = self._sound is not None
        except Exception:
            self._audio_available = False
        return self._audio_available

    def trigger_buzzer(self):
        """Play a buzzer alert when limit is exceeded."""
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
            pass
        finally:
            self._buzzer_active = False

    def _fallback_buzzer(self):
        """Desktop fallback — play sound if audio works, otherwise skip."""
        if self._check_audio() and self._sound:
            try:
                self._sound.play()
            except Exception:
                self._audio_available = False
        self._buzzer_active = False

    def stop_buzzer(self):
        self._buzzer_active = False
