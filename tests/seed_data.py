"""
Shared seed constants for unit tests and E2E test setup.

Imported by:
  - tests/conftest.py  (pytest fixtures)
  - main.py            (seeds FakeRepository when APP_ENV=test)
"""
from __future__ import annotations

MONTH = 3
YEAR = 2026

# fmt: off
HECTOR_TRANSACTIONS = [
    # (date, description, amount, source, category)
    ("2026-03-02", "Mercadona",          -85.30, "account", "common"),
    ("2026-03-05", "Netflix",            -15.99, "card",    "common"),
    ("2026-03-08", "Gym membership",     -40.00, "account", "personal"),
    ("2026-03-10", "Ikea",               -60.50, "card",    "common"),
    ("2026-03-15", "Restaurante Casa",   -32.00, "card",    "personal"),
    ("2026-03-18", "El Corte Ingles",    -25.00, "account", "common"),
    ("2026-03-22", "Farmacia",           -12.80, "account", "personal"),
    ("2026-03-28", "Carrefour",          -47.60, "account", "common"),
]

LAERKE_TRANSACTIONS = [
    ("2026-03-01", "Netto",              -72.40, "account", "common"),
    ("2026-03-04", "Spotify",            -9.99,  "card",    "personal"),
    ("2026-03-07", "Apoteket",           -18.50, "account", "personal"),
    ("2026-03-11", "IKEA",               -44.90, "card",    "common"),
    ("2026-03-14", "Bioparc entrada",    -28.00, "card",    "common"),
    ("2026-03-19", "Matas",              -35.20, "account", "personal"),
    ("2026-03-23", "Lidl",               -55.10, "account", "common"),
    # Intentional duplicate of the first row — must be silently ignored by upsert
    ("2026-03-01", "Netto",              -72.40, "account", "common"),
]

FIXED_EXPENSES = [
    {"user": "Hector",  "name": "Prestamo coche",  "amount": 250.00, "active": True},
    {"user": "Hector",  "name": "Seguro hogar",     "amount": 45.00,  "active": True},
    {"user": "Laerke",  "name": "SU loan",          "amount": 180.00, "active": True},
    {"user": "Laerke",  "name": "Phone plan",       "amount": 30.00,  "active": False},  # inactive
]
# fmt: on


def make_tx(user: str, row: tuple) -> dict:
    date, description, amount, source, category = row
    return {
        "user": user,
        "month": MONTH,
        "year": YEAR,
        "date": date,
        "description": description,
        "amount": amount,
        "source": source,
        "category": category,
    }
