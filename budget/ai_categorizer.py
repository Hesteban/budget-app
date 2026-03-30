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
from agents.tracing import trace
from pydantic import BaseModel, Field


CONFIDENCE_THRESHOLD = 0.85

ValidCategory = Literal["personal", "common", "covered", "uncategorized"]


class CategoryResult(BaseModel):
    category: ValidCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


_agent = Agent(
    name="TransactionCategorizer",
    model="gpt-4o-mini",
    instructions="""
You categorize Spanish bank transactions for a couple tracking shared monthly expenses.
They split common household expenses 50/50.

Categories:
- 'common': Shared expense both people benefit from (groceries, rent, utilities,
  streaming services, restaurants together, household supplies, petrol stations;
  Some examples: PANADERIA, BM (supermarket), DIA (supermarket), ALDI (supermarket), E.S BECERRIl (meaming Estacion de servicio gasolina), FCIA (meaning Farmacia) )
- 'personal': Expense for one person only (clothing, personal health, bank operations
  solo transport, individual hobbies, etc.)
- 'covered': This is not possible to categorize by an LLM , so just not use it
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


def categorize_transaction( description: str, amount: float, source: str) -> CategoryResult:
    """
    Categorize a single transaction synchronously.
    Returns a CategoryResult with category, confidence, and reasoning.
    """
    prompt = (
        f"Description: {description}\n"
        f"Amount: €{amount:.2f}\n"
        f"Source: {source}"
    )
    with trace("categorize_transaction", metadata={"description": description}):
        result = Runner.run_sync(_agent, prompt)
    return result.final_output
