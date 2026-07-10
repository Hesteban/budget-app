"""
Unit tests for budget/csv_importers.py and the CSV dispatch path in
budget/importer.py (parse_bank_file with .csv extension).
"""
from __future__ import annotations

import pandas as pd
import pytest

from budget.csv_importers import (
    CSV_PARSERS,
    TradeBankCSV,
    detect_csv_parser,
)
from budget.importer import (
    df_to_records,
    parse_bank_file,
    parse_bank_file_bulk,
)


# ---------------------------------------------------------------------------
# TradeBankCSV.can_parse
# ---------------------------------------------------------------------------

class TestTradeBankCanParse:
    def test_matches_tradebank_columns(self) -> None:
        df = pd.DataFrame(columns=[
            "datetime", "date", "account_type", "category", "type",
            "amount", "currency", "description", "transaction_id",
        ])
        assert TradeBankCSV().can_parse(df) is True

    def test_matches_with_extra_columns(self) -> None:
        df = pd.DataFrame(columns=[
            "date", "category", "type", "amount",
            "extra_col_a", "extra_col_b",
        ])
        assert TradeBankCSV().can_parse(df) is True

    def test_case_insensitive_column_match(self) -> None:
        df = pd.DataFrame(columns=["DATE", "Category", "TYPE", "AMOUNT"])
        assert TradeBankCSV().can_parse(df) is True

    def test_rejects_missing_date(self) -> None:
        df = pd.DataFrame(columns=["category", "type", "amount"])
        assert TradeBankCSV().can_parse(df) is False

    def test_rejects_missing_category(self) -> None:
        df = pd.DataFrame(columns=["date", "type", "amount"])
        assert TradeBankCSV().can_parse(df) is False

    def test_rejects_missing_type(self) -> None:
        df = pd.DataFrame(columns=["date", "category", "amount"])
        assert TradeBankCSV().can_parse(df) is False

    def test_rejects_missing_amount(self) -> None:
        df = pd.DataFrame(columns=["date", "category", "type"])
        assert TradeBankCSV().can_parse(df) is False

    def test_rejects_unrelated_columns(self) -> None:
        df = pd.DataFrame(columns=["Col1", "Col2", "Col3"])
        assert TradeBankCSV().can_parse(df) is False


# ---------------------------------------------------------------------------
# TradeBankCSV.parse
# ---------------------------------------------------------------------------

