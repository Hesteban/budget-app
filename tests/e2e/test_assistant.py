"""
E2E — Assitant
"""
from __future__ import annotations


import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_assistant(assistant_page: Page) -> None:
    """Happy path: Assistant answer questions in the chat"""
    page = assistant_page

    expect(page.get_by_role('heading', level=1, name="Budget Assistant")).to_be_visible()

    chat_input = page.locator('[data-testid="stChatInputTextArea"]')
    chat_input.fill("Can you give the balance for march in one line")
    chat_input.press("Enter")

    # .last targets the assistant bubble (user bubble is first)
    ai_response = page.locator('[data-testid="stChatMessageContent"]').last
    expect(ai_response).to_be_visible(timeout=15_000)
    expect(ai_response).to_contain_text("Hector €74.50")
