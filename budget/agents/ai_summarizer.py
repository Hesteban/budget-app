"""
LLM-based monthly spending summary generator using the OpenAI Agents SDK.

The agent receives a structured spending summary for a calendar month and produces
a concise, friendly narrative report in English formatted as Markdown.
"""
from __future__ import annotations

from agents import Agent, Runner
from agents.tracing import trace

import budget.db as db


_SYSTEM_PROMPT = """
You are a household finance analyst for a two-person household (Laerke and Hector).
You receive a structured spending summary for a calendar month and produce a concise,
friendly narrative report in English formatted as Markdown.

The 'label' column in the transaction tables is already a human-readable interpretation
of the raw bank transaction text — use it directly in the report without further interpretation.

The report must include:
1. **Overview** — total common spend, total personal spend per person
2. **Laerke's personal spending** — brief breakdown.
3. **Hector's personal spending** — brief breakdown.
4. **Key observations** — 5 actionable or notable insights (e.g. unusually high category, trends).

Keep the tone friendly and factual. Use € for amounts.
"""

_agent = Agent(
    name="MonthlyFinanceSummarizer",
    model="gpt-4o-mini",
    instructions=_SYSTEM_PROMPT,
)


def _label(t: dict) -> str:
    """Return human-readable label, falls back to raw description if no reasoning."""
    label = (t["description"] + '|' + t.get("reasoning")) if t.get("reasoning") else t["description"]
    return (label).strip()


def generate_monthly_summary(month: int, year: int) -> str:
    """
    Generate a monthly spending summary narrative for the given month/year.
    
    Fetches all transactions and structures them for the LLM,
    and returns a markdown-formatted spending narrative.
    """
    transactions = db.get_transactions(month, year)

    # Build structured data block for the prompt
    common_tx = [t for t in transactions if t["category"] == "common" and t["amount"] < 0]
    laerke_personal = [
        t for t in transactions
        if t["user"] == "Laerke" and t["category"] == "personal" and t["amount"] < 0
    ]
    hector_personal = [
        t for t in transactions
        if t["user"] == "Hector" and t["category"] == "personal" and t["amount"] < 0
    ]

    # Enrich each transaction with a "label" field for the prompt
    for t in common_tx + laerke_personal + hector_personal:
        t["label"] = _label(t)

    common_total = sum(abs(t["amount"]) for t in common_tx)
    laerke_total = sum(abs(t["amount"]) for t in laerke_personal)
    hector_total = sum(abs(t["amount"]) for t in hector_personal)

    top_common = sorted(
        common_tx, key=lambda t: abs(t["amount"]), reverse=True
    )[:10]

    prompt = f"""
## Month: {month}/{year}

### Totals
- Common spend: €{common_total:.2f}
- Laerke personal: €{laerke_total:.2f}
- Hector personal: €{hector_total:.2f}

### Top Common Transactions
{_format_list(top_common, fields=["date", "label", "amount"])}

### Laerke Personal Transactions
{_format_list(laerke_personal, fields=["date", "label", "amount"])}

### Hector Personal Transactions
{_format_list(hector_personal, fields=["date", "label", "amount"])}
"""

    with trace("monthly_summary", metadata={"month": month, "year": year}):
        result = Runner.run_sync(_agent, prompt)

    return result.final_output  # markdown string


def _format_list(items: list[dict], fields: list[str]) -> str:
    """Format a list of dicts as a markdown table."""
    if not items:
        return "_(none)_"
    header = " | ".join(fields)
    rows = "\n".join(
        " | ".join(str(item.get(f, "")) for f in fields) for item in items
    )
    return f"{header}\n{rows}"


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    # Example usage — generate March 2026 summary from test data
    result = generate_monthly_summary(month=3, year=2026)
    print(result)
