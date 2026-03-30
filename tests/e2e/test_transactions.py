"""
E2E — Transactions page happy path.

Scenario:
  Given I am logged in (auto-login as Héctor via APP_ENV=test)
  When  I navigate to the Transactions page
  Then  I can see Hector's transactions for March 2026
"""
from __future__ import annotations

import calendar

import pytest
from playwright.sync_api import Page, expect

from tests.seed_data import HECTOR_TRANSACTIONS, LAERKE_TRANSACTIONS, MONTH, YEAR


@pytest.mark.e2e
def test_transactions_page_shows_march_2026_data(transactions_page: Page) -> None:
    """Happy path: Transactions page renders March 2026 transactions."""
    page = transactions_page

    heading = page.get_by_role("heading", name="💳 Transactions", exact=False)
    expect(heading).to_be_visible()

    month_name = calendar.month_name[MONTH]  # "March"
    expect(page.get_by_text(f"{month_name} {YEAR}", exact=False)).to_be_visible()

    total_transactions = len(HECTOR_TRANSACTIONS) + len(LAERKE_TRANSACTIONS) - 1 # There is one duplicated to test upsert deduplication
    expect(
        transactions_page.get_by_text(
            f"{month_name} {YEAR} — {total_transactions} transaction(s) loaded",
            exact=False,
        )
    ).to_be_visible(timeout=10_000)

    # Assert the dataframe grid container is rendered
    expect(transactions_page.locator(".stDataFrameGlideDataEditor")).to_be_visible()
    
    expect(
        transactions_page.get_by_text(
            "Common: €434.79", exact=False
        )
    ).to_be_visible(timeout=10_000)

    expect(
        transactions_page.get_by_text("Personal: €148.49", exact=False)
    ).to_be_visible(timeout=10_000)
    expect(
        transactions_page.get_by_text("Uncategorised: 0", exact=False)
    ).to_be_visible(timeout=10_000)