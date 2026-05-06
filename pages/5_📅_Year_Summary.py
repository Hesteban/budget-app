"""
Page 5 — Year Summary: per-month settlements for a selected year with yearly totals.
"""
import calendar

import pandas as pd
import streamlit as st

from budget import db

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

st.title("📅 Year Summary")

all_summaries = db.get_monthly_summaries()

if not all_summaries:
    st.info("No monthly data available yet. Upload transactions and run settlements first.")
    st.stop()

available_years = sorted({s["year"] for s in all_summaries}, reverse=True)
selected_year = int(st.selectbox("Year", options=available_years))

summaries_by_month = {s["month"]: s for s in all_summaries if s["year"] == selected_year}

st.divider()
st.subheader(f"Monthly Breakdown — {selected_year}")

rows = []
for m in range(1, 13):
    s = summaries_by_month.get(m)
    if s:
        rows.append(
            {
                "Month": calendar.month_name[m],
                "Laerke paid": f"€{s['laerke_common'] + s['fixed_laerke']:.2f}",
                "Hector paid": f"€{s['hector_common'] + s['fixed_hector']:.2f}",
                "Settlement": s["who_pays_whom"] or "—",
            }
        )
    else:
        rows.append(
            {
                "Month": calendar.month_name[m],
                "Laerke paid": "—",
                "Hector paid": "—",
                "Settlement": "No data",
            }
        )

st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

available = list(summaries_by_month.values())
if not available:
    st.info(f"No settlement data found for {selected_year}.")
    st.stop()

st.divider()
st.subheader(f"Yearly Total — {selected_year}")

yearly_balance = sum(s["balance"] for s in available)
total_laerke = sum(s["laerke_common"] + s["fixed_laerke"] for s in available)
total_hector = sum(s["hector_common"] + s["fixed_hector"] for s in available)

if yearly_balance > 0.005:
    yearly_who = f"Hector pays Laerke €{yearly_balance:.2f}"
    bg, icon = "#fff3cd", "💸"
elif yearly_balance < -0.005:
    yearly_who = f"Laerke pays Hector €{abs(yearly_balance):.2f}"
    bg, icon = "#fff3cd", "💸"
else:
    yearly_who = "All settled ✓"
    bg, icon = "#d1e7dd", "✅"

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Laerke total", f"€{total_laerke:.2f}")
with c2:
    st.metric("Hector total", f"€{total_hector:.2f}")
with c3:
    st.markdown(
        f"""<div style="background:{bg};padding:1rem;border-radius:12px;text-align:center;">
            <span style="font-size:2rem;">{icon}</span>
            <p style="font-size:1.2rem;font-weight:700;margin:0.5rem 0;">{yearly_who}</p>
            <p style="color:#555;font-size:0.85rem;">{len(available)} month(s) with data</p>
        </div>""",
        unsafe_allow_html=True,
    )
