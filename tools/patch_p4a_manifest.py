"""
Patch the python-for-android SDL2 manifest template to register our
NotificationListenerService inside <application>.

Buildozer/aapt won't let us inject a <service> via android.extra_manifest_xml
(that lands in <manifest>, which is invalid for a service). So in CI we clone
p4a, run this patch, and point buildozer at the patched copy via p4a.source_dir.

Usage:  python tools/patch_p4a_manifest.py <path-to-p4a-clone>
Idempotent: running twice is a no-op.
"""

import sys
import os
import glob

SERVICE_XML = """        <service android:name="com.expensetracker.NotificationListener"
            android:label="Expense Tracker Notifications"
            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"
            android:exported="true">
            <intent-filter>
                <action android:name="android.service.notification.NotificationListenerService" />
            </intent-filter>
        </service>
"""

MARKER = "com.expensetracker.NotificationListener"


def find_template(p4a_root):
    preferred = os.path.join(
        p4a_root, "pythonforandroid", "bootstraps", "sdl2", "build",
        "templates", "AndroidManifest.tmpl.xml",
    )
    if os.path.isfile(preferred):
        return preferred
    # Fall back to any sdl2 manifest template in the tree.
    matches = [
        m for m in glob.glob(
            os.path.join(p4a_root, "**", "AndroidManifest.tmpl.xml"), recursive=True
        )
        if "sdl2" in m.replace("\\", "/")
    ]
    if matches:
        return matches[0]
    return None


def main():
    if len(sys.argv) != 2:
        print("usage: patch_p4a_manifest.py <p4a-clone-dir>", file=sys.stderr)
        return 2

    p4a_root = sys.argv[1]
    path = find_template(p4a_root)
    if not path:
        print("ERROR: could not find sdl2 AndroidManifest.tmpl.xml under %s" % p4a_root,
              file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    if MARKER in src:
        print("Already patched: %s" % path)
        return 0

    idx = src.rfind("</application>")
    if idx == -1:
        print("ERROR: no </application> in template %s" % path, file=sys.stderr)
        return 1

    patched = src[:idx] + SERVICE_XML + src[idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)

    print("Patched notification service into %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
