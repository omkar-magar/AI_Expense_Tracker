"""Formatting utilities for currency and dates."""


def format_currency(amount: float) -> str:
    if amount >= 100000:
        return f"Rs.{amount/100000:.1f}L"
    if amount >= 1000:
        return f"Rs.{amount:,.0f}"
    return f"Rs.{amount:.0f}"


def format_date_display(iso_date: str) -> str:
    from datetime import datetime
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%d %b %Y")
