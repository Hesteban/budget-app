"""
Page 1 — Upload bank XLS file for the active user.
"""
import calendar

import pandas as pd
import streamlit as st

from budget import db, importer, calculator

# Guard: require login
if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

active_user: str = st.session_state.get("active_user", "")
if not active_user:
    st.warning("Please select your user on the Home page.")
    st.stop()

st.title("📤 Upload Bank Movements")
st.caption(f"Uploading as: **{active_user}**")


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

st.divider()

# --- Single-month upload (existing flow) ---
st.subheader("Single Month Upload")
uploaded = st.file_uploader(
    "Upload your bank export (.xls or .xlsx)",
    type=["xls", "xlsx"],
    help="Export your movements from your bank's online portal and upload here.",
    key="single_month_upload",
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

st.divider()

# --- Bulk upload (new flow) ---
with st.expander("📦 Bulk Upload — Multiple Months", expanded=False):
    st.write(
        "Upload a single file containing transactions from multiple months. "
        "All months will be imported in one go. Duplicates are automatically skipped."
    )

    bulk_uploaded = st.file_uploader(
        "Upload your bank export (.xls or .xlsx) with multiple months",
        type=["xls", "xlsx"],
        help="Export your movements from your bank's online portal. The file can contain multiple months.",
        key="bulk_upload",
    )

    if bulk_uploaded is not None:
        bulk_bytes = bulk_uploaded.read()

        with st.spinner("Parsing bulk file…"):
            try:
                bulk_df, bulk_fmt = importer.parse_bank_file_bulk(
                    bulk_bytes, bulk_uploaded.name, active_user
                )
            except ValueError as e:
                st.error(f"❌ {e}")
                st.stop()

        if bulk_df.empty:
            st.warning("No transactions found in this file.")
            st.stop()

        # Get unique months in the file
        bulk_df_display = bulk_df.copy()
        bulk_df_display["month_name"] = bulk_df_display["month"].apply(
            lambda m: calendar.month_name[int(m)] if pd.notna(m) else None
        )
        unique_months = sorted(
            bulk_df_display[["month", "year", "month_name"]].drop_duplicates().values,
            key=lambda x: (x[1], x[0]),  # Sort by year, then month
        )

        # Check for existing transactions in any of the detected months
        months_with_existing = []
        for m, y, month_name in unique_months:
            existing_count = len(db.get_transactions(int(m), int(y), user=active_user))
            if existing_count > 0:
                months_with_existing.append((m, y, month_name, existing_count))

        if months_with_existing:
            warning_text = "⚠️ **Overlapping months detected:**\n\n"
            for m, y, month_name, count in months_with_existing:
                warning_text += f"- **{month_name} {y}**: {count} existing transaction(s) — duplicates will be skipped.\n"
            st.warning(warning_text)

        # --- Preview ---
        st.success(
            f"✅ Detected format: **{bulk_fmt}** — Found **{len(bulk_df)}** transaction(s) "
            f"across **{len(unique_months)}** month(s)"
        )
        st.subheader("Preview (first 30 rows, sorted by date)")

        preview_bulk = bulk_df_display[["date", "month_name", "description", "amount", "source", "category"]].head(30).copy()
        preview_bulk.columns = ["Date", "Month", "Description", "Amount (€)", "Source", "Category"]
        st.dataframe(preview_bulk, use_container_width=True, hide_index=True)

        # --- Confirm import ---
        st.divider()
        if st.button("✅ Confirm Bulk Import", type="primary", use_container_width=True, key="confirm_bulk"):
            with st.spinner("Saving to database…"):
                # Ensure each detected month exists
                for m, y, _ in unique_months:
                    calculator.ensure_month_exists(int(m), int(y))

                # Upsert all transactions at once
                records = importer.df_to_records(bulk_df)
                db.upsert_transactions(records)

            st.success(
                f"✅ Imported {len(records)} transactions for {active_user} "
                f"across {len(unique_months)} month(s)."
            )
            months_list = ", ".join([f"{name} {y}" for _, y, name in unique_months])
            st.info(f"👉 Go to **Transactions** to categorise them. Months imported: {months_list}")
