"""
Transaction service — orchestrates parsing, validation, dedup, and storage.

Receives:  raw notification text + package name
Does:      parse → deduplicate → categorize (AI) → save to DB
Returns:   saved transaction dict, or None if invalid/duplicate
"""

from services.transaction_parser import parse_notification
from database.queries import insert_transaction, find_duplicate, log_notification


class TransactionService:

    def __init__(self, db, ai_service=None):
        self.db = db
        self.ai_service = ai_service

    def process_notification(self, text: str, package_name: str = None) -> dict | None:
        """Full pipeline: parse → dedup → categorize → save as 'pending'.

        Auto-captured transactions are stored as 'pending' so the user reviews
        them before they count toward spending (see the review inbox). Manual
        entries go straight to 'confirmed' via add_manual_transaction.
        """
        txn = parse_notification(text, package_name)

        if txn is None:
            log_notification(self.db, package_name, None, text, processed=-1)
            return None

        if find_duplicate(self.db, txn):
            log_notification(self.db, package_name, None, text, processed=-1)
            return None

        if self.ai_service:
            txn["category"] = self.ai_service.categorize(
                txn.get("merchant"), txn["raw_notification"]
            )

        txn_id = insert_transaction(self.db, txn, status="pending")
        txn["id"] = txn_id
        txn["status"] = "pending"

        log_notification(self.db, package_name, None, text, processed=1, txn_id=txn_id)

        return txn
