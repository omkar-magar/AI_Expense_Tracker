"""
AI service — pluggable categorization and insights layer.

Uses Gemini Flash Pro when enabled and API key is configured.
Falls back to rule-based keyword matching when AI is off or API fails.
"""

import json
from typing import Optional

try:
    from google import genai
except ImportError:
    genai = None

CATEGORIES = ["Food", "Travel", "Shopping", "Recharge", "Bills", "Entertainment", "Other"]

CATEGORY_KEYWORDS = {
    "Food": [
        "swiggy", "zomato", "dominos", "pizza", "mcdonalds", "kfc",
        "burger", "restaurant", "cafe", "food", "biryani", "chai",
        "starbucks", "subway", "dunkin",
    ],
    "Travel": [
        "uber", "ola", "rapido", "metro", "irctc", "redbus",
        "makemytrip", "goibibo", "yatra", "petrol", "fuel",
        "parking", "toll",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa",
        "croma", "reliance", "dmart", "bigbasket", "blinkit",
        "zepto", "instamart",
    ],
    "Recharge": [
        "jio", "airtel", "vi", "vodafone", "idea", "bsnl",
        "recharge", "prepaid", "postpaid",
    ],
    "Bills": [
        "electricity", "water", "gas", "broadband", "wifi",
        "insurance", "emi", "loan", "rent", "maintenance",
        "bill payment",
    ],
    "Entertainment": [
        "netflix", "hotstar", "prime", "spotify", "youtube",
        "bookmyshow", "pvr", "inox", "gaming",
    ],
}

CATEGORIZE_PROMPT = """You are a transaction categorizer for an Indian expense tracker app.

Given a UPI/payment notification, respond with ONLY one of these categories:
Food, Travel, Shopping, Recharge, Bills, Entertainment, Other

Merchant: {merchant}
Notification: {text}

Category:"""

SUMMARY_PROMPT = """You are a smart expense assistant for an Indian user.

Here are today's transactions:
{transactions}

Daily limit: Rs.{daily_limit}
Total spent: Rs.{total_spent}
Remaining: Rs.{remaining}

Give a short, helpful 2-3 sentence summary of today's spending. Mention the top spending category, any notable patterns, and whether the user is on track with their budget. Keep it conversational and in Indian Rupees. Do not use markdown."""

INSIGHTS_PROMPT = """You are a financial insights assistant for an Indian expense tracker.

Here are today's transactions:
{transactions}

Provide 2-3 short, actionable spending tips based on these transactions. Each tip should be one sentence. Be specific to what the user actually spent on. Do not use markdown or bullet points — just numbered lines."""


class AIService:

    def __init__(self, use_llm=False, api_key=None):
        self.use_llm = use_llm
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None and self.api_key and genai:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def configure(self, use_llm: bool, api_key: str = None):
        self.use_llm = use_llm
        if api_key and api_key != self.api_key:
            self.api_key = api_key
            self._client = None

    @property
    def is_active(self) -> bool:
        return self.use_llm and bool(self.api_key) and genai is not None

    def categorize(self, merchant: Optional[str], raw_text: str = "") -> str:
        if self.is_active:
            result = self._gemini_categorize(merchant, raw_text)
            if result:
                return result
        return self._rule_based_categorize(merchant, raw_text)

    def get_daily_summary(self, transactions: list, budget_summary: dict = None) -> str:
        if self.is_active and transactions:
            result = self._gemini_summary(transactions, budget_summary)
            if result:
                return result
        return self._rule_based_summary(transactions)

    def get_insights(self, transactions: list) -> str:
        if self.is_active and transactions:
            result = self._gemini_insights(transactions)
            if result:
                return result
        return ""

    # --- Gemini API calls ---

    def _gemini_categorize(self, merchant: Optional[str], raw_text: str) -> Optional[str]:
        try:
            prompt = CATEGORIZE_PROMPT.format(
                merchant=merchant or "Unknown",
                text=raw_text,
            )
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            category = response.text.strip().split("\n")[0].strip()
            if category in CATEGORIES:
                return category
            for cat in CATEGORIES:
                if cat.lower() in category.lower():
                    return cat
            return None
        except Exception as e:
            print(f"[AIService] Gemini categorize failed: {e}")
            return None

    def _gemini_summary(self, transactions: list, budget_summary: dict = None) -> Optional[str]:
        try:
            txn_lines = []
            for t in transactions:
                txn_lines.append(
                    f"Rs.{t.get('amount', 0):.0f} to {t.get('merchant', 'Unknown')} [{t.get('category', 'Other')}] at {t.get('txn_time', '')}"
                )
            txn_text = "\n".join(txn_lines)

            total = sum(t.get("amount", 0) for t in transactions)
            limit = budget_summary.get("daily_limit", 0) if budget_summary else 0
            remaining = budget_summary.get("remaining", 0) if budget_summary else 0

            prompt = SUMMARY_PROMPT.format(
                transactions=txn_text,
                daily_limit=f"{limit:.0f}",
                total_spent=f"{total:.0f}",
                remaining=f"{remaining:.0f}",
            )
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AIService] Gemini summary failed: {e}")
            return None

    def _gemini_insights(self, transactions: list) -> Optional[str]:
        try:
            txn_lines = []
            for t in transactions:
                txn_lines.append(
                    f"Rs.{t.get('amount', 0):.0f} to {t.get('merchant', 'Unknown')} [{t.get('category', 'Other')}]"
                )
            prompt = INSIGHTS_PROMPT.format(transactions="\n".join(txn_lines))
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AIService] Gemini insights failed: {e}")
            return None

    # --- Rule-based fallbacks ---

    def _rule_based_categorize(self, merchant: Optional[str], raw_text: str) -> str:
        search_text = f"{merchant or ''} {raw_text}".lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in search_text:
                    return category
        return "Other"

    def _rule_based_summary(self, transactions: list) -> str:
        if not transactions:
            return "No transactions today."

        total = sum(t.get("amount", 0) for t in transactions)
        count = len(transactions)

        category_totals = {}
        for t in transactions:
            cat = t.get("category", "Other")
            category_totals[cat] = category_totals.get(cat, 0) + t.get("amount", 0)

        top_category = max(category_totals, key=category_totals.get)

        return (
            f"You made {count} transaction(s) totaling Rs.{total:.0f} today. "
            f"Top category: {top_category} (Rs.{category_totals[top_category]:.0f})."
        )
