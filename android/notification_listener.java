/*
 * Android NotificationListenerService stub.
 *
 * This file should be placed in the Buildozer android project's Java source
 * directory. It listens for all device notifications and broadcasts
 * transaction-relevant ones to the Python layer.
 *
 * Path in buildozer project:
 *   .buildozer/android/app/src/main/java/com/expensetracker/NotificationListener.java
 *
 * Required in AndroidManifest.xml:
 *   <service android:name=".NotificationListener"
 *            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
 *       <intent-filter>
 *           <action android:name="android.service.notification.NotificationListenerService" />
 *       </intent-filter>
 *   </service>
 *
 * The user must grant "Notification Access" permission in Android Settings.
 */

package com.expensetracker;

import android.content.Intent;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class NotificationListener extends NotificationListenerService {

    // Package names to monitor
    private static final Set<String> MONITORED_PACKAGES = new HashSet<>(Arrays.asList(
        "com.phonepe.app",
        "com.google.android.apps.nbu.paisa.user",  // Google Pay
        "net.one97.paytm"                           // Paytm
    ));

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        String packageName = sbn.getPackageName();

        if (!MONITORED_PACKAGES.contains(packageName)) {
            return;
        }

        CharSequence bodyCs = sbn.getNotification().extras.getCharSequence("android.text");
        CharSequence titleCs = sbn.getNotification().extras.getCharSequence("android.title");

        String body = bodyCs != null ? bodyCs.toString() : "";
        String title = titleCs != null ? titleCs.toString() : "";

        // Broadcast to Python layer
        Intent intent = new Intent("com.expensetracker.NOTIFICATION");
        intent.putExtra("package_name", packageName);
        intent.putExtra("title", title);
        intent.putExtra("body", body);
        sendBroadcast(intent);
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // No action needed
    }
}
