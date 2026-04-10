"""
LLM-based transaction categorizer using the OpenAI Agents SDK.

The agent receives a single transaction (description, amount, source) and
returns a structured CategoryResult.  Only results whose self-reported
confidence meets CONFIDENCE_THRESHOLD are auto-applied; the rest remain
'uncategorized' for manual review.
"""
from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Few-shot examples — add/edit entries here to improve model accuracy.
# Each entry: description, amount (negative = debit), source, and expected output.
# ---------------------------------------------------------------------------
_EXAMPLES: list[dict] = [
    # common — supermarkets
    {"description": "ALDI", "amount": -62.40, "source": "card",
     "category": "common", "confidence": 0.97, "reasoning": "Supermarket purchase shared by the household."},
    {"description": "DIA", "amount": -28.15, "source": "card",
     "category": "common", "confidence": 0.97, "reasoning": "Supermarket purchase shared by the household."},
    {"description": "BM", "amount": -45.00, "source": "card",
     "category": "common", "confidence": 0.96, "reasoning": "Supermarket purchase shared by the household."},
    {"description": "MERCADONA", "amount": -87.30, "source": "card",
     "category": "common", "confidence": 0.97, "reasoning": "Supermarket purchase shared by the household."},
    # common — bakeries / food
    {"description": "PANADERIA", "amount": -5.60, "source": "card",
     "category": "common", "confidence": 0.92, "reasoning": "Bakery purchase likely shared."},
    # common — petrol stations
    {"description": "E.S. BECERRIL", "amount": -75.00, "source": "card",
     "category": "common", "confidence": 0.94, "reasoning": "Petrol station, fuel is a shared household expense."},
    {"description": "REPSOL", "amount": -60.00, "source": "card",
     "category": "common", "confidence": 0.94, "reasoning": "Fuel purchase treated as shared expense."},
    # common — pharmacy
    {"description": "FCIA. MAYOR 12", "amount": -12.80, "source": "card",
     "category": "common", "confidence": 0.90, "reasoning": "Pharmacy purchase, typically a shared household expense."},
    # common — shared household expense
    {"description": "CANAL DE", "amount": -55.00, "source": "account",
     "category": "common", "confidence": 0.98, "reasoning": "Water utility bill, a shared household expense."},
    {"description": "MUTUA", "amount": -190, "source": "account",
     "category": "common", "confidence": 0.95, "reasoning": "Car insurance payment, shared household expense."},
    {"description": "IMP VEHICULO", "amount": -70, "source": "account",
     "category": "common", "confidence": 0.95, "reasoning": "Car taxes payment, shared household expense."},
     {"description": "PEPE ENERGY", "amount": -60, "source": "account",
     "category": "common", "confidence": 0.95, "reasoning": "Electricity bill, a shared household expense."},
    # personal — haircut / beauty
    {"description": "CARLOS RIGAGORDA", "amount": -35.00, "source": "card",
     "category": "personal", "confidence": 0.95, "reasoning": "Hairdresser, personal grooming expense."},
    # personal — clothing / individual shops
    {"description": "HENKO", "amount": -49.95, "source": "card",
     "category": "personal", "confidence": 0.90, "reasoning": "Clothing/personal goods store."},
    # personal — bank / finance operations
    {"description": "TELFISA GLOBAL", "amount": -150.00, "source": "account",
     "category": "personal", "confidence": 0.88, "reasoning": "Individual financial operation."},
    {"description": "MONKIMUN", "amount": -29.00, "source": "card",
     "category": "personal", "confidence": 0.88, "reasoning": "Individual purchase, personal expense."},
    # uncategorized
    {"description": "TRANSFERENCIA", "amount": -200.00, "source": "account",
     "category": "uncategorized", "confidence": 0.60, "reasoning": "Generic bank transfer with no context to determine purpose."},
]


def _build_few_shot_messages() -> list[dict]:
    """Return alternating user/assistant message dicts from _EXAMPLES."""
    messages = []
    for ex in _EXAMPLES:
        user_content = (
            f"Description: {ex['description']}\n"
            f"Amount: €{ex['amount']:.2f}\n"
            f"Source: {ex['source']}"
        )
        assistant_content = json.dumps({
            "category": ex["category"],
            "confidence": ex["confidence"],
            "reasoning": ex["reasoning"],
        })
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": assistant_content})
    return messages


_FEW_SHOT_MESSAGES = _build_few_shot_messages()

_agent = Agent(
    name="TransactionCategorizer",
    model="gpt-4o-mini",
    instructions="""
You categorize Spanish bank transactions for a couple tracking shared monthly expenses.
They split common household expenses 50/50.

Categories:
- 'common': Shared expense both people benefit from — groceries, rent, utilities,
  streaming services, restaurants together, household supplies, petrol stations, pharmacy.
- 'personal': Expense for one person only — clothing, personal health, solo transport,
  individual hobbies, individual bank/finance operations.
- 'covered': Do not use this category.
- 'uncategorized': Genuinely unclear from the description alone.

You will receive: description (bank transaction text), amount in euros (negative means
debit/spending, positive means credit/income), and source ('card' or 'account').

Respond with the most likely category, a confidence score from 0.0 to 1.0, and a brief
one-sentence reasoning.
""",
    output_type=CategoryResult,
)


def categorize_transaction(description: str, amount: float, source: str) -> CategoryResult:
    """
    Categorize a single transaction synchronously.
    Returns a CategoryResult with category, confidence, and reasoning.
    """
    user_message = (
        f"Description: {description}\n"
        f"Amount: €{amount:.2f}\n"
        f"Source: {source}"
    )
    messages = [*_FEW_SHOT_MESSAGES, {"role": "user", "content": user_message}]
    with trace("categorize_transaction", metadata={"description": description}):
        result = Runner.run_sync(_agent, messages)
    return result.final_output

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    # Example usage
    test_transaction = {
        "description": "MUTUA MADR495565 01010155",
        "amount": -180,
        "source": "card",
    }
    result = categorize_transaction(**test_transaction)
    print(result.model_dump_json(indent=2))