class TestTradeBankParse:
    def _make_raw_df(self) -> pd.DataFrame:
        """Mixed CSV content: TRADING, CASH/non-card, CASH+card."""
        return pd.DataFrame([
            {
                "datetime": "2026-06-04T14:51:27Z", "date": "2026-06-04",
                "category": "CASH", "type": "CARD_TRANSACTION",
                "amount": "-130.550000", "name": "AHORRAMAS",
                "description": "AHORRAMAS",
            },
            {
                "datetime": "2026-06-04T14:51:28Z", "date": "2026-06-04",
                "category": "TRADING", "type": "BUY",
                "amount": "-100.00", "name": "Some Fund",
                "description": "Savings plan",
            },
            {
                "datetime": "2026-06-05T08:18:52Z", "date": "2026-06-05",
                "category": "CASH", "type": "TRANSFER_INBOUND",
                "amount": "6000.000000", "name": "HECTOR",
                "description": "Transfer in",
            },
            {
                "datetime": "2026-06-17T11:28:34Z", "date": "2026-06-17",
                "category": "CASH", "type": "CARD_TRANSACTION",
                "amount": "-2.500000", "name": "CHIRINGUITO",
                "description": "CHIRINGUITO",
            },
        ])

    def test_output_columns(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert set(df.columns) == {"date", "description", "amount", "source"}

    def test_source_is_card(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert (df["source"] == "card").all()

    def test_filters_non_card_rows(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert len(df) == 2  # only the 2 CASH+CARD_TRANSACTION rows

    def test_drops_trading_rows(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert "Savings plan" not in df["description"].values

    def test_drops_transfer_inbound_rows(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert "Transfer in" not in df["description"].values

    def test_amounts_parsed(self) -> None:
        df = TradeBankCSV().parse(self._make_raw_df())
        assert df["amount"].iloc[0] == pytest.approx(-130.55, abs=0.001)
        assert df["amount"].iloc[1] == pytest.approx(-2.50, abs=0.001)

    def test_dates_are_date_objects(self) -> None:
        from datetime import date
        df = TradeBankCSV().parse(self._make_raw_df())
        assert df["date"].iloc[0] == date(2026, 6, 4)
        assert df["date"].iloc[1] == date(2026, 6, 17)

    def test_description_falls_back_to_name(self) -> None:
        raw = pd.DataFrame([{
            "date": "2026-06-04", "category": "CASH",
            "type": "CARD_TRANSACTION", "amount": "-10.0",
            "name": "MERCHANT NAME", "description": "",
        }])
        df = TradeBankCSV().parse(raw)
        assert df["description"].iloc[0] == "MERCHANT NAME"

    def test_description_prefers_existing_value(self) -> None:
        raw = pd.DataFrame([{
            "date": "2026-06-04", "category": "CASH",
            "type": "CARD_TRANSACTION", "amount": "-10.0",
            "name": "MERCHANT NAME", "description": "Long narrative text",
        }])
        df = TradeBankCSV().parse(raw)
        assert df["description"].iloc[0] == "Long narrative text"

    def test_description_defaults_to_empty_when_no_name_or_description(self) -> None:
        raw = pd.DataFrame([{
            "date": "2026-06-04", "category": "CASH",
            "type": "CARD_TRANSACTION", "amount": "-10.0",
        }])
        df = TradeBankCSV().parse(raw)
        assert df["description"].iloc[0] == ""
        assert len(df) == 1

    def test_drops_rows_with_null_amount(self) -> None:
        raw = pd.DataFrame([
            {"date": "2026-06-04", "category": "CASH",
             "type": "CARD_TRANSACTION", "amount": "-10.0",
             "name": "OK", "description": "OK"},
            {"date": "2026-06-05", "category": "CASH",
             "type": "CARD_TRANSACTION", "amount": None,
             "name": "BAD", "description": "BAD"},
        ])
        df = TradeBankCSV().parse(raw)
        assert len(df) == 1

    def test_name_property_returns_card(self) -> None:
        assert TradeBankCSV().name == "card"


# ---------------------------------------------------------------------------
# detect_csv_parser (registry dispatch)
# ---------------------------------------------------------------------------

class TestDetectCSVParser:
    def test_returns_tradebank_parser(self) -> None:
        df = pd.DataFrame(columns=[
            "date", "category", "type", "amount", "description",
        ])
        parser = detect_csv_parser(df)
        assert isinstance(parser, TradeBankCSV)

    def test_registry_is_non_empty(self) -> None:
        assert len(CSV_PARSERS) >= 1

    def test_raises_on_unknown_columns(self) -> None:
        df = pd.DataFrame(columns=["Col1", "Col2", "Col3"])
        with pytest.raises(ValueError, match="Unrecognised CSV format"):
            detect_csv_parser(df)


# ---------------------------------------------------------------------------
# parse_bank_file — CSV dispatch (end-to-end)
# ---------------------------------------------------------------------------

class TestParseBankFileCSV:
    def test_dispatches_csv_path(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        df, fmt = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        assert fmt == "card"

    def test_returns_only_card_transaction_rows(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        # 11 CARD_TRANSACTION rows in new_bank.csv (June 2026)
        assert len(df) == 11

    def test_filters_out_january_when_asked_for_june(
        self, tradebank_csv_simple_bytes: bytes
    ) -> None:
        # Simple CSV has 1 Feb + 3 Jun CARD_TRANSACTION rows.
        df, _ = parse_bank_file(
            tradebank_csv_simple_bytes, "trade.csv", "Hector", 6, 2026
        )
        assert len(df) == 3

    def test_filters_out_june_when_asked_for_february(
        self, tradebank_csv_simple_bytes: bytes
    ) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_simple_bytes, "trade.csv", "Hector", 2, 2026
        )
        assert len(df) == 1

    def test_user_assigned(self, tradebank_csv_bytes: bytes) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Laerke", 6, 2026
        )
        assert (df["user"] == "Laerke").all()

    def test_source_is_card(self, tradebank_csv_bytes: bytes) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        assert (df["source"] == "card").all()

    def test_rule_categorizes_dia_row_as_common(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        # First CARD_TRANSACTION row is MP**DIA 18128 — matches Rule("dia").
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        dia_rows = df[df["description"].str.contains("DIA", case=False)]
        assert len(dia_rows) > 0
        assert (dia_rows["category"] == "common").all()
        assert (dia_rows["reasoning"] != "").all()

    def test_uncategorized_rows_have_empty_reasoning(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        uncategorized = df[df["category"] == "uncategorized"]
        assert (uncategorized["reasoning"] == "").all()

    def test_date_is_iso_string(self, tradebank_csv_bytes: bytes) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        assert df["date"].iloc[0] == "2026-06-04"

    def test_amounts_negative(self, tradebank_csv_bytes: bytes) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        assert (df["amount"] < 0).all()

    def test_dedup_drops_duplicate_rows(
        self, tradebank_csv_simple_bytes: bytes
    ) -> None:
        # Append an exact duplicate of the first row.
        from budget.importer import load_csv
        raw = load_csv(tradebank_csv_simple_bytes)
        duplicated = pd.concat([raw, raw.head(1)], ignore_index=True)
        import io
        buf = io.BytesIO()
        duplicated.to_csv(buf, index=False)
        df, _ = parse_bank_file(buf.getvalue(), "dup.csv", "Hector", 6, 2026)
        # 3 unique June rows
        assert len(df) == 3

    def test_unrecognised_csv_raises_value_error(self) -> None:
        csv_bytes = b"foo,bar,baz\n1,2,3\n"
        with pytest.raises(ValueError, match="Unrecognised"):
            parse_bank_file(csv_bytes, "bad.csv", "Hector", 6, 2026)


# ---------------------------------------------------------------------------
# parse_bank_file_bulk — CSV explicitly not supported
# ---------------------------------------------------------------------------

class TestParseBankFileBulkCSV:
    def test_csv_bulk_raises_not_implemented(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        with pytest.raises(NotImplementedError, match="CSV bulk"):
            parse_bank_file_bulk(
                tradebank_csv_bytes, "new_bank.csv", "Hector"
            )


# ---------------------------------------------------------------------------
# df_to_records works for CSV output
# ---------------------------------------------------------------------------

class TestDfToRecordsCSV:
    def test_csv_records_have_expected_keys(
        self, tradebank_csv_bytes: bytes
    ) -> None:
        df, _ = parse_bank_file(
            tradebank_csv_bytes, "new_bank.csv", "Hector", 6, 2026
        )
        records = df_to_records(df)
        expected = {"user", "month", "year", "date", "description",
                    "amount", "source", "category", "reasoning"}
        assert set(records[0].keys()) == expected
        assert all(r["source"] == "card" for r in records)
