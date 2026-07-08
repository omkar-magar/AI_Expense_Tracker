"""
Transaction parser — regex-based extraction from notification text.

Receives:  raw notification string (e.g. "Paid ₹230 to Swiggy")
Returns:   structured dict with amount, merchant, txn_type, etc.
           or None if the notification is not a valid transaction.

This is the CORE parser. No AI dependency — pure regex + rules.
"""

import re
from datetime import datetime
from typing import Optional


# Amount patterns: ₹230  |  Rs.230  |  Rs 230  |  INR 1,000.50
_AMOUNT_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)

# Amounts that describe a balance/limit, not the transaction value — used to
# skip the wrong number when a message contains several (e.g. "debited ₹230.
# Avl bal ₹9,500"). We match the label that PRECEDES such an amount.
_BALANCE_CONTEXT = re.compile(
    r"(?:avl(?:\.|able)?\s*bal|available\s*balance|bal(?:ance)?|limit|"
    r"a/?c\s*bal)[^₹Rs\dINR]*(?:₹|Rs\.?|INR)?\s*[\d,]+",
    re.IGNORECASE,
)

# Debit indicators
_DEBIT_KEYWORDS = [
    r"\bpaid\b",
    r"\bsent\b",
    r"\bdebited\b",
    r"\bspent\b",
    r"\bpayment\b.*\bsuccessful\b",
    r"\btransferred\b",
    r"\bcharged\b",
    r"\bwithdrawn\b",
]

# Credit indicators
_CREDIT_KEYWORDS = [
    r"\breceived\b",
    r"\bcredited\b",
    r"\brefund(?:ed)?\b",
    r"\bcashback\b",
]

# Text that means "this is NOT a completed transaction" — reject outright even
# if it contains an amount and a debit/credit-looking word. Order matters less
# than coverage here; each is a substring/regex checked against lowered text.
_REJECT_PATTERNS = [
    r"\bwill\s+be\s+(?:debited|charged|deducted|credited)\b",  # autopay reminder
    r"\bdue\b",                                                # bill due reminder
    r"\bwould\s+be\b",
    r"\bfailed\b",
    r"\bdeclined\b",
    r"\bunsuccessful\b",
    r"\bcancell?ed\b",
    r"\breversed\b",
    r"\brequest(?:ed|ing)?\b.*\bmoney\b",                      # collect request
    r"\bhas\s+requested\b",
    r"\brequesting\b",
    r"\bget\b.*\bcashback\b",                                  # promo offer
    r"\bwin\b",
    r"\boffer\b",
    r"\bvoucher\b",
    r"\bexpir(?:e|es|ing|ed)\b",
    r"\bo\.?t\.?p\b",                                          # OTP messages
    r"\bstatement\b",
]

# Merchant extraction: "to Swiggy", "at Amazon", "from Rahul"
_MERCHANT_PATTERN = re.compile(
    r"(?:to|at|from)\s+([A-Za-z0-9][\w\s&'.@()-]{0,40})",
    re.IGNORECASE,
)

# Words that commonly trail a merchant name and should be trimmed off, e.g.
# "Swiggy via UPI", "Amazon on 05-Jul", "Rahul ref 12345".
_MERCHANT_STOPWORDS = re.compile(
    r"\b(?:via|using|on|ref|refno|reference|upi|vpa|txn|utr|id|"
    r"account|a/?c|your|the|dated?|for|thru|through)\b",
    re.IGNORECASE,
)

# Known UPI / payment app packages
KNOWN_PACKAGES = {
    "com.phonepe.app": "PhonePe",
    "com.google.android.apps.nbu.paisa.user": "Google Pay",
    "net.one97.paytm": "Paytm",
}


def parse_notification(text: str, package_name: str = None) -> Optional[dict]:
    """Parse a notification string into a transaction dict.

    Returns None if the text does not look like a completed financial
    transaction (promos, reminders, OTPs, failures are all rejected).
    """
    if not text:
        return None

    if _is_rejected(text):
        return None

    txn_type = _detect_txn_type(text)
    if txn_type is None:
        return None

    amount = _extract_amount(text)
    if amount is None or amount <= 0:
        return None

    merchant = _extract_merchant(text)
    now = datetime.now()

    return {
        "amount": amount,
        "merchant": merchant,
        "txn_type": txn_type,
        "source_app": KNOWN_PACKAGES.get(package_name, package_name or "Unknown"),
        "txn_date": now.strftime("%Y-%m-%d"),
        "txn_time": now.strftime("%H:%M:%S"),
        "raw_notification": text,
        "category": "Other",
    }


def _is_rejected(text: str) -> bool:
    text_lower = text.lower()
    for pattern in _REJECT_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _extract_amount(text: str) -> Optional[float]:
    """Pick the transaction amount, skipping numbers that are clearly a
    balance/limit. Falls back to the first amount if every match looks like a
    balance (better to record something than nothing)."""
    matches = list(_AMOUNT_PATTERN.finditer(text))
    if not matches:
        return None

    balance_spans = [m.span() for m in _BALANCE_CONTEXT.finditer(text)]

    def _in_balance(match) -> bool:
        return any(start <= match.start() <= end for start, end in balance_spans)

    chosen = None
    for m in matches:
        if not _in_balance(m):
            chosen = m
            break
    if chosen is None:
        chosen = matches[0]

    amount_str = chosen.group(1).replace(",", "")
    try:
        return float(amount_str)
    except ValueError:
        return None


def _detect_txn_type(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern in _DEBIT_KEYWORDS:
        if re.search(pattern, text_lower):
            return "debit"
    for pattern in _CREDIT_KEYWORDS:
        if re.search(pattern, text_lower):
            return "credit"
    return None


def _extract_merchant(text: str) -> Optional[str]:
    match = _MERCHANT_PATTERN.search(text)
    if not match:
        return None
    merchant = match.group(1).strip()

    # Cut the name off at the first trailing stopword ("Swiggy via UPI" -> "Swiggy").
    stop = _MERCHANT_STOPWORDS.search(merchant)
    if stop:
        merchant = merchant[: stop.start()]

    # Trim punctuation/whitespace and collapse internal runs of spaces.
    merchant = re.sub(r"\s+", " ", merchant).strip(" .,-&'")
    if len(merchant) > 1:
        return merchant
    return None
