"""
Pytest fixtures shared across all test modules.

repo         — fresh FakeRepository seeded with March 2026 data
               (8 transactions per user + 2 fixed expenses per user)
account_xlsx_bytes — in-memory .xlsx bytes in the bank "account" format
"""
from __future__ import annotations

import io

import openpyxl
import pytest

from budget.fake_repository import FakeRepository
from tests.seed_data import (
    FIXED_EXPENSES,
    HECTOR_TRANSACTIONS,
    LAERKE_TRANSACTIONS,
    make_tx,
)


# ---------------------------------------------------------------------------
# repo fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo() -> FakeRepository:
    """
    Fresh FakeRepository seeded with March 2026 test data.
    scope=function (default) — each test gets an isolated copy.
    """
    r = FakeRepository()

    # Transactions (Laerke duplicate will be silently dropped by upsert)
    r.upsert_transactions([make_tx("Hector", tx) for tx in HECTOR_TRANSACTIONS])
    r.upsert_transactions([make_tx("Laerke", tx) for tx in LAERKE_TRANSACTIONS])

    # Fixed expenses
    for fe in FIXED_EXPENSES:
        r.upsert_fixed_expense(fe)

    return r


# ---------------------------------------------------------------------------
# account_xlsx_bytes fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def account_xlsx_bytes() -> bytes:
    """
    In-memory .xlsx bytes that match the bank 'account' column signature.
    Header is on row 11 (0-based index 10) as configured by BANK_HEADER_ROW.
    Rows 0-9 are filler (simulating bank metadata rows).
    Contains 5 transactions for March 2026 + 1 for February (filtered out).
    """
    wb = openpyxl.Workbook()
    ws = wb.active

    # Rows 1-10: blank filler to simulate bank header padding (BANK_HEADER_ROW=10)
    for _ in range(10):
        ws.append([""] * 5)

    # Row 11: column headers (account format)
    ws.append([
        "Fecha de operación",
        "Fecha valor",
        "Concepto",
        "Importe",
        "Divisa",
        "Saldo",
        "Nº mov",
        "Oficina",
    ])

    # March 2026 transactions (should all be parsed)
    march_rows = [
        ("03/03/2026", "03/03/2026", "Supermercado",    "-62,50", "EUR", "1000,00", "1", "001"),
        ("10/03/2026", "10/03/2026", "Farmacia",         "-18,90", "EUR",  "937,50", "2", "001"),
        ("15/03/2026", "15/03/2026", "Transferencia",    "500,00", "EUR", "1437,50", "3", "001"),
        ("20/03/2026", "20/03/2026", "Recibo luz",       "-95,20", "EUR", "1342,30", "4", "001"),
        ("28/03/2026", "28/03/2026", "Restaurante",      "-44,00", "EUR", "1298,30", "5", "001"),
    ]
    for row in march_rows:
        ws.append(list(row))

    # February 2026 transaction — must be filtered out by parse_bank_file
    ws.append(["15/02/2026", "15/02/2026", "Old bill", "-30,00", "EUR", "1268,30", "6", "001"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
