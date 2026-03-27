"""
LLM-based transaction categorizer using the OpenAI Agents SDK.

The agent receives a single transaction (description, amount, source) and
returns a structured CategoryResult.  Only results whose self-reported
confidence meets CONFIDENCE_THRESHOLD are auto-applied; the rest remain
'uncategorized' for manual review.
"""
from __future__ import annotations

from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------

ValidCategory = Literal["personal", "common", "covered", "uncategorized"]


class CategoryResult(BaseModel):
    category: ValidCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ---------------------------------------------------------------------------
# Agent (module-level singleton — reused across calls)
# ---------------------------------------------------------------------------

_agent = Agent(
    name="TransactionCategorizer",
    model="gpt-4o-mini",
    instructions="""
You categorize Spanish bank transactions for a couple tracking shared monthly expenses.

The couple is Laerke and Hector. They split common household expenses 50/50.

Categories:
- 'common': Shared expense both people benefit from (groceries, rent, utilities,
  streaming services, restaurants together, household supplies, etc.)
- 'personal': Expense for one person only (clothing, personal health,
  solo transport, individual hobbies, etc.)
- 'covered': Already reimbursed or handled outside the app; should be excluded
  from the settlement calculation.
- 'uncategorized': Genuinely unclear from the description alone; insufficient
  information to decide.

You will receive: description (bank transaction text), amount in euros (negative
means debit/spending, positive means credit/income), and source ('card' or
'account').

Respond with the most likely category, a confidence score from 0.0 to 1.0, and
a brief one-sentence reasoning.
""",
    output_type=CategoryResult,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def categorize_transaction(
    description: str, amount: float, source: str
) -> CategoryResult:
    """
    Categorize a single transaction synchronously.
    Returns a CategoryResult with category, confidence, and reasoning.
    """
    prompt = (
        f"Description: {description}\n"
        f"Amount: €{amount:.2f}\n"
        f"Source: {source}"
    )
    result = Runner.run_sync(_agent, prompt)
    return result.final_output
