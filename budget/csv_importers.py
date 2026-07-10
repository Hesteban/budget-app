"""
CSV bank importers.

A `CSVParser` is a pluggable strategy for a single bank's CSV export shape.
Concrete parsers are listed in `CSV_PARSERS` (registry); adding a new bank
is as simple as writing a new class and appending it to the registry — no
edits to `importer.py` required.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class CSVParser(Protocol):
    """Contract for a single bank's CSV parser."""

    @property
    def name(self) -> str:
        """Value written to transactions.source (e.g. 'card', 'tradebank')."""
        ...

    def can_parse(self, df: pd.DataFrame) -> bool:
        """Return True if this parser can handle the given DataFrame's columns."""
        ...

    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalise raw CSV rows into the canonical DataFrame:

            columns = ['date', 'description', 'amount', 'source']

        - date: datetime.date object (or None to be dropped)
        - description: stripped string (may be empty)
        - amount: float (negative = expense)
        - source: this parser's `name`
        """
        ...


class TradeBankCSV:
    """
    Parser for TradeBank CSV exports.

    Filters to CASH + CARD_TRANSACTION rows (drops TRADING/BUY, CASH/INTEREST_PAYMENT,
    CASH/TRANSFER_INBOUND, CASH/BENEFITS_SAVEBACK, etc.).

    Source value is 'card' — semantically these are card transactions, and reusing
    the existing source avoids any conflict with the (user, date, description,
    amount, source) unique constraint in the transactions table.
    """

    REQUIRED_COLS = {"date", "amount", "category", "type"}

    @property
    def name(self) -> str:
        return "card"

    def can_parse(self, df: pd.DataFrame) -> bool:
        cols_lower = {c.lower().strip() for c in df.columns}
        return self.REQUIRED_COLS.issubset(cols_lower)

    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        mask = (df["category"] == "CASH") & (df["type"] == "CARD_TRANSACTION")
        df = df.loc[mask].copy()

        if "description" not in df.columns:
            df["description"] = df["name"] if "name" in df.columns else ""
        elif "name" in df.columns:
            mask = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
            df.loc[mask, "description"] = df.loc[mask, "name"]

        df["description"] = df["description"].fillna("").astype(str).str.strip()

        from budget.importer import _clean_amount, _parse_date

        df["date"] = df["date"].apply(_parse_date)
        df["amount"] = df["amount"].apply(_clean_amount)
        df["source"] = self.name

        df = df.loc[:, ["date", "description", "amount", "source"]]
        return df.dropna(subset=["date", "amount"])


CSV_PARSERS: list[CSVParser] = [TradeBankCSV()]


def detect_csv_parser(df: pd.DataFrame) -> CSVParser:
    """
    Find the first registered parser whose `can_parse(df)` returns True.

    Raises ValueError if no parser matches — the caller should surface this
    to the user as an unrecognised file format error.
    """
    for parser in CSV_PARSERS:
        if parser.can_parse(df):
            return parser
    raise ValueError(
        f"Unrecognised CSV format. Detected columns: {list(df.columns)}"
    )
