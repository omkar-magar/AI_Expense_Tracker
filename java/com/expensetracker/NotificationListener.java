/*
 * NotificationListener — minimal Android glue for reading UPI notifications.
 *
 * Android requires notification access to go through a NotificationListenerService
 * that the OS itself instantiates, so this small Java class is unavoidable. It
 * contains NO app logic: it only grabs the notification text from monitored
 * payment apps and appends it to a queue file in the app's private files dir.
 * The Python side (android/notification_bridge.py) polls that file and does all
 * parsing, categorizing, and storage.
 *
 * Queue line format:  <package>\t<body>\n
 *
 * This file is compiled into the APK via `android.add_src` in buildozer.spec.
 * It must also be declared in AndroidManifest.xml (see android/README_notifications.md).
 * The user must grant "Notification Access" in Android Settings once.
 */

package com.expensetracker;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.io.File;
import java.io.FileWriter;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class NotificationListener extends NotificationListenerService {

    private static final String QUEUE_FILENAME = "notif_queue.txt";

    private static final Set<String> MONITORED_PACKAGES = new HashSet<>(Arrays.asList(
        "com.phonepe.app",                          // PhonePe
        "com.google.android.apps.nbu.paisa.user",   // Google Pay
        "net.one97.paytm"                           // Paytm
    ));

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        String packageName = sbn.getPackageName();
        if (packageName == null || !MONITORED_PACKAGES.contains(packageName)) {
            return;
        }

        CharSequence bodyCs = sbn.getNotification().extras.getCharSequence("android.text");
        String body = bodyCs != null ? bodyCs.toString() : "";
        if (body.isEmpty()) {
            return;
        }

        // Keep the line single-record: strip tabs/newlines from the body.
        String line = packageName + "\t" + body.replace("\t", " ").replace("\n", " ").replace("\r", " ") + "\n";

        synchronized (NotificationListener.class) {
            FileWriter writer = null;
            try {
                File queue = new File(getFilesDir(), QUEUE_FILENAME);
                writer = new FileWriter(queue, true);  // append
                writer.write(line);
            } catch (Exception e) {
                // Ignore — nothing we can safely do from here.
            } finally {
                if (writer != null) {
                    try { writer.close(); } catch (Exception ignored) {}
                }
            }
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // No action needed.
    }
}
