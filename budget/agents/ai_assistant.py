"""
Conversational AI assistant for budget data using the OpenAI Agents SDK.

The agent has read-only access to budget data via @function_tool wrappers.
stream_response() bridges async Runner.run_streamed to a sync generator
suitable for st.write_stream.
"""
from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Generator

from agents import Agent, Runner, function_tool
from openai.types.responses import ResponseTextDeltaEvent

import budget.db as db


_SENTINEL = object()

_SYSTEM_PROMPT = """You are a helpful financial assistant for a two-person household \
(Laerke and Hector). They share a home in Spain and split common household expenses 50/50.

You have read-only access to their budget data via tools. Always fetch real data before \
answering questions about spending, settlements, or transactions.

Data model:
- Transactions: bank imports per month. amount is negative for expenses, positive for income.
  Fields: user, date, description, amount, source ('card'/'account'), category, reasoning.
- Categories: 'common' (shared 50/50), 'personal' (individual), 'covered', 'uncategorized'.
- Monthly settlement summary: who paid what in common expenses and who owes whom.
- Fixed expenses: recurring monthly costs per user.

Rules:
- Use months_with_data first if unsure which months have been imported.
- When asked about a month without a year, assume 2026.
- Use absolute values when presenting expense totals (amounts are stored as negatives).
- Format all amounts as €X.XX. Be concise and friendly.
- If no data exists for a requested period, say so clearly."""


@function_tool(strict_mode=False)
def get_transactions(month: int, year: int, user: str | None = None) -> list[dict]:
    """Fetch all transactions for a given month and year, optionally filtered by user
    ('Laerke' or 'Hector'). Returns list of dicts with keys: user, date, description,
    amount, category, source, reasoning. Amounts are negative for expenses."""
    return db.get_transactions(month, year, user)


@function_tool
def get_monthly_summary(month: int, year: int) -> dict | None:
    """Fetch the settlement summary for a specific month/year. Returns keys:
    laerke_common, hector_common, fixed_laerke, fixed_hector, laerke_personal,
    hector_personal, balance, who_pays_whom. Returns null if no data exists."""
    return db.get_monthly_summary(month, year)


@function_tool
def get_monthly_summaries() -> list[dict]:
    """Fetch settlement summaries for all months that have data, sorted newest first.
    Use this to answer trend or year-overview questions."""
    return db.get_monthly_summaries()


@function_tool(strict_mode=False)
def get_fixed_expenses(user: str | None = None) -> list[dict]:
    """Fetch recurring fixed expenses, optionally filtered by user ('Laerke' or 'Hector').
    Returns list of dicts with keys: user, name, amount, active."""
    return db.get_fixed_expenses(user)


@function_tool
def months_with_data() -> list[dict]:
    """Return a list of {month, year} dicts for every month that has at least one
    transaction, sorted newest first. Call this first to orient yourself."""
    return db.months_with_data()


_agent = Agent(
    name="BudgetAssistant",
    model="gpt-4o-mini",
    instructions=_SYSTEM_PROMPT,
    tools=[
        get_transactions,
        get_monthly_summary,
        get_monthly_summaries,
        get_fixed_expenses,
        months_with_data,
    ],
)


async def _stream_to_queue(messages: list[dict], q: queue.Queue) -> None:
    try:
        result = Runner.run_streamed(_agent, input=messages)
        async for event in result.stream_events():
            if (
                event.type == "raw_response_event"
                and isinstance(event.data, ResponseTextDeltaEvent)
            ):
                q.put(event.data.delta)
    except Exception as exc:
        q.put(exc)
    finally:
        q.put(_SENTINEL)


def stream_response(messages: list[dict]) -> Generator[str, None, None]:
    """Sync generator yielding text token deltas. Safe to pass directly to st.write_stream.

    Bridges async Runner.run_streamed to Streamlit's synchronous execution model
    via a daemon thread and a queue. Tool calls are executed transparently by the
    SDK and never appear in the yielded output.
    """
    q: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=asyncio.run,
        args=(_stream_to_queue(messages, q),),
        daemon=True,
    )
    thread.start()
    try:
        while True:
            item = q.get()
            if item is _SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        thread.join(timeout=2.0)
