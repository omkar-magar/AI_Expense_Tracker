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

   **STATUS: wired via a CI patch.** `android.extra_manifest_xml` only injects
   into the top-level `<manifest>`, and aapt rejects a `<service>` there
   (`error: unexpected element <service> found in <manifest>`); no buildozer key
   injects a child element into `<application>`. So instead the CI workflow:
     1. clones python-for-android at `v2024.01.21` into `p4a-patched/`,
     2. runs `tools/patch_p4a_manifest.py`, which inserts the `<service>` above
        into the SDL2 `AndroidManifest.tmpl.xml` (inside `<application>`), and
     3. rewrites `p4a.branch` to `p4a.source_dir = .../p4a-patched` so buildozer
        builds from the patched copy.

   To verify after a build, check the generated
   `.buildozer/android/platform/build-*/dists/*/src/main/AndroidManifest.xml`
   contains the `<service>` inside `<application>`.

## Granting access on the phone
Notification access is not a runtime permission. The user must enable it once:
**Settings → Notification access → AI Expense Tracker → allow**. The app's
Settings screen has a **"Grant Notification Access"** button that opens this
screen directly.

## SMS (no Java needed)
`capture/sms_reader.py` reads bank/UPI SMS by polling the SMS content provider
via pyjnius. It only needs the `READ_SMS` permission (requested at startup).
The last-seen message id is persisted (`sms_last_id` in settings), so messages
that arrive while the app is closed are picked up on the next poll instead of
being skipped.

## Background service (capture while the app is closed)
`service/capture.py` is a python-for-android **foreground service** that runs
the same capture pipeline in a separate process, so SMS / UPI notifications are
captured even when the UI is backgrounded or closed.

- Wired in `buildozer.spec`: `services = capture:service/capture.py:foreground`
  plus the `FOREGROUND_SERVICE` and `WAKE_LOCK` permissions.
- Started from the app in `main.py::_start_background_service()` via the p4a
  generated class `com.expensetracker.expensetracker.ServiceCapture`.
- It reuses `SmsReader`/`NotificationBridge` through their `setup()` +
  `poll_once()`/`drain_once()` methods (no duplicated logic). Running it
  alongside the in-app pollers is safe: SMS progress is the shared persisted
  `sms_last_id`, and the notification queue file is claimed atomically.

**Needs on-device verification** (cannot be tested off-device):
  1. Install, grant Notification Access + SMS permission, then close the app.
  2. Make a UPI payment; confirm a persistent "capture service" notification is
     present and the payment appears in the Review inbox on reopening.
  3. If the service class isn't found, check the generated service name in
     `.buildozer/.../dists/*/src/main/java/.../ServiceCapture.java` and update
     the class name in `_start_background_service()` to match.
