"""
Page 3 — Manage recurring fixed expenses per user.
Fixed expenses auto-carry (they live in one table, not per-month).
"""
import streamlit as st

from budget import db

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

active_user: str = st.session_state.get("active_user", "")

st.title("🔁 Fixed Expenses")
st.caption(
    "Recurring monthly expenses per user. "
    "These are automatically included in every month's settlement. "
    "Toggle **Active** to include/exclude from calculations."
)


def render_user_section(user: str) -> None:
    st.subheader(f"{'🟥' if user == 'Laerke' else '🟦'} {user}")
    expenses = db.get_fixed_expenses(user=user)

    if not expenses:
        st.caption("No fixed expenses yet.")
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
                )
            with col4:
                if st.button("💾", key=f"save_{exp['id']}", help="Save changes"):
                    db.upsert_fixed_expense(
                        {
                            "id": exp["id"],
                            "user": user,
                            "name": new_name,
                            "amount": new_amount,
                            "active": new_active,
                        }
                    )
                    st.success("Saved.")
                    st.rerun()
            with col5:
                if st.button("🗑️", key=f"del_{exp['id']}", help="Delete"):
                    db.delete_fixed_expense(exp["id"])
                    st.rerun()

    # --- Add new ---
    with st.expander(f"➕ Add fixed expense for {user}"):
        with st.form(key=f"add_form_{user}", clear_on_submit=True):
            new_name = st.text_input("Name", placeholder="e.g. Prestamo, Spotify…")
            new_amount = st.number_input(
                "Monthly amount (€)", min_value=0.0, step=0.01, format="%.2f"
            )
            submitted = st.form_submit_button("Add", type="primary")
            if submitted and new_name:
                db.upsert_fixed_expense(
                    {
                        "user": user,
                        "name": new_name,
                        "amount": new_amount,
                        "active": True,
                    }
                )
                st.success(f"Added '{new_name}' for {user}.")
                st.rerun()


col_left, col_right = st.columns(2)
with col_left:
    render_user_section("Laerke")
with col_right:
    render_user_section("Hector")


st.divider()
all_fixed = db.get_fixed_expenses()
laerke_total = sum(f["amount"] for f in all_fixed if f["user"] == "Laerke" and f["active"])
hector_total = sum(f["amount"] for f in all_fixed if f["user"] == "Hector" and f["active"])

c1, c2 = st.columns(2)
c1.metric("Laerke fixed total / month", f"€{laerke_total:.2f}")
c2.metric("Hector fixed total / month", f"€{hector_total:.2f}")
