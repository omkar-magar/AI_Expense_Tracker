[app]
title = AI Expense Tracker
package.name = expensetracker
package.domain = com.expensetracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3,db
version = 0.1.0
requirements = python3,kivy,pyjnius,android,sqlite3
orientation = portrait
fullscreen = 0

# Android permissions
android.permissions = BIND_NOTIFICATION_LISTENER_SERVICE,VIBRATE,RECEIVE_BOOT_COMPLETED

# Android API
android.api = 33
android.minapi = 21
android.ndk = 25b

# Include the Java notification listener service
android.add_src = android/

# Presplash and icon (replace with actual assets)
# presplash.filename = assets/presplash.png
# icon.filename = assets/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
