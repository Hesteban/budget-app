"""
E2E — Summary 
"""
from __future__ import annotations


import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_summary_page_shows_march_2026_report(summary_page: Page, expected_settlement: dict) -> None:
    """Happy path: Summary page renders March 2026 report."""
    page = summary_page

    # Validate tabs
    tabs = page.get_by_role('tab')
    expect(tabs).to_have_count(3)

    expect(page.get_by_role('tab', name="📊 Settlement")).to_have_attribute('aria-selected', 'true')
    expect(page.get_by_role('tab', name="📈 Trends")).to_have_attribute('aria-selected', 'false')
    expect(page.get_by_role('tab', name="📝 AI Report")).to_have_attribute('aria-selected', 'false')

    # Current tab = Settlement
    tab_title = page.get_by_role('heading', level=3, name="Settlement — March")
    expect(tab_title).to_be_visible()

    # expect(page.get_by_text('Laerke pays Hector')).to_be_visible()
    expect(page.get_by_text(expected_settlement["who_pays_whom"])).to_be_visible()

    expect(page.get_by_role('heading', level=3, name="Breakdown")).to_be_visible()