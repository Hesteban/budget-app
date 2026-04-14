"""
Unit tests for the autocategorization result-collection logic.

Mocks categorize_transaction to return controlled CategoryResult values
and verifies the categorized/skipped split.
"""
from __future__ import annotations

import pytest

from budget.agents.ai_categorizer import CategoryResult, CONFIDENCE_THRESHOLD


def _run_categorization(transactions: list[dict], mock_results: list[CategoryResult]):
    """
    Simulate the categorization loop from the Transactions page.
    Returns (updates, categorized_results, skipped_results).
    """
    updates = []
    categorized_results = []
    skipped_results = []

    for tx, result in zip(transactions, mock_results):
        entry = {
            "description": tx["description"],
            "amount": tx["amount"],
            "category": result.category,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }
        if result.confidence >= CONFIDENCE_THRESHOLD:
            updates.append({"id": tx["id"], "category": result.category, "reasoning": result.reasoning})
            categorized_results.append(entry)
        else:
            skipped_results.append(entry)

    return updates, categorized_results, skipped_results


class TestCategorizationResultCollection:
    def test_high_confidence_goes_to_categorized(self):
        txs = [{"id": "1", "description": "MERCADONA", "amount": -50.0, "source": "card"}]
        results = [CategoryResult(category="common", confidence=0.95, reasoning="Supermarket")]

        updates, categorized, skipped = _run_categorization(txs, results)

        assert len(updates) == 1
        assert updates[0] == {"id": "1", "category": "common"}
        assert len(categorized) == 1
        assert categorized[0]["reasoning"] == "Supermarket"
        assert len(skipped) == 0

    def test_low_confidence_goes_to_skipped(self):
        txs = [{"id": "2", "description": "UNKNOWN SHOP", "amount": -20.0, "source": "card"}]
        results = [CategoryResult(category="personal", confidence=0.60, reasoning="Unclear merchant")]

        updates, categorized, skipped = _run_categorization(txs, results)

        assert len(updates) == 0
        assert len(categorized) == 0
        assert len(skipped) == 1
        assert skipped[0]["description"] == "UNKNOWN SHOP"
        assert skipped[0]["confidence"] == 0.60

    def test_exact_threshold_goes_to_categorized(self):
        txs = [{"id": "3", "description": "REPSOL", "amount": -60.0, "source": "card"}]
        results = [CategoryResult(category="common", confidence=CONFIDENCE_THRESHOLD, reasoning="Fuel")]

        updates, categorized, skipped = _run_categorization(txs, results)

        assert len(categorized) == 1
        assert len(skipped) == 0

    def test_mixed_results(self):
        txs = [
            {"id": "1", "description": "ALDI", "amount": -40.0, "source": "card"},
            {"id": "2", "description": "OBSCURE", "amount": -10.0, "source": "account"},
            {"id": "3", "description": "DIA", "amount": -25.0, "source": "card"},
        ]
        results = [
            CategoryResult(category="common", confidence=0.97, reasoning="Supermarket"),
            CategoryResult(category="uncategorized", confidence=0.50, reasoning="Unknown"),
            CategoryResult(category="common", confidence=0.92, reasoning="Supermarket"),
        ]

        updates, categorized, skipped = _run_categorization(txs, results)

        assert len(updates) == 2
        assert len(categorized) == 2
        assert len(skipped) == 1
        assert skipped[0]["description"] == "OBSCURE"

    def test_entry_contains_all_fields(self):
        txs = [{"id": "1", "description": "TEST", "amount": -99.0, "source": "account"}]
        results = [CategoryResult(category="personal", confidence=0.90, reasoning="Personal item")]

        _, categorized, _ = _run_categorization(txs, results)

        entry = categorized[0]
        assert set(entry.keys()) == {"description", "amount", "category", "confidence", "reasoning"}
        assert entry["description"] == "TEST"
        assert entry["amount"] == -99.0
        assert entry["category"] == "personal"
        assert entry["confidence"] == 0.90
        assert entry["reasoning"] == "Personal item"
