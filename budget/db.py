"""
Supabase database client and all CRUD operations.

Production code uses SupabaseRepository (wraps supabase-py).
When APP_ENV=test the module-level functions delegate to FakeRepository
so no real Supabase credentials are needed during testing.

All pages and calculator.py call the module-level functions as before —
zero changes needed in callers (Option B delegation pattern).
"""
from __future__ import annotations

import os

import streamlit as st
from supabase import create_client, Client

from budget.budget_repository import BudgetRepository
from budget.fake_repository import FakeRepository


@st.cache_resource
def _get_supabase_client() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)


# Keep old name for any external references
get_client = _get_supabase_client


class SupabaseRepository:
    """Thin wrapper around the supabase-py client."""

    def _client(self) -> Client:
        return _get_supabase_client()

    # --- Transactions ---

    def get_transactions(
        self, month: int, year: int, user: str | None = None
    ) -> list[dict]:
        query = (
            self._client().table("transactions")
            .select("*")
            .eq("month", month)
            .eq("year", year)
            .order("date", desc=True)
        )
        if user:
            query = query.eq("user", user)
        return query.execute().data

    def upsert_transactions(self, rows: list[dict]) -> None:
        if not rows:
            return
        self._client().table("transactions").upsert(
            rows, on_conflict="user,date,description,amount,source"
        ).execute()

    def update_transaction_category(self, tx_id: str, category: str) -> None:
        self._client().table("transactions").update({"category": category}).eq(
            "id", tx_id
        ).execute()

    def bulk_update_categories(self, updates: list[dict]) -> None:
        for item in updates:
            payload = {"category": item["category"]}
            if "reasoning" in item:
                payload["reasoning"] = item["reasoning"][:300]
            self._client().table("transactions").update(
                payload
            ).eq("id", item["id"]).execute()

    def delete_transactions(self, month: int, year: int, user: str) -> None:
        self._client().table("transactions").delete().eq("month", month).eq(
            "year", year
        ).eq("user", user).execute()

    # --- Fixed Expenses ---

    def get_fixed_expenses(self, user: str | None = None) -> list[dict]:
        query = self._client().table("fixed_expenses").select("*").order("name")
        if user:
            query = query.eq("user", user)
        return query.execute().data

    def upsert_fixed_expense(self, row: dict) -> None:
        self._client().table("fixed_expenses").upsert(row).execute()

    def delete_fixed_expense(self, expense_id: str) -> None:
        self._client().table("fixed_expenses").delete().eq(
            "id", expense_id
        ).execute()

    def toggle_fixed_expense(self, expense_id: str, active: bool) -> None:
        self._client().table("fixed_expenses").update({"active": active}).eq(
            "id", expense_id
        ).execute()

    # --- Monthly Summary ---

    def get_monthly_summaries(self) -> list[dict]:
        return (
            self._client()
            .table("monthly_summary")
            .select("*")
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
            .data
        )

    def get_monthly_summary(self, month: int, year: int) -> dict | None:
        rows = (
            self._client()
            .table("monthly_summary")
            .select("*")
            .eq("month", month)
            .eq("year", year)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def upsert_monthly_summary(self, row: dict) -> None:
        self._client().table("monthly_summary").upsert(
            row, on_conflict="month,year"
        ).execute()

    # --- Helpers ---

    def months_with_data(self) -> list[dict]:
        rows = (
            self._client()
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

    def has_uncategorized(self, month: int, year: int) -> bool:
        rows = (
            self._client()
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

    # --- Monthly Reports ---

    def get_monthly_report(self, month: int, year: int) -> str | None:
        result = (
            self._client().table("monthly_reports")
            .select("content")
            .eq("month", month)
            .eq("year", year)
            .maybe_single()
            .execute()
        )
        if result is None:
            return None

        if not result.data:
            return None

        return result.data.get("content")

    def upsert_monthly_report(self, month: int, year: int, content: str) -> None:
        self._client().table("monthly_reports").upsert(
            {"month": month, "year": year, "content": content},
            on_conflict="month,year",
        ).execute()



# Repository factory
# Module-level singleton for the fake repo so all callers in a test session
# share the same in-memory state (mirrors how Supabase is a shared service).
_fake_repo: FakeRepository | None = None


def get_repo() -> BudgetRepository:
    """
    Return the active repository implementation.

    - APP_ENV=test  →  FakeRepository (in-memory, no network)
    - otherwise     →  SupabaseRepository (production)
    """
    global _fake_repo
    if os.getenv("APP_ENV") == "test":
        if _fake_repo is None:
            _fake_repo = FakeRepository()
        return _fake_repo
    return SupabaseRepository()


def reset_fake_repo() -> None:
    """
    Replace the module-level FakeRepository with a fresh empty instance.
    Call this in test teardown or conftest fixtures to isolate tests.
    """
    global _fake_repo
    _fake_repo = FakeRepository()


# ---------------------------------------------------------------------------
# Module-level API — delegates to get_repo() (Option B)
# Pages and calculator.py call these directly; no changes needed there.
# ---------------------------------------------------------------------------

def get_transactions(month: int, year: int, user: str | None = None) -> list[dict]:
    return get_repo().get_transactions(month, year, user)


def upsert_transactions(rows: list[dict]) -> None:
    get_repo().upsert_transactions(rows)


def update_transaction_category(tx_id: str, category: str) -> None:
    get_repo().update_transaction_category(tx_id, category)


def bulk_update_categories(updates: list[dict]) -> None:
    get_repo().bulk_update_categories(updates)


def delete_transactions(month: int, year: int, user: str) -> None:
    get_repo().delete_transactions(month, year, user)


def get_fixed_expenses(user: str | None = None) -> list[dict]:
    return get_repo().get_fixed_expenses(user)


def upsert_fixed_expense(row: dict) -> None:
    get_repo().upsert_fixed_expense(row)


def delete_fixed_expense(expense_id: str) -> None:
    get_repo().delete_fixed_expense(expense_id)


def toggle_fixed_expense(expense_id: str, active: bool) -> None:
    get_repo().toggle_fixed_expense(expense_id, active)


def get_monthly_summaries() -> list[dict]:
    return get_repo().get_monthly_summaries()


def get_monthly_summary(month: int, year: int) -> dict | None:
    return get_repo().get_monthly_summary(month, year)


def upsert_monthly_summary(row: dict) -> None:
    get_repo().upsert_monthly_summary(row)


def months_with_data() -> list[dict]:
    return get_repo().months_with_data()


def has_uncategorized(month: int, year: int) -> bool:
    return get_repo().has_uncategorized(month, year)


def get_monthly_report(month: int, year: int) -> str | None:
    return get_repo().get_monthly_report(month, year)


def upsert_monthly_report(month: int, year: int, content: str) -> None:
    get_repo().upsert_monthly_report(month, year, content)
