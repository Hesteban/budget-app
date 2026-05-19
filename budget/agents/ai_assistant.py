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
- If no data exists for a requested period, say so clearly.
- Use query_transactions with sort_by='amount' and limit=N for "top N" expense questions (default is largest first).
- Use get_category_totals when the question is about totals/breakdown by category.
- Use get_monthly_summary for settlement/balance questions.
- Only use query_transactions with no filters if the user explicitly asks to see all transactions."""


@function_tool(strict_mode=False)
def query_transactions(
    month: int | None = None,
    year: int | None = None,
    user: str | None = None,
    category: str | None = None,
    sort_by: str | None = None,
    ascending: bool | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query transactions with optional filters. Returns list of dicts with keys:
    user, date, description, amount, category, source, reasoning.
    - month/year: filter by specific month (required for meaningful queries)
    - user: 'Laerke' or 'Hector' to filter by user
    - category: 'common', 'personal', 'covered', or 'uncategorized'
    - sort_by: 'amount' (sort by absolute value) or 'date'
    - ascending: True for smallest/oldest first, False for largest/most recent first. Defaults to False.
    - limit: return only N results (use for "top N" questions)
    Amounts are negative for expenses; use absolute values when presenting totals."""
    if month is None or year is None:
        return []
    transactions = db.get_transactions(month, year, user)
    if category:
        transactions = [t for t in transactions if t["category"] == category]
    if ascending is None:
        ascending = False
    if sort_by == "amount":
        transactions = sorted(transactions, key=lambda t: abs(t["amount"]), reverse=not ascending)
    elif sort_by == "date":
        transactions = sorted(transactions, key=lambda t: t["date"], reverse=not ascending)
    if limit is not None:
        transactions = transactions[:limit]
    return transactions


@function_tool
def get_category_totals(month: int, year: int, user: str | None = None) -> dict:
    """Get spending totals broken down by category for a month.
    Returns dict with keys: common, personal, covered, uncategorized, grand_total.
    - user: 'Laerke', 'Hector', or None for combined totals.
    Amounts are negative for expenses; values in response are absolute."""
    transactions = db.get_transactions(month, year, user)
    totals = {"common": 0.0, "personal": 0.0, "covered": 0.0, "uncategorized": 0.0}
    for t in transactions:
        cat = t.get("category")
        if cat in totals and t["amount"] < 0:
            totals[cat] += abs(t["amount"])
    totals["grand_total"] = sum(totals.values())
    return totals


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
        query_transactions,
        get_category_totals,
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
