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

   We inject this via `android.extra_manifest_xml` in `buildozer.spec`. **If your
   buildozer version ignores that key**, the service won't be registered and
   notifications won't be captured (SMS still works). To verify after a build,
   check the generated
   `.buildozer/android/platform/build-*/dists/*/src/main/AndroidManifest.xml`
   contains the `<service>` above. If it doesn't, add it to the p4a manifest
   template or use your buildozer version's manifest-injection option.

## Granting access on the phone
Notification access is not a runtime permission. The user must enable it once:
**Settings → Notification access → AI Expense Tracker → allow**. The app's
Settings screen has a **"Grant Notification Access"** button that opens this
screen directly.

## SMS (no Java needed)
`capture/sms_reader.py` reads bank/UPI SMS by polling the SMS content provider
via pyjnius. It only needs the `READ_SMS` permission (requested at startup).
