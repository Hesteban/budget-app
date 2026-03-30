"""
Unit tests for budget/calculator.py

The calculator is tested in isolation by injecting a FakeRepository via
the `repo` fixture (defined in conftest.py). The module-level db functions
used by calculator.py are patched to delegate to the fixture's repo instance,
so no Supabase connection is ever made.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from budget import calculator
from budget.repository import FakeRepository
from tests.conftest import MONTH, YEAR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_calculator(repo: FakeRepository) -> dict:
    """Patch db module-level functions to use the given repo, then calculate."""
    with (
        patch("budget.calculator.db.get_transactions", side_effect=repo.get_transactions),
        patch("budget.calculator.db.get_fixed_expenses", side_effect=repo.get_fixed_expenses),
        patch("budget.calculator.db.upsert_monthly_summary", side_effect=repo.upsert_monthly_summary),
        patch("budget.calculator.db.get_monthly_summary", side_effect=repo.get_monthly_summary),
    ):
        return calculator.calculate_settlement(MONTH, YEAR)


def _run_ensure_month(repo: FakeRepository) -> None:
    with (
        patch("budget.calculator.db.get_monthly_summary", side_effect=repo.get_monthly_summary),
        patch("budget.calculator.db.upsert_monthly_summary", side_effect=repo.upsert_monthly_summary),
    ):
        calculator.ensure_month_exists(MONTH, YEAR)


def _run_get_or_calculate(repo: FakeRepository) -> dict | None:
    with (
        patch("budget.calculator.db.get_transactions", side_effect=repo.get_transactions),
        patch("budget.calculator.db.get_fixed_expenses", side_effect=repo.get_fixed_expenses),
        patch("budget.calculator.db.upsert_monthly_summary", side_effect=repo.upsert_monthly_summary),
        patch("budget.calculator.db.get_monthly_summary", side_effect=repo.get_monthly_summary),
    ):
        return calculator.get_or_calculate(MONTH, YEAR)


# ---------------------------------------------------------------------------
# Tests — settlement calculation
# ---------------------------------------------------------------------------

class TestCalculateSettlement:
    def test_returns_correct_keys(self, repo: FakeRepository) -> None:
        result = _run_calculator(repo)
        expected_keys = {
            "month", "year",
            "laerke_common", "hector_common",
            "fixed_laerke", "fixed_hector",
            "laerke_personal", "hector_personal",
            "balance", "who_pays_whom",
        }
        assert expected_keys == set(result.keys())

    def test_month_year_correct(self, repo: FakeRepository) -> None:
        result = _run_calculator(repo)
        assert result["month"] == MONTH
        assert result["year"] == YEAR

    def test_hector_common_sum(self, repo: FakeRepository) -> None:
        # From conftest: Mercadona 85.30 + Netflix 15.99 + Ikea 60.50
        #                + El Corte Ingles 25.00 + Carrefour 47.60 = 234.39
        result = _run_calculator(repo)
        assert result["hector_common"] == pytest.approx(234.39, abs=0.01)

    def test_laerke_common_sum(self, repo: FakeRepository) -> None:
        # From conftest: Netto 72.40 + IKEA 44.90 + Bioparc 28.00 + Lidl 55.10 = 200.40
        # Netto duplicate is dropped by upsert, so counted once only.
        result = _run_calculator(repo)
        assert result["laerke_common"] == pytest.approx(200.40, abs=0.01)

    def test_fixed_expenses_only_active(self, repo: FakeRepository) -> None:
        # Hector active fixed: 250.00 + 45.00 = 295.00
        # Laerke active fixed: 180.00 only (Phone plan is inactive)
        result = _run_calculator(repo)
        assert result["fixed_hector"] == pytest.approx(295.00, abs=0.01)
        assert result["fixed_laerke"] == pytest.approx(180.00, abs=0.01)

    def test_balance_formula(self, repo: FakeRepository) -> None:
        result = _run_calculator(repo)
        total_laerke = result["laerke_common"] + result["fixed_laerke"]
        total_hector = result["hector_common"] + result["fixed_hector"]
        expected_balance = total_laerke - (total_laerke + total_hector) / 2
        assert result["balance"] == pytest.approx(expected_balance, abs=0.01)

    def test_who_pays_whom_text(self, repo: FakeRepository) -> None:
        result = _run_calculator(repo)
        wph = result["who_pays_whom"]
        balance = result["balance"]
        if balance > 0.005:
            assert wph.startswith("Hector pays Laerke")
        elif balance < -0.005:
            assert wph.startswith("Laerke pays Hector")
        else:
            assert wph == "All settled ✓"

    def test_result_persisted_to_repo(self, repo: FakeRepository) -> None:
        _run_calculator(repo)
        saved = repo.get_monthly_summary(MONTH, YEAR)
        assert saved is not None
        assert saved["month"] == MONTH
        assert saved["year"] == YEAR

    def test_personal_not_included_in_balance(self, repo: FakeRepository) -> None:
        """Personal expenses are tracked but must NOT affect balance."""
        result_before = _run_calculator(repo)
        balance_before = result_before["balance"]

        # Add a large personal expense for Hector — balance must stay the same
        repo.upsert_transactions([{
            "user": "Hector", "month": MONTH, "year": YEAR,
            "date": "2026-03-29", "description": "Personal splurge",
            "amount": -999.00, "source": "card", "category": "personal",
        }])
        result_after = _run_calculator(repo)
        assert result_after["balance"] == pytest.approx(balance_before, abs=0.01)


# ---------------------------------------------------------------------------
# Tests — ensure_month_exists
# ---------------------------------------------------------------------------

class TestEnsureMonthExists:
    def test_creates_seed_row_when_missing(self, repo: FakeRepository) -> None:
        assert repo.get_monthly_summary(1, 2025) is None
        with (
            patch("budget.calculator.db.get_monthly_summary", side_effect=repo.get_monthly_summary),
            patch("budget.calculator.db.upsert_monthly_summary", side_effect=repo.upsert_monthly_summary),
        ):
            calculator.ensure_month_exists(1, 2025)
        row = repo.get_monthly_summary(1, 2025)
        assert row is not None
        assert row["balance"] == 0

    def test_does_not_overwrite_existing(self, repo: FakeRepository) -> None:
        _run_calculator(repo)  # persists a real summary for MONTH/YEAR
        saved = repo.get_monthly_summary(MONTH, YEAR)
        original_balance = saved["balance"]

        _run_ensure_month(repo)  # should be a no-op
        after = repo.get_monthly_summary(MONTH, YEAR)
        assert after["balance"] == original_balance


# ---------------------------------------------------------------------------
# Tests — get_or_calculate
# ---------------------------------------------------------------------------

class TestGetOrCalculate:
    def test_returns_none_when_no_transactions(self) -> None:
        empty_repo = FakeRepository()
        result = None
        with (
            patch("budget.calculator.db.get_transactions", side_effect=empty_repo.get_transactions),
            patch("budget.calculator.db.get_fixed_expenses", side_effect=empty_repo.get_fixed_expenses),
            patch("budget.calculator.db.upsert_monthly_summary", side_effect=empty_repo.upsert_monthly_summary),
            patch("budget.calculator.db.get_monthly_summary", side_effect=empty_repo.get_monthly_summary),
        ):
            result = calculator.get_or_calculate(MONTH, YEAR)
        assert result is None

    def test_returns_dict_when_transactions_exist(self, repo: FakeRepository) -> None:
        result = _run_get_or_calculate(repo)
        assert result is not None
        assert "balance" in result


# ---------------------------------------------------------------------------
# Tests — settled edge case
# ---------------------------------------------------------------------------

class TestSettledEdgeCase:
    def test_all_settled_when_equal_contributions(self) -> None:
        r = FakeRepository()
        # Both users contribute exactly the same common amount, no fixed expenses
        for user in ("Hector", "Laerke"):
            r.upsert_transactions([{
                "user": user, "month": MONTH, "year": YEAR,
                "date": f"2026-03-0{1 if user == 'Hector' else 2}",
                "description": "Equal share", "amount": -100.00,
                "source": "account", "category": "common",
            }])
        with (
            patch("budget.calculator.db.get_transactions", side_effect=r.get_transactions),
            patch("budget.calculator.db.get_fixed_expenses", side_effect=r.get_fixed_expenses),
            patch("budget.calculator.db.upsert_monthly_summary", side_effect=r.upsert_monthly_summary),
            patch("budget.calculator.db.get_monthly_summary", side_effect=r.get_monthly_summary),
        ):
            result = calculator.calculate_settlement(MONTH, YEAR)
        assert result["who_pays_whom"] == "All settled ✓"
        assert abs(result["balance"]) <= 0.005
