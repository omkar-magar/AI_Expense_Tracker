[app]
title = AI Expense Tracker
package.name = expensetracker
package.domain = com.expensetracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3,db
source.exclude_dirs = tests,venv,.git,.github,.claude,__pycache__
version = 0.1.0
requirements = python3,kivy,pyjnius,android,sqlite3,openssl,requests,certifi,charset-normalizer,idna,urllib3
orientation = portrait
fullscreen = 0
android.accept_sdk_license = True

# Android permissions
android.permissions = INTERNET,BIND_NOTIFICATION_LISTENER_SERVICE,VIBRATE,RECEIVE_BOOT_COMPLETED,READ_SMS,RECEIVE_SMS

# Compile the NotificationListenerService glue (java/com/expensetracker/*.java)
android.add_src = java

# Register the NotificationListenerService in the manifest so Android can bind
# it. Injected inside <application>. If this key is not honoured by the
# buildozer version, see java/README_notifications.md for the manual step.
android.extra_manifest_xml = <service android:name="com.expensetracker.NotificationListener" android:label="Expense Tracker Notifications" android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" android:exported="true"><intent-filter><action android:name="android.service.notification.NotificationListenerService" /></intent-filter></service>

# Android API
android.api = 34
android.minapi = 21
android.ndk = 25b

# Arch
android.archs = arm64-v8a

# Pin python-for-android to a stable release. Buildozer clones p4a from git
# (ignoring any pip-installed version), and its default branch (master) now
# builds Python 3.14 — whose android glue module is broken (missing
# mActivity → soft-keyboard crash) and has no kivy wheel. v2024.01.21 builds
# a stable Python 3.11 where both work.
p4a.branch = v2024.01.21

# Presplash and icon (replace with actual assets)
# presplash.filename = assets/presplash.png
# icon.filename = assets/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
