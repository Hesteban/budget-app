"""
XLS/XLSX importer for bank exports.

Supports two formats produced by the same bank:
  - "account"  : Fecha de operación | Fecha valor | Concepto | Importe | Divisa | Saldo | Nº mov | Oficina
  - "card"     : Fecha operación | Hora | Nombre comercio | Concepto | Importe | Divisa
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration — driven by .streamlit/secrets.toml [bank] header_row
# Falls back to 10 (row 11 in Excel) if secrets not available.
# ---------------------------------------------------------------------------
try:
    BANK_HEADER_ROW: int = int(st.secrets["bank"]["header_row"])
except Exception:
    BANK_HEADER_ROW: int = 10  # 0-based: row 11 in Excel

ACCOUNT_COLS = {"fecha de operación", "concepto", "importe", "saldo"}
CARD_COLS = {"fecha operación", "nombre comercio", "importe", "hora"}


def detect_format(df: pd.DataFrame) -> str:
    """Return 'account', 'card', or raise ValueError."""
    cols_lower = {c.lower().strip() for c in df.columns}
    if ACCOUNT_COLS.issubset(cols_lower):
        return "account"
    if CARD_COLS.issubset(cols_lower):
        return "card"
    raise ValueError(
        f"Unrecognised XLS format. Detected columns: {list(df.columns)}"
    )


def _clean_amount(val) -> float | None:
    """Convert various amount representations to float."""
    if pd.isna(val):
        return None
    s = str(val).strip().replace("\xa0", "").replace(" ", "")
    # Handle European decimal comma
    # Remove thousands separator (dot) if followed by 3 digits, then swap comma→dot
    import re
    s = re.sub(r"\.(?=\d{3}(?:[,\.]|$))", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val) -> date | None:
    if pd.isna(val):
        return None
    if isinstance(val, (pd.Timestamp, date)):
        return pd.Timestamp(val).date()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return pd.to_datetime(str(val), format=fmt).date()
        except Exception:
            pass
    return None


def parse_account_format(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise account movement export."""
    # Normalise column names
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={
        "fecha de operación": "date",
        "concepto": "description",
        "importe": "amount",
    })
    df = df[["date", "description", "amount"]].copy()
    df["date"] = df["date"].apply(_parse_date)
    df["amount"] = df["amount"].apply(_clean_amount)
    df["source"] = "account"
    return df.dropna(subset=["date", "amount"])


def parse_card_format(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise card movement export."""
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={
        "fecha operación": "date",
        "nombre comercio": "description",
        "importe": "amount",
    })
    # Some card exports use 'concepto' as description fallback
    if "description" not in df.columns and "concepto" in df.columns:
        df["description"] = df["concepto"]
    df = df[["date", "description", "amount"]].copy()
    df["date"] = df["date"].apply(_parse_date)
    df["amount"] = df["amount"].apply(_clean_amount)
    df["source"] = "card"
    return df.dropna(subset=["date", "amount"])


def load_xls(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read raw XLS/XLSX bytes into a DataFrame, skipping bank header rows."""
    buf = io.BytesIO(file_bytes)
    engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"
    df = pd.read_excel(buf, engine=engine, header=BANK_HEADER_ROW)
    # Sanity check: if none of the expected columns are found, fall back to
    # auto-detection (header=None then find the right row)
    cols_lower = {str(c).lower().strip() for c in df.columns}
    if not (ACCOUNT_COLS | CARD_COLS) & cols_lower:
        buf.seek(0)
        raw = pd.read_excel(buf, engine=engine, header=None)
        for i, row in raw.iterrows():
            row_vals = {str(v).lower().strip() for v in row.values if pd.notna(v)}
            if ACCOUNT_COLS & row_vals or CARD_COLS & row_vals:
                buf.seek(0)
                df = pd.read_excel(buf, engine=engine, header=i)
                break
    return df


def parse_bank_file(
    file_bytes: bytes,
    filename: str,
    user: str,
    month: int,
    year: int,
) -> tuple[pd.DataFrame, str]:
    """
    Parse a bank XLS/XLSX file and return a normalised DataFrame ready for
    Supabase insertion, plus the detected format string ('account' | 'card').

    Returned DataFrame columns:
        user, month, year, date (str ISO), description, amount, source, category
    """
    raw = load_xls(file_bytes, filename)

    # Drop fully empty rows/cols
    raw = raw.dropna(how="all").reset_index(drop=True)

    fmt = detect_format(raw)

    if fmt == "account":
        df = parse_account_format(raw)
    else:
        df = parse_card_format(raw)

    # Filter to the selected month/year
    df = df[
        (df["date"].apply(lambda d: d.month if d else None) == month)
        & (df["date"].apply(lambda d: d.year if d else None) == year)
    ].copy()

    df["user"] = user
    df["month"] = month
    df["year"] = year
    df["category"] = "uncategorized"
    df["date"] = df["date"].apply(lambda d: d.isoformat() if d else None)
    df["description"] = df["description"].fillna("").str.strip()

    # Keep only rows with actual amounts
    df = df[df["amount"].notna()].copy()

    # Deduplicate within the file itself before sending to Supabase.
    # The unique constraint is (user, date, description, amount, source) — same as DB.
    df = df.drop_duplicates(subset=["user", "date", "description", "amount", "source"])

    return df, fmt


def parse_bank_file_bulk(
    file_bytes: bytes,
    filename: str,
    user: str,
) -> tuple[pd.DataFrame, str]:
    """
    Parse a bank XLS/XLSX file and return a normalised DataFrame containing
    transactions for ALL months in the file (no month/year filtering).
    Month and year are derived from each row's date.

    Returned DataFrame columns:
        user, month, year, date (str ISO), description, amount, source, category
    """
    raw = load_xls(file_bytes, filename)

    # Drop fully empty rows/cols
    raw = raw.dropna(how="all").reset_index(drop=True)

    fmt = detect_format(raw)

    if fmt == "account":
        df = parse_account_format(raw)
    else:
        df = parse_card_format(raw)

    # Derive month and year from date (no filtering)
    df["month"] = df["date"].apply(lambda d: d.month if d else None)
    df["year"] = df["date"].apply(lambda d: d.year if d else None)

    df["user"] = user
    df["category"] = "uncategorized"
    df["date"] = df["date"].apply(lambda d: d.isoformat() if d else None)
    df["description"] = df["description"].fillna("").str.strip()

    # Keep only rows with actual amounts
    df = df[df["amount"].notna()].copy()

    # Deduplicate within the file itself before sending to Supabase.
    # The unique constraint is (user, date, description, amount, source) — same as DB.
    df = df.drop_duplicates(subset=["user", "date", "description", "amount", "source"])

    return df, fmt


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts for Supabase upsert."""
    cols = ["user", "month", "year", "date", "description", "amount", "source", "category"]
    return df[cols].to_dict(orient="records")
