"""
Budget App — Home / Auth page.

Flow:
  1. User enters shared password → authenticated flag set in session_state.
  2. User selects "I am Laerke" or "I am Héctor" → active_user set.
  3. Sidebar shows active user and navigation throughout.
"""
import os

from budget import db
import bcrypt
import streamlit as st

st.set_page_config(
    page_title="Budget App",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded",
)

if os.getenv("APP_ENV") != "test":
    os.environ["OPENAI_API_KEY"] = st.secrets["openai"]["api_key"]

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "active_user" not in st.session_state:
    st.session_state["active_user"] = ""

with st.sidebar:
    st.title("Budget App 💶")
    if st.session_state["authenticated"]:
        st.success(f"👤 {st.session_state['active_user'] or 'No user selected'}")
        if st.button("🚪 Log out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["active_user"] = ""
            st.rerun()
    else:
        st.info("Please log in.")

# ---------------------------------------------------------------------------
# TEST ONLY — auto-login when APP_ENV=test (CI / Playwright).
# This block MUST never run in production; it is gated behind an env var
# that is only set in CI workflows and local test runs.
# ---------------------------------------------------------------------------
if os.getenv("APP_ENV") == "test" and not st.session_state["authenticated"]:
    # Seed the in-memory FakeRepository once (idempotent — skipped if data exists)
    from tests.seed_data import (
        FIXED_EXPENSES,
        HECTOR_TRANSACTIONS,
        LAERKE_TRANSACTIONS,
        MONTH,
        YEAR,
        make_tx,
    )
    if not db.get_transactions(MONTH, YEAR):
        db.upsert_transactions([make_tx("Hector", tx) for tx in HECTOR_TRANSACTIONS])
        db.upsert_transactions([make_tx("Laerke", tx) for tx in LAERKE_TRANSACTIONS])
        for fe in FIXED_EXPENSES:
            db.upsert_fixed_expense(fe)

    st.session_state["authenticated"] = True
    st.session_state["active_user"] = "Hector"
    st.rerun()

if not st.session_state["authenticated"]:
    st.title("Welcome to Budget App 💶")
    st.markdown(
        "Track monthly expenses, categorise transactions, and settle up automatically."
    )
    st.divider()

    with st.form("login_form"):
        password = st.text_input("Enter app password", type="password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

    if submitted:
        stored_hash: str = st.secrets["auth"]["password_hash"]
        try:
            match = bcrypt.checkpw(
                password.encode(), stored_hash.encode()
            )
        except Exception:
            match = False

        if match:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect password.")

    st.stop()

st.title("Budget App 💶")
st.markdown(
    f"**Date:** {__import__('datetime').date.today().strftime('%d %B %Y')}"
)
st.divider()

st.subheader("Who are you?")
col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🟥 I am Laerke",
        use_container_width=True,
        type="primary" if st.session_state["active_user"] == "Laerke" else "secondary",
    ):
        st.session_state["active_user"] = "Laerke"
        st.rerun()

with col2:
    if st.button(
        "🟦 I am Héctor",
        use_container_width=True,
        type="primary" if st.session_state["active_user"] == "Hector" else "secondary",
    ):
        st.session_state["active_user"] = "Hector"
        st.rerun()

if st.session_state["active_user"]:
    st.success(
        f"Active user: **{st.session_state['active_user']}** — "
        "Use the sidebar to navigate."
    )
else:
    st.info("Please select your user to continue.")


st.divider()
st.subheader("📋 Quick overview")

try:

    months = db.months_with_data()
    if not months:
        st.caption("No data yet. Upload your first bank file to get started.")
    else:
        st.caption(f"Months with data: **{len(months)}**")
        latest = months[0]
        summary = db.get_monthly_summary(latest["month"], latest["year"])
        if summary:
            import calendar
            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Latest month",
                f"{calendar.month_abbr[latest['month']]} {latest['year']}",
            )
            c2.metric("Settlement", summary["who_pays_whom"] or "—")
            uncategorized = db.has_uncategorized(latest["month"], latest["year"])
            c3.metric(
                "Uncategorised",
                "🔴 Yes — action needed" if uncategorized else "✅ All done",
            )
except Exception as e:
    st.caption(f"Connect to Supabase to see live data. ({e})")
