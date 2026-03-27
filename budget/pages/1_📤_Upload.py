"""
Page 1 — Upload bank XLS file for the active user.
"""
import calendar

import pandas as pd
import streamlit as st

from budget import db, importer, calculator

st.set_page_config(page_title="Upload", page_icon="📤", layout="wide")

# Guard: require login
if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

active_user: str = st.session_state.get("active_user", "")
if not active_user:
    st.warning("Please select your user on the Home page.")
    st.stop()

# ---------------------------------------------------------------------------
st.title("📤 Upload Bank Movements")
st.caption(f"Uploading as: **{active_user}**")

# ---------------------------------------------------------------------------
# Month / Year selector
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        format_func=lambda m: calendar.month_name[m],
        index=pd.Timestamp.now().month - 1,
    )
with col2:
    year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2100,
        value=pd.Timestamp.now().year,
        step=1,
    )

month = int(month)
year = int(year)

# ---------------------------------------------------------------------------
# File uploader
# ---------------------------------------------------------------------------
st.divider()
uploaded = st.file_uploader(
    "Upload your bank export (.xls or .xlsx)",
    type=["xls", "xlsx"],
    help="Export your movements from your bank's online portal and upload here.",
)

if uploaded is not None:
    file_bytes = uploaded.read()

    with st.spinner("Parsing file…"):
        try:
            df, fmt = importer.parse_bank_file(
                file_bytes, uploaded.name, active_user, month, year
            )
        except ValueError as e:
            st.error(f"❌ {e}")
            st.stop()

    if df.empty:
        st.warning(
            f"No transactions found for **{calendar.month_name[month]} {year}** "
            f"in this file. Make sure the file covers that month."
        )
        st.stop()

    # --- Preview ---
    st.success(
        f"✅ Detected format: **{fmt}** — Found **{len(df)}** transaction(s)"
    )
    st.subheader("Preview (first 20 rows)")

    preview = df[["date", "description", "amount", "source", "category"]].head(20).copy()
    preview.columns = ["Date", "Description", "Amount (€)", "Source", "Category"]
    st.dataframe(preview, use_container_width=True, hide_index=True)

    # --- Confirm import ---
    st.divider()
    existing = db.get_transactions(month, year, user=active_user)
    if existing:
        st.warning(
            f"⚠️ There are already **{len(existing)}** transactions for "
            f"**{active_user}** in {calendar.month_name[month]} {year}. "
            "Duplicates will be skipped automatically."
        )

    if st.button("✅ Confirm Import", type="primary", use_container_width=True):
        with st.spinner("Saving to database…"):
            calculator.ensure_month_exists(month, year)
            records = importer.df_to_records(df)
            db.upsert_transactions(records)
        st.success(
            f"Imported {len(records)} transactions for {active_user} — "
            f"{calendar.month_name[month]} {year}."
        )
        st.info("👉 Go to **Transactions** to categorise them as personal or common.")
