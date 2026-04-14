"""
Settlement calculator.

Logic:
  total_common_per_user  = sum of transactions tagged 'common'
  fixed_per_user         = sum of active fixed expenses
  total_per_user         = total_common + fixed
  fair_share             = (total_laerke + total_hector) / 2
  balance                = total_laerke - total_hector  (positive → Laerke paid more)
  delta                  = abs(balance) / 2
  who_pays_whom          = "Hector pays Laerke €X" or vice versa

Fixed expenses auto-carry: when a new month is opened (first upload for that
month), copy all active fixed expenses from the most recent previous month
that has data (or from the base fixed_expenses table).
"""
from __future__ import annotations

from budget import db




def ensure_month_exists(month: int, year: int) -> None:
    """
    Called before the first import of a month.
    Ensures a monthly_summary row exists and that fixed expenses are recorded.
    Fixed expenses live in the fixed_expenses table directly (not per-month),
    so no copy is needed — they are always pulled live.
    This function just guarantees a monthly_summary seed row exists.
    """
    existing = db.get_monthly_summary(month, year)
    if existing is None:
        db.upsert_monthly_summary(
            {
                "month": month,
                "year": year,
                "laerke_common": 0,
                "hector_common": 0,
                "fixed_laerke": 0,
                "fixed_hector": 0,
                "laerke_personal": 0,
                "hector_personal": 0,
                "balance": 0,
                "who_pays_whom": None,
            }
        )


def calculate_settlement(month: int, year: int) -> dict:
    """
    Recompute and persist the monthly summary for the given month/year.
    Returns the summary dict.
    """
    transactions = db.get_transactions(month, year)
    fixed_expenses = db.get_fixed_expenses()

    # --- Common transactions per user ---
    laerke_common_tx = [
        t for t in transactions
        if t["user"] == "Laerke" and t["category"] == "common" and t["amount"] < 0
    ]
    hector_common_tx = [
        t for t in transactions
        if t["user"] == "Hector" and t["category"] == "common" and t["amount"] < 0
    ]
    laerke_common = sum(abs(t["amount"]) for t in laerke_common_tx)
    hector_common = sum(abs(t["amount"]) for t in hector_common_tx)

    # --- Personal transactions per user ---
    laerke_personal_tx = [
        t for t in transactions
        if t["user"] == "Laerke" and t["category"] == "personal" and t["amount"] < 0
    ]
    hector_personal_tx = [
        t for t in transactions
        if t["user"] == "Hector" and t["category"] == "personal" and t["amount"] < 0
    ]
    laerke_personal = sum(abs(t["amount"]) for t in laerke_personal_tx)
    hector_personal = sum(abs(t["amount"]) for t in hector_personal_tx)

    # --- Active fixed expenses per user ---
    fixed_laerke = sum(
        fe["amount"]
        for fe in fixed_expenses
        if fe["user"] == "Laerke" and fe["active"]
    )
    fixed_hector = sum(
        fe["amount"]
        for fe in fixed_expenses
        if fe["user"] == "Hector" and fe["active"]
    )

    # --- Settlement (50/50 on common + fixed) ---
    total_laerke = laerke_common + fixed_laerke
    total_hector = hector_common + fixed_hector
    total_combined = total_laerke + total_hector
    fair_share = total_combined / 2

    # Positive → Laerke paid more than her share → Hector owes Laerke
    balance = total_laerke - fair_share  # amount Laerke is owed (or owes if negative)

    if balance > 0.005:
        who_pays_whom = f"Hector pays Laerke €{balance:.2f}"
    elif balance < -0.005:
        who_pays_whom = f"Laerke pays Hector €{abs(balance):.2f}"
    else:
        who_pays_whom = "All settled ✓"

    summary = {
        "month": month,
        "year": year,
        "laerke_common": round(laerke_common, 2),
        "hector_common": round(hector_common, 2),
        "fixed_laerke": round(fixed_laerke, 2),
        "fixed_hector": round(fixed_hector, 2),
        "laerke_personal": round(laerke_personal, 2),
        "hector_personal": round(hector_personal, 2),
        "balance": round(balance, 2),
        "who_pays_whom": who_pays_whom,
    }

    db.upsert_monthly_summary(summary)
    return summary


def get_or_calculate(month: int, year: int) -> dict | None:
    """Return existing summary or calculate fresh if transactions exist."""
    txs = db.get_transactions(month, year)
    if not txs:
        return None
    return calculate_settlement(month, year)
