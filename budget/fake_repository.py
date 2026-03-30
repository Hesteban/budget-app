import copy
import uuid

class FakeRepository:
    """
    Stateful in-memory store that mirrors the Supabase schema.
    Each instance is independent — use a fresh one per test.

    Upsert dedup key for transactions: (user, date, description, amount, source)
    Upsert dedup key for fixed_expenses: (id) — new row if no id present
    Upsert dedup key for monthly_summary: (month, year)
    """

    def __init__(self) -> None:
        self._transactions: list[dict] = []
        self._fixed_expenses: list[dict] = []
        self._monthly_summaries: list[dict] = []

    # Transactions
    def get_transactions(
        self, month: int, year: int, user: str | None = None
    ) -> list[dict]:
        rows = [
            t for t in self._transactions
            if t["month"] == month and t["year"] == year
        ]
        if user:
            rows = [t for t in rows if t["user"] == user]
        return sorted(rows, key=lambda t: t["date"], reverse=True)

    def upsert_transactions(self, rows: list[dict]) -> None:
        """Insert rows, skipping exact duplicates (same dedup key as DB)."""
        def dedup_key(r: dict) -> tuple:
            return (r["user"], r["date"], r["description"], r["amount"], r["source"])

        existing_keys = {dedup_key(t) for t in self._transactions}
        for row in rows:
            if dedup_key(row) not in existing_keys:
                record = copy.deepcopy(row)
                record.setdefault("id", str(uuid.uuid4()))
                record.setdefault("category", "uncategorized")
                self._transactions.append(record)
                existing_keys.add(dedup_key(record))

    def update_transaction_category(self, tx_id: str, category: str) -> None:
        for t in self._transactions:
            if t["id"] == tx_id:
                t["category"] = category
                return

    def bulk_update_categories(self, updates: list[dict]) -> None:
        for item in updates:
            self.update_transaction_category(item["id"], item["category"])

    def delete_transactions(self, month: int, year: int, user: str) -> None:
        self._transactions = [
            t for t in self._transactions
            if not (t["month"] == month and t["year"] == year and t["user"] == user)
        ]

    # Fixed Expenses
    def get_fixed_expenses(self, user: str | None = None) -> list[dict]:
        rows = list(self._fixed_expenses)
        if user:
            rows = [f for f in rows if f["user"] == user]
        return sorted(rows, key=lambda f: f["name"])

    def upsert_fixed_expense(self, row: dict) -> None:
        record = copy.deepcopy(row)
        expense_id = record.get("id")
        if expense_id:
            for i, f in enumerate(self._fixed_expenses):
                if f["id"] == expense_id:
                    self._fixed_expenses[i] = record
                    return
        record["id"] = str(uuid.uuid4())
        self._fixed_expenses.append(record)

    def delete_fixed_expense(self, expense_id: str) -> None:
        self._fixed_expenses = [
            f for f in self._fixed_expenses if f["id"] != expense_id
        ]

    def toggle_fixed_expense(self, expense_id: str, active: bool) -> None:
        for f in self._fixed_expenses:
            if f["id"] == expense_id:
                f["active"] = active
                return

    # Monthly Summary
    def get_monthly_summaries(self) -> list[dict]:
        return sorted(
            self._monthly_summaries,
            key=lambda s: (s["year"], s["month"]),
            reverse=True,
        )

    def get_monthly_summary(self, month: int, year: int) -> dict | None:
        for s in self._monthly_summaries:
            if s["month"] == month and s["year"] == year:
                return copy.deepcopy(s)
        return None

    def upsert_monthly_summary(self, row: dict) -> None:
        record = copy.deepcopy(row)
        record.setdefault("id", str(uuid.uuid4()))
        for i, s in enumerate(self._monthly_summaries):
            if s["month"] == record["month"] and s["year"] == record["year"]:
                self._monthly_summaries[i] = record
                return
        self._monthly_summaries.append(record)

    # Helpers
    def months_with_data(self) -> list[dict]:
        seen: set[tuple[int, int]] = set()
        result: list[dict] = []
        for t in self._transactions:
            key = (t["month"], t["year"])
            if key not in seen:
                seen.add(key)
                result.append({"month": t["month"], "year": t["year"]})
        result.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
        return result

    def has_uncategorized(self, month: int, year: int) -> bool:
        return any(
            t["month"] == month and t["year"] == year and t["category"] == "uncategorized"
            for t in self._transactions
        )
