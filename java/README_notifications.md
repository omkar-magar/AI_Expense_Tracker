# Notification capture — Android build notes

Reading other apps' notifications requires an Android `NotificationListenerService`,
which the OS itself instantiates. That is why a small Java class exists here —
it holds **no app logic**, it only forwards notification text to the Python
side. All parsing/categorizing/storage stays in Python.

## Files
- `java/com/expensetracker/NotificationListener.java` — the glue service. It
  appends `"<package>\t<body>\n"` for monitored payment apps to
  `getFilesDir()/notif_queue.txt`.
- `capture/notification_bridge.py` — Python poller that drains that queue file
  and feeds each line into the transaction pipeline.

## Build wiring (in `buildozer.spec`)
1. `android.add_src = java` — compiles the Java class into the APK.
2. `android.permissions = ...,BIND_NOTIFICATION_LISTENER_SERVICE` — already set.
3. The service must be declared in `AndroidManifest.xml` inside `<application>`:

   ```xml
   <service
       android:name="com.expensetracker.NotificationListener"
       android:label="Expense Tracker Notifications"
       android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"
       android:exported="true">
       <intent-filter>
           <action android:name="android.service.notification.NotificationListenerService" />
       </intent-filter>
   </service>
   ```

   **STATUS: not yet wired.** `android.extra_manifest_xml` only injects into the
   top-level `<manifest>` element, and aapt rejects a `<service>` there
   (`error: unexpected element <service> found in <manifest>`). There is no
   buildozer key that injects a child element into `<application>`.

   To finish this, modify the python-for-android SDL2 manifest template so the
   `<service>` (see `java/extra_manifest.xml`) is emitted inside `<application>`.
   The template lives at
   `pythonforandroid/bootstraps/sdl2/build/templates/AndroidManifest.tmpl.xml`;
   with `p4a.branch = v2024.01.21` it is cloned into
   `.buildozer/android/platform/python-for-android/`. This can be done with a
   small patch step in the CI workflow before `buildozer android debug`.

   Until then the Java class is compiled into the APK but never bound by the OS,
   so **notification capture is inactive**. SMS capture is unaffected and works.

## Granting access on the phone
Notification access is not a runtime permission. The user must enable it once:
**Settings → Notification access → AI Expense Tracker → allow**. The app's
Settings screen has a **"Grant Notification Access"** button that opens this
screen directly.

## SMS (no Java needed)
`capture/sms_reader.py` reads bank/UPI SMS by polling the SMS content provider
via pyjnius. It only needs the `READ_SMS` permission (requested at startup).
