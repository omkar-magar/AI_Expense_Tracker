"""
Notification service — entry point for incoming Android notifications.

Receives:  raw notification data from the Android bridge
Does:      delegates to TransactionService, then checks budget, triggers alert
Returns:   nothing (side-effects: DB write, possible buzzer)

This is the top-level orchestrator called by the Android bridge.
"""

from kivy.clock import Clock


class NotificationService:

    def __init__(self, transaction_service, budget_service, alert_service):
        self.transaction_service = transaction_service
        self.budget_service = budget_service
        self.alert_service = alert_service
        self._dashboard_callback = None

    def set_dashboard_callback(self, callback):
        """Register a callback to refresh the dashboard after new transactions."""
        self._dashboard_callback = callback

    def on_notification_received(self, text: str, package_name: str = None):
        """Called by the Android bridge when a notification arrives."""
        txn = self.transaction_service.process_notification(text, package_name)

        if txn is None:
            return

        # The txn is captured as 'pending' (not yet counted), so warn using a
        # projected total: today's confirmed spend + this new debit.
        if txn["txn_type"] == "debit":
            if self.budget_service.would_exceed(txn.get("amount", 0)):
                self.alert_service.trigger_buzzer()

        if self._dashboard_callback:
            Clock.schedule_once(lambda dt: self._dashboard_callback(), 0)
