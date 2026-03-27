"""
Supabase database client and all CRUD operations.
"""
from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import create_client, Client


# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def get_transactions(month: int, year: int, user: str | None = None) -> list[dict]:
    client = get_client()
    query = (
        client.table("transactions")
        .select("*")
        .eq("month", month)
        .eq("year", year)
        .order("date", desc=True)
    )
    if user:
        query = query.eq("user", user)
    return query.execute().data


def upsert_transactions(rows: list[dict]) -> None:
    """Insert transactions, ignoring duplicates via unique constraint."""
    if not rows:
        return
    get_client().table("transactions").upsert(
        rows, on_conflict="user,date,description,amount"
    ).execute()


def update_transaction_category(tx_id: str, category: str) -> None:
    get_client().table("transactions").update({"category": category}).eq(
        "id", tx_id
    ).execute()


def bulk_update_categories(updates: list[dict]) -> None:
    """updates: list of {id, category}"""
    client = get_client()
    for item in updates:
        client.table("transactions").update({"category": item["category"]}).eq(
            "id", item["id"]
        ).execute()


def delete_transactions(month: int, year: int, user: str) -> None:
    get_client().table("transactions").delete().eq("month", month).eq(
        "year", year
    ).eq("user", user).execute()


# ---------------------------------------------------------------------------
# Fixed Expenses
# ---------------------------------------------------------------------------

def get_fixed_expenses(user: str | None = None) -> list[dict]:
    client = get_client()
    query = client.table("fixed_expenses").select("*").order("name")
    if user:
        query = query.eq("user", user)
    return query.execute().data


def upsert_fixed_expense(row: dict) -> None:
    get_client().table("fixed_expenses").upsert(row).execute()


def delete_fixed_expense(expense_id: str) -> None:
    get_client().table("fixed_expenses").delete().eq("id", expense_id).execute()


def toggle_fixed_expense(expense_id: str, active: bool) -> None:
    get_client().table("fixed_expenses").update({"active": active}).eq(
        "id", expense_id
    ).execute()


# ---------------------------------------------------------------------------
# Monthly Summary
# ---------------------------------------------------------------------------

def get_monthly_summaries() -> list[dict]:
    return (
        get_client()
        .table("monthly_summary")
        .select("*")
        .order("year", desc=True)
        .order("month", desc=True)
        .execute()
        .data
    )


def get_monthly_summary(month: int, year: int) -> dict | None:
    rows = (
        get_client()
        .table("monthly_summary")
        .select("*")
        .eq("month", month)
        .eq("year", year)
        .execute()
        .data
    )
    return rows[0] if rows else None


def upsert_monthly_summary(row: dict) -> None:
    get_client().table("monthly_summary").upsert(
        row, on_conflict="month,year"
    ).execute()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def months_with_data() -> list[dict]:
    """Return distinct month/year combos that have transactions."""
    rows = (
        get_client()
        .table("transactions")
        .select("month,year")
        .execute()
        .data
    )
    seen: set[tuple[int, int]] = set()
    result: list[dict] = []
    for r in rows:
        key = (r["month"], r["year"])
        if key not in seen:
            seen.add(key)
            result.append({"month": r["month"], "year": r["year"]})
    result.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    return result


def has_uncategorized(month: int, year: int) -> bool:
    rows = (
        get_client()
        .table("transactions")
        .select("id")
        .eq("month", month)
        .eq("year", year)
        .eq("category", "uncategorized")
        .limit(1)
        .execute()
        .data
    )
    return len(rows) > 0
