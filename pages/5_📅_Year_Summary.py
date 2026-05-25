"""
Page 5 — Year Summary: per-month settlements for a selected year with yearly totals.
"""
import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from budget import db, calculator

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

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Recalculate all months for this year", use_container_width=True):
        with st.spinner("Recalculating…"):
            for m in range(1, 13):
                if summaries_by_month.get(m):
                    calculator.calculate_settlement(m, selected_year)
        st.success("All settlements recalculated.")
        st.rerun()
with col2:
    if st.button("🔄 Recalculate ALL years", use_container_width=True):
        with st.spinner("Recalculating all settlements…"):
            all_months = db.months_with_data()
            for m_y in all_months:
                calculator.calculate_settlement(m_y["month"], m_y["year"])
        st.success("All settlements recalculated.")
        st.rerun()

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

st.divider()
st.subheader(f"💰 Income & Savings — {selected_year}")

yearly_income_laerke = sum(float(s.get("laerke_income") or 0) for s in available)
yearly_income_hector = sum(float(s.get("hector_income") or 0) for s in available)
yearly_personal_laerke = sum(float(s.get("laerke_personal") or 0) for s in available)
yearly_personal_hector = sum(float(s.get("hector_personal") or 0) for s in available)
yearly_fair_share_laerke = sum(float(s.get("fair_share") or 0) for s in available)
yearly_fair_share_hector = sum(float(s.get("fair_share") or 0) for s in available)
yearly_direct_laerke = sum(float(s.get("direct_per_person") or 0) for s in available)
yearly_direct_hector = sum(float(s.get("direct_per_person") or 0) for s in available)
yearly_savings_laerke = sum(float(s.get("laerke_savings") or 0) for s in available)
yearly_savings_hector = sum(float(s.get("hector_savings") or 0) for s in available)

comparison_rows = [
    ("Total Income", yearly_income_laerke, yearly_income_hector),
    ("Personal Expenses", yearly_personal_laerke, yearly_personal_hector),
    ("Fair Share (total)", yearly_fair_share_laerke, yearly_fair_share_hector),
    ("Direct Expenses (÷2)", yearly_direct_laerke, yearly_direct_hector),
    ("Net Savings", yearly_savings_laerke, yearly_savings_hector),
]
comp_df = pd.DataFrame(comparison_rows, columns=["Metric", "🟥 Laerke", "🟦 Hector"])
st.dataframe(comp_df, hide_index=True, use_container_width=True)

ic1, ic2 = st.columns(2)
with ic1:
    delta_l = "surplus" if yearly_savings_laerke >= 0 else "deficit"
    st.metric(
        "🟥 Laerke — Net Savings",
        f"€{yearly_savings_laerke:.2f}",
        delta=delta_l,
        delta_color="normal" if yearly_savings_laerke >= 0 else "inverse",
    )
with ic2:
    delta_h = "surplus" if yearly_savings_hector >= 0 else "deficit"
    st.metric(
        "🟦 Hector — Net Savings",
        f"€{yearly_savings_hector:.2f}",
        delta=delta_h,
        delta_color="normal" if yearly_savings_hector >= 0 else "inverse",
    )

st.divider()
st.subheader("📈 Monthly Savings Trend")

monthly_data = []
for m in range(1, 13):
    s = summaries_by_month.get(m)
    if s:
        monthly_data.append({
            "month": calendar.month_abbr[m],
            "Laerke": float(s.get("laerke_savings") or 0),
            "Hector": float(s.get("hector_savings") or 0),
        })

if monthly_data:
    df_chart = pd.DataFrame(monthly_data)
    fig = go.Figure(
        data=[
            go.Bar(
                name="Laerke",
                x=df_chart["month"],
                y=df_chart["Laerke"],
                marker_color="#E63946",
                opacity=0.85,
                text=df_chart["Laerke"].apply(lambda v: f"€{v:.0f}"),
                textposition="outside",
            ),
            go.Bar(
                name="Hector",
                x=df_chart["month"],
                y=df_chart["Hector"],
                marker_color="#457B9D",
                opacity=0.85,
                text=df_chart["Hector"].apply(lambda v: f"€{v:.0f}"),
                textposition="outside",
            ),
        ]
    )
    fig.update_layout(
        barmode="group",
        xaxis_title="Month",
        yaxis_title="€",
        template="plotly_white",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No monthly savings data available.")
