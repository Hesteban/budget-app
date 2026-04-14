"""
BudgetRepository protocol and FakeRepository in-memory implementation.

The Protocol defines the contract that both SupabaseRepository (production)
and FakeRepository (tests / APP_ENV=test) must satisfy.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


# Protocol — the contract every repository implementation must satisfy
@runtime_checkable
class BudgetRepository(Protocol):

    # --- Transactions ---

    def get_transactions(
        self, month: int, year: int, user: str | None = None
    ) -> list[dict]: ...

    def upsert_transactions(self, rows: list[dict]) -> None: ...

    def update_transaction_category(self, tx_id: str, category: str) -> None: ...

    def bulk_update_categories(self, updates: list[dict]) -> None: ...

    def delete_transactions(self, month: int, year: int, user: str) -> None: ...

    # --- Fixed Expenses ---

    def get_fixed_expenses(self, user: str | None = None) -> list[dict]: ...

    def upsert_fixed_expense(self, row: dict) -> None: ...

    def delete_fixed_expense(self, expense_id: str) -> None: ...

    def toggle_fixed_expense(self, expense_id: str, active: bool) -> None: ...

    # --- Monthly Summary ---

    def get_monthly_summaries(self) -> list[dict]: ...

    def get_monthly_summary(self, month: int, year: int) -> dict | None: ...

    def upsert_monthly_summary(self, row: dict) -> None: ...

    # --- Monthly Reports (AI-generated) ---

    def get_monthly_report(self, month: int, year: int) -> str | None: ...

    def upsert_monthly_report(self, month: int, year: int, content: str) -> None: ...

    # --- Helpers ---

    def months_with_data(self) -> list[dict]: ...

    def has_uncategorized(self, month: int, year: int) -> bool: ...
