"""Tests for the transaction parser."""

import unittest
from services.transaction_parser import parse_notification


class TestTransactionParser(unittest.TestCase):

    def test_paid_to_merchant(self):
        result = parse_notification("Paid ₹230 to Swiggy")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 230.0)
        self.assertEqual(result["txn_type"], "debit")
        self.assertEqual(result["merchant"], "Swiggy")

    def test_sent_to_person(self):
        result = parse_notification("Sent ₹1000 to Rahul")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 1000.0)
        self.assertEqual(result["txn_type"], "debit")
        self.assertEqual(result["merchant"], "Rahul")

    def test_debited_via_upi(self):
        result = parse_notification("Debited ₹250 from account via UPI")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 250.0)
        self.assertEqual(result["txn_type"], "debit")

    def test_received_is_credit(self):
        result = parse_notification("Received ₹500 from Amit")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 500.0)
        self.assertEqual(result["txn_type"], "credit")
        self.assertEqual(result["merchant"], "Amit")

    def test_payment_successful(self):
        result = parse_notification("Payment of ₹500 successful")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 500.0)
        self.assertEqual(result["txn_type"], "debit")

    def test_rs_format(self):
        result = parse_notification("Paid Rs.350 to Amazon")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 350.0)

    def test_comma_amount(self):
        result = parse_notification("Sent ₹1,500 to Flipkart")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 1500.0)

    def test_non_transaction_returns_none(self):
        result = parse_notification("Your OTP is 123456")
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        result = parse_notification("")
        self.assertIsNone(result)

    def test_none_input_returns_none(self):
        result = parse_notification(None)
        self.assertIsNone(result)

    def test_package_name_maps_to_source(self):
        result = parse_notification("Paid ₹100 to Test", "com.phonepe.app")
        self.assertEqual(result["source_app"], "PhonePe")

    def test_unknown_package(self):
        result = parse_notification("Paid ₹100 to Test", "com.unknown.app")
        self.assertEqual(result["source_app"], "com.unknown.app")


class TestParserCorrectness(unittest.TestCase):
    """Regression tests for false-positive filtering, merchant cleanup, and
    balance-aware amount selection (suggestion #1)."""

    def test_future_autopay_reminder_rejected(self):
        self.assertIsNone(parse_notification("₹499 will be debited on 5th for Netflix"))

    def test_failed_txn_rejected(self):
        self.assertIsNone(parse_notification("Payment of ₹500 to Swiggy failed"))

    def test_declined_txn_rejected(self):
        self.assertIsNone(parse_notification("Your payment of ₹1200 was declined"))

    def test_collect_request_rejected(self):
        self.assertIsNone(parse_notification("Rahul has requested ₹200 from you"))

    def test_promo_cashback_offer_rejected(self):
        self.assertIsNone(parse_notification("Get ₹100 cashback on your next order!"))

    def test_bill_due_reminder_rejected(self):
        self.assertIsNone(parse_notification("Your electricity bill of ₹1500 is due"))

    def test_merchant_trailing_via_stripped(self):
        result = parse_notification("Paid ₹230 to Swiggy via UPI")
        self.assertIsNotNone(result)
        self.assertEqual(result["merchant"], "Swiggy")

    def test_merchant_trailing_ref_stripped(self):
        result = parse_notification("Sent ₹500 to Rahul ref 998877")
        self.assertEqual(result["merchant"], "Rahul")

    def test_balance_amount_not_picked(self):
        result = parse_notification("Debited ₹230 to Amazon. Avl bal ₹9,500")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 230.0)

    def test_limit_amount_not_picked(self):
        result = parse_notification("Spent ₹230 at Cafe. Card limit ₹50,000")
        self.assertEqual(result["amount"], 230.0)

    def test_real_cashback_credit_still_parses(self):
        result = parse_notification("₹50 cashback credited to your account")
        self.assertIsNotNone(result)
        self.assertEqual(result["txn_type"], "credit")


class TestAIService(unittest.TestCase):

    def test_food_category(self):
        from services.ai_service import AIService
        ai = AIService()
        self.assertEqual(ai.categorize("Swiggy", ""), "Food")
        self.assertEqual(ai.categorize("Zomato", ""), "Food")

    def test_travel_category(self):
        from services.ai_service import AIService
        ai = AIService()
        self.assertEqual(ai.categorize("Uber", ""), "Travel")

    def test_shopping_category(self):
        from services.ai_service import AIService
        ai = AIService()
        self.assertEqual(ai.categorize("Amazon", ""), "Shopping")

    def test_unknown_category(self):
        from services.ai_service import AIService
        ai = AIService()
        self.assertEqual(ai.categorize("Rahul", "Sent money"), "Other")


if __name__ == "__main__":
    unittest.main()
