"""
Page 2 — View and categorise transactions for a given month.
Shows a 🔴 badge in the sidebar when uncategorised transactions exist.
"""
import calendar

import pandas as pd
import streamlit as st

from budget import db, calculator
from budget.ai_categorizer import categorize_transaction, CONFIDENCE_THRESHOLD

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

active_user: str = st.session_state.get("active_user", "")

# ---------------------------------------------------------------------------
# Month / Year selector  (sidebar)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filter")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            format_func=lambda m: calendar.month_name[m],
            index=pd.Timestamp.now().month - 1,
            key="tx_month",
        )
    with col2:
        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=pd.Timestamp.now().year,
            step=1,
            key="tx_year",
        )
    month = int(month)
    year = int(year)

    user_filter = st.selectbox(
        "User",
        options=["All", "Laerke", "Hector"],
        index=0,
        key="tx_user_filter",
    )
    cat_filter = st.selectbox(
        "Category",
        options=["All", "uncategorized", "personal", "common", "covered"],
        index=0,
        key="tx_cat_filter",
    )

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
all_tx = db.get_transactions(
    month, year, user=None if user_filter == "All" else user_filter
)

has_uncategorized = any(t["category"] == "uncategorized" for t in all_tx)

# Page title with badge
badge = " 🔴" if has_uncategorized else ""
st.title(f"💳 Transactions{badge}")
st.caption(
    f"**{calendar.month_name[month]} {year}** — "
    f"{len(all_tx)} transaction(s) loaded"
    + (" — 🔴 Uncategorised transactions remain" if has_uncategorized else "")
)

if not all_tx:
    st.info("No transactions found. Upload a bank file first.")
    st.stop()

# Apply category filter
if cat_filter != "All":
    display_tx = [t for t in all_tx if t["category"] == cat_filter]
else:
    display_tx = all_tx

# ---------------------------------------------------------------------------
# Build editable DataFrame
# ---------------------------------------------------------------------------
df = pd.DataFrame(display_tx)
df = df[["id", "user", "date", "description", "amount", "source", "category"]].copy()
df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d/%m/%Y")
df["amount"] = df["amount"].apply(lambda x: float(x))

# Category column as a selectable type
CATEGORIES = ["uncategorized", "personal", "common", "covered"]

edited_df = st.data_editor(
    df,
    column_config={
        "id": None,  # hidden
        "user": st.column_config.TextColumn("User", disabled=True, width="small"),
        "date": st.column_config.TextColumn("Date", disabled=True, width="small"),
        "description": st.column_config.TextColumn(
            "Description", disabled=True, width="large"
        ),
        "amount": st.column_config.NumberColumn(
            "Amount (€)", disabled=True, format="€%.2f", width="small"
        ),
        "source": st.column_config.TextColumn("Source", disabled=True, width="small"),
        "category": st.column_config.SelectboxColumn(
            "Category",
            options=CATEGORIES,
            required=True,
            width="medium",
        ),
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
)

# ---------------------------------------------------------------------------
# Detect changes and persist
# ---------------------------------------------------------------------------
changed = edited_df[edited_df["category"] != df["category"]]

col1, col2 = st.columns([1, 3])
with col1:
    if st.button(
        f"💾 Save changes ({len(changed)} pending)",
        type="primary",
        disabled=len(changed) == 0,
        use_container_width=True,
    ):
        updates = changed[["id", "category"]].to_dict(orient="records")
        with st.spinner("Saving…"):
            db.bulk_update_categories(updates)
            calculator.calculate_settlement(month, year)
        st.success(f"Saved {len(updates)} change(s) and updated settlement.")
        st.rerun()

    uncategorized_rows = [t for t in all_tx if t["category"] == "uncategorized"]
    if st.button(
        f"🤖 Auto-categorize ({len(uncategorized_rows)} left)",
        disabled=len(uncategorized_rows) == 0,
        use_container_width=True,
    ):
        updates = []
        skipped = 0
        placeholder = st.empty()
        total = len(uncategorized_rows)
        for i, tx in enumerate(uncategorized_rows, start=1):
            placeholder.caption(f"Categorizing {i}/{total}: {tx['description']}…")
            result = categorize_transaction(tx["description"], tx["amount"], tx["source"])
            if result.confidence >= CONFIDENCE_THRESHOLD:
                updates.append({"id": tx["id"], "category": result.category})
            else:
                skipped += 1
        placeholder.empty()
        if updates:
            db.bulk_update_categories(updates)
            calculator.calculate_settlement(month, year)
        st.success(
            f"✅ {len(updates)} auto-categorized, "
            f"{skipped} skipped (low confidence — review manually)."
        )
        st.rerun()

with col2:
    # Running totals
    common_df = edited_df[edited_df["category"] == "common"]
    personal_df = edited_df[edited_df["category"] == "personal"]
    uncategorized_df = edited_df[edited_df["category"] == "uncategorized"]

    st.caption(
        f"**Common:** €{abs(common_df['amount'].sum()):.2f} &nbsp;|&nbsp; "
        f"**Personal:** €{abs(personal_df['amount'].sum()):.2f} &nbsp;|&nbsp; "
        f"**Uncategorised:** {len(uncategorized_df)}"
    )
