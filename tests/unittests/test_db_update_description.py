"""
Unit tests for budget.db.update_transaction_description
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from budget import db
from budget.fake_repository import FakeRepository
from tests.seed_data import HECTOR_TRANSACTIONS, LAERKE_TRANSACTIONS, make_tx, MONTH, YEAR


@pytest.fixture()
def repo() -> FakeRepository:
    r = FakeRepository()
    r.upsert_transactions([make_tx("Hector", tx) for tx in HECTOR_TRANSACTIONS])
    r.upsert_transactions([make_tx("Laerke", tx) for tx in LAERKE_TRANSACTIONS])
    return r


class TestFakeRepositoryUpdateDescription:
    def test_updates_description(self, repo: FakeRepository) -> None:
        txs = repo.get_transactions(MONTH, YEAR, user="Hector")
        original = txs[0]
        original_id = original["id"]

        repo.update_transaction_description(original_id, "New Description")

        updated = next(t for t in repo.get_transactions(MONTH, YEAR, user="Hector") if t["id"] == original_id)
        assert updated["description"] == "New Description"

    def test_does_not_change_other_fields(self, repo: FakeRepository) -> None:
        txs = repo.get_transactions(MONTH, YEAR, user="Hector")
        original = txs[0]
        original_id = original["id"]

        repo.update_transaction_description(original_id, "Changed Description")

        updated = next(t for t in repo.get_transactions(MONTH, YEAR, user="Hector") if t["id"] == original_id)
        assert updated["amount"] == original["amount"]
        assert updated["date"] == original["date"]
        assert updated["category"] == original["category"]
        assert updated["source"] == original["source"]
        assert updated["user"] == original["user"]

    def test_noop_for_nonexistent_id(self, repo: FakeRepository) -> None:
        repo.update_transaction_description("nonexistent-id", "New Description")
        txs = repo.get_transactions(MONTH, YEAR, user="Hector")
        assert all(t["description"] != "New Description" for t in txs)


class TestModuleLevelUpdateDescription:
    def test_delegates_to_repo(self, repo: FakeRepository) -> None:
        txs = repo.get_transactions(MONTH, YEAR, user="Hector")
        original_id = txs[0]["id"]

        with patch("budget.db.get_repo", return_value=repo):
            db.update_transaction_description(original_id, "Module Level Update")

        updated = next(t for t in repo.get_transactions(MONTH, YEAR, user="Hector") if t["id"] == original_id)
        assert updated["description"] == "Module Level Update"