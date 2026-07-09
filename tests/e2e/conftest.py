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
import subprocess
import sys
import time
from collections.abc import Iterator

import urllib.request


import pytest

from playwright.sync_api import Page, expect
from budget import db, calculator
from tests.seed_data import FIXED_EXPENSES, HECTOR_TRANSACTIONS, LAERKE_TRANSACTIONS, MONTH, YEAR, make_tx

# To point to the fake de when calling the get_repo before each db method
os.environ.setdefault("APP_ENV", "test")


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    return os.getenv("BASE_URL", "http://localhost:8501")


@pytest.fixture(scope="session")
def expected_settlement() -> dict:                                                                                                                                                                               
    if not db.get_transactions(MONTH, YEAR):                                                                                                                                                                                              
        db.upsert_transactions([make_tx("Hector", tx) for tx in HECTOR_TRANSACTIONS])                                                                                                                                                                            
        db.upsert_transactions([make_tx("Laerke", tx) for tx in LAERKE_TRANSACTIONS])
        for fe in FIXED_EXPENSES:                                                                                                                                                                                                       
            db.upsert_fixed_expense(fe)                                                                                                                                                                                                               
    return calculator.calculate_settlement(MONTH, YEAR)

@pytest.fixture(scope="session", autouse=True)
def streamlit_server(base_url: str) -> Iterator[None]:
    """
    Start the Streamlit server for the e2e suite, wait until it is ready,
    then terminate it after the session ends.
    """
    env = os.environ.copy()
    env["APP_ENV"] = "test"

    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "main.py", "--server.port=8501"],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for the server to become ready
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base_url, timeout=1):
                break
        except Exception:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError(f"Streamlit server did not start within 30s ({base_url})")

    yield

    # Teardown
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()

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

@pytest.fixture()
def summary_page(page: Page, base_url: str) -> Page:
    """
    Navigate to the home page, wait for the auto-login rerun to settle,
    then click the '📊 Summary' sidebar link and select the seed
    data month/year in the sidebar filters.
    """
    page.goto(base_url)

    # Wait for the auto-login rerun to complete — sidebar title is the anchor
    expect(page.get_by_text("Budget App 💶").first).to_be_visible(timeout=15_000)

    # Click the Transactions nav link in the sidebar
    page.get_by_role("link", name="Summary", exact=True).click()

    expect(page.get_by_role("heading", name="📊 Monthly Summary", exact=False)).to_be_visible(
        timeout=15_000
    )
    # Select the seed data month in the Month filter (defaults to current month)
    month_name = calendar.month_name[MONTH]
    month_select = page.locator('[data-baseweb="select"]').first
    month_select.click()
    page.get_by_role("option", name=month_name, exact=True).click()

    # Wait for the page to rerun with the selected month
    expect(
        page.get_by_text(f"{month_name} {YEAR}", exact=False)
    ).to_be_visible(timeout=15_000)

    return page

@pytest.fixture()
def assistant_page(page: Page, base_url: str) -> Page:
    """
    Navigate to the home page, wait for the auto-login rerun to settle,
    then click the '💬 Assistant' sidebar link.
    """
    page.goto(base_url)

    # Wait for the auto-login rerun to complete — sidebar title is the anchor
    expect(page.get_by_text("Budget App 💶").first).to_be_visible(timeout=15_000)

    # Click the Transactions nav link in the sidebar
    page.get_by_role("link", name="Assistant").click()

    # Wait for the page heading to confirm navigation succeeded
    expect(page.get_by_role("heading", name="💬 Budget Assistant", exact=False)).to_be_visible(
        timeout=15_000
    )

    return page
