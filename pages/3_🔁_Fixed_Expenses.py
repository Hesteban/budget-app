"""
Page 3 — Manage recurring fixed expenses per user, scoped by year.
Fixed expenses auto-carry (they live in one table, not per-month).
"""
import datetime

import streamlit as st

from budget import db

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

active_user: str = st.session_state.get("active_user", "")

st.title("Fixed Expenses")
st.caption(
    "Recurring monthly expenses per user, organized by year. "
    "These are automatically included in every month's settlement. "
    "Toggle **Active** to include/exclude from calculations."
)

current_year = datetime.date.today().year

col_year, col_copy = st.columns([1, 2])
with col_year:
    selected_year = st.selectbox(
        "Year",
        options=list(range(2020, 2101)),
        index=list(range(2020, 2101)).index(current_year),
    )
with col_copy:
    st.write("")  # vertical align
    if st.button("Copy from previous year"):
        prev_year = selected_year - 1
        db.copy_fixed_expenses_year(prev_year, selected_year)
        st.success(f"Copied fixed expenses from {prev_year} to {selected_year}.")
        st.rerun()


def render_user_section(user: str, year: int) -> None:
    st.subheader(f"{'Laerke' if user == 'Laerke' else 'Hector'}")
    expenses = db.get_fixed_expenses(user=user, year=year)

    if not expenses:
        st.caption(f"No fixed expenses for {year}.")
    else:
        for exp in expenses:
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1, 1])
            with col1:
                new_name = st.text_input(
                    "Name",
                    value=exp["name"],
                    key=f"name_{exp['id']}",
                    label_visibility="collapsed",
                )
            with col2:
                new_amount = st.number_input(
                    "Amount",
                    value=float(exp["amount"]),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"amount_{exp['id']}",
                    label_visibility="collapsed",
                )
            with col3:
                new_active = st.toggle(
                    "Active",
                    value=exp["active"],
                    key=f"active_{exp['id']}",
                    label_visibility="collapsed",
                )
            with col4:
                if st.button("Save", key=f"save_{exp['id']}", type="primary"):
                    db.upsert_fixed_expense(
                        {
                            "id": exp["id"],
                            "user": user,
                            "name": new_name,
                            "amount": new_amount,
                            "active": new_active,
                            "year": year,
                        }
                    )
                    st.success("Saved.")
                    st.rerun()
            with col5:
                if st.button("Delete", key=f"del_{exp['id']}"):
                    db.delete_fixed_expense(exp["id"])
                    st.rerun()

    with st.expander(f"Add fixed expense for {user}"):
        with st.form(key=f"add_form_{user}_{year}", clear_on_submit=True):
            new_name = st.text_input("Name", placeholder="e.g. Prestamo, Spotify")
            new_amount = st.number_input(
                "Monthly amount", min_value=0.0, step=0.01, format="%.2f"
            )
            submitted = st.form_submit_button("Add", type="primary")
            if submitted and new_name:
                db.upsert_fixed_expense(
                    {
                        "user": user,
                        "name": new_name,
                        "amount": new_amount,
                        "active": True,
                        "year": year,
                    }
                )
                st.success(f"Added '{new_name}' for {user}.")
                st.rerun()


st.markdown(
    """
    <style>
    /* Prevent button labels from wrapping */
    div[data-testid="stButton"] > button p {
        white-space: nowrap;
    }
    /* Delete button — danger red */
    div[data-testid="stHorizontalBlock"] > div:nth-child(5)
        > div[data-testid="stButton"] > button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: 1px solid #ff4b4b !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(5)
        > div[data-testid="stButton"] > button:hover {
        background-color: #e03030 !important;
        border: 1px solid #e03030 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_left, col_right = st.columns(2)
with col_left:
    render_user_section("Laerke", selected_year)
with col_right:
    render_user_section("Hector", selected_year)


st.divider()
all_fixed = db.get_fixed_expenses(year=selected_year)
laerke_total = sum(f["amount"] for f in all_fixed if f["user"] == "Laerke" and f["active"])
hector_total = sum(f["amount"] for f in all_fixed if f["user"] == "Hector" and f["active"])

c1, c2 = st.columns(2)
c1.metric("Laerke fixed total / month", f"€{laerke_total:.2f}")
c2.metric("Hector fixed total / month", f"€{hector_total:.2f}")

st.divider()
st.subheader("🏠 Direct Expenses")
st.caption(
    "Shared household costs settled directly between you (e.g. mortgage, insurance). "
    "Split equally (÷2). Reduce savings only — not included in the monthly settlement."
)

direct = db.get_direct_expenses(year=selected_year)

if not direct:
    st.caption(f"No direct expenses for {selected_year}.")
else:
    for exp in direct:
        d1, d2, d3, d4 = st.columns([3, 1.5, 1, 1])
        with d1:
            new_name = st.text_input(
                "Name", value=exp["name"],
                key=f"dname_{exp['id']}", label_visibility="collapsed",
            )
        with d2:
            new_amount = st.number_input(
                "Amount", value=float(exp["amount"]),
                min_value=0.0, step=0.01, format="%.2f",
                key=f"damount_{exp['id']}", label_visibility="collapsed",
            )
        with d3:
            if st.button("Save", key=f"dsave_{exp['id']}", type="primary"):
                db.upsert_direct_expense(
                    {"id": exp["id"], "name": new_name, "amount": new_amount,
                     "active": True, "year": selected_year}
                )
                st.success("Saved.")
                st.rerun()
        with d4:
            if st.button("Delete", key=f"ddel_{exp['id']}"):
                db.delete_direct_expense(exp["id"])
                st.rerun()

with st.expander(f"Add direct expense for {selected_year}"):
    with st.form(key=f"add_direct_{selected_year}", clear_on_submit=True):
        d_name = st.text_input("Name", placeholder="e.g. Mortgage, Insurance")
        d_amount = st.number_input("Monthly amount", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button("Add", type="primary") and d_name:
            db.upsert_direct_expense(
                {"name": d_name, "amount": d_amount, "active": True, "year": selected_year}
            )
            st.success(f"Added '{d_name}'.")
            st.rerun()

direct_total = sum(e["amount"] for e in direct if e["active"])
st.metric("Total direct expenses / month (each person pays)", f"€{direct_total / 2:.2f}")