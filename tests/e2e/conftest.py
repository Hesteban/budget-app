"""
Shared fixtures for Playwright E2E tests.

Provides:
  base_url          — read from BASE_URL env var (default: http://localhost:8501)
  transactions_page — Playwright Page already on the Transactions page,
                      navigated via the sidebar link (resilient to URL slug changes)
"""
from __future__ import annotations

import calendar
import os

import pytest
from playwright.sync_api import Page, expect

from tests.seed_data import MONTH, YEAR


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    return os.getenv("BASE_URL", "http://localhost:8501")


@pytest.fixture()
def transactions_page(page: Page, base_url: str) -> Page:
    """
    Navigate to the home page, wait for the auto-login rerun to settle,
    then click the '💳 Transactions' sidebar link and select the seed
    data month/year in the sidebar filters.
    """
    page.goto(base_url)

    # Wait for the auto-login rerun to complete — sidebar title is the anchor
    expect(page.get_by_text("Budget App 💶").first).to_be_visible(timeout=15_000)

    # Click the Transactions nav link in the sidebar
    page.get_by_role("link", name="Transactions").click()

    # Wait for the page heading to confirm navigation succeeded
    expect(page.get_by_role("heading", name="💳 Transactions", exact=False)).to_be_visible(
        timeout=15_000
    )

    # Select the seed data month in the Month filter (defaults to current month)
    month_name = calendar.month_name[MONTH]
    month_select = page.locator('[data-testid="stSelectbox"]').first
    month_select.click()
    page.get_by_role("option", name=month_name, exact=True).click()

    # Wait for the page to rerun with the selected month
    expect(
        page.get_by_text(f"{month_name} {YEAR}", exact=False)
    ).to_be_visible(timeout=15_000)

    return page
