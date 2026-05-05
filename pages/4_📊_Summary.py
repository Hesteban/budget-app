"""
Page 4 — Monthly summary: settlement result, personal totals, multi-month chart.
"""
import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from budget import db, calculator
from budget.agents import ai_summarizer

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

st.title("📊 Monthly Summary")

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


if st.button("🔄 Recalculate settlement", type="primary"):
    with st.spinner("Calculating…"):
        calculator.calculate_settlement(month, year)
    st.success("Settlement updated.")
    st.rerun()

summary = db.get_monthly_summary(month, year)

if summary is None:
    st.info(
        f"No data for {calendar.month_name[month]} {year}. "
        "Upload transactions first."
    )
    st.stop()

tab1, tab2, tab3 = st.tabs(["📊 Settlement", "📈 Trends", "📝 AI Report"])

with tab1:
    st.subheader(f"Settlement — {calendar.month_name[month]} {year}")

    balance = summary["balance"]
    who = summary["who_pays_whom"] or "No data"

    if "pays" in who:
        bg = "#fff3cd"
        icon = "💸"
    else:
        bg = "#d1e7dd"
        icon = "✅"

    st.markdown(
        f"""
        <div style="background:{bg};padding:1.5rem;border-radius:12px;text-align:center;">
            <span style="font-size:2.5rem;">{icon}</span>
            <p style="font-size:1.6rem;font-weight:700;margin:0.5rem 0;">{who}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.subheader("Breakdown")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 🟥 Laerke")
        st.metric("Common expenses paid", f"€{summary['laerke_common']:.2f}")
        st.metric("Fixed expenses", f"€{summary['fixed_laerke']:.2f}")
        st.metric(
            "Total contribution",
            f"€{summary['laerke_common'] + summary['fixed_laerke']:.2f}",
        )
        st.metric("Personal expenses (info)", f"€{summary['laerke_personal']:.2f}")

    with c2:
        st.markdown("### 🟦 Hector")
        st.metric("Common expenses paid", f"€{summary['hector_common']:.2f}")
        st.metric("Fixed expenses", f"€{summary['fixed_hector']:.2f}")
        st.metric(
            "Total contribution",
            f"€{summary['hector_common'] + summary['fixed_hector']:.2f}",
        )
        st.metric("Personal expenses (info)", f"€{summary['hector_personal']:.2f}")

with tab2:
    st.subheader("📈 Multi-month comparison — Common expenses")

    all_summaries = db.get_monthly_summaries()

    if len(all_summaries) < 2:
        st.caption("More months of data needed to show the comparison chart.")
    else:
        hist = pd.DataFrame(all_summaries)
        hist = hist.sort_values(["year", "month"])
        hist["label"] = hist.apply(
            lambda r: f"{calendar.month_abbr[r['month']]} {r['year']}", axis=1
        )

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Laerke",
                    x=hist["label"],
                    y=hist["laerke_common"] + hist["fixed_laerke"],
                    marker_color="#E63946",
                    text=(hist["laerke_common"] + hist["fixed_laerke"]).apply(
                        lambda v: f"€{v:.0f}"
                    ),
                    textposition="outside",
                ),
                go.Bar(
                    name="Hector",
                    x=hist["label"],
                    y=hist["hector_common"] + hist["fixed_hector"],
                    marker_color="#457B9D",
                    text=(hist["hector_common"] + hist["fixed_hector"]).apply(
                        lambda v: f"€{v:.0f}"
                    ),
                    textposition="outside",
                ),
            ]
        )
        fig.update_layout(
            barmode="group",
            xaxis_title="Month",
            yaxis_title="€",
            legend_title="User",
            template="plotly_white",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📉 Personal expenses per month")
        fig2 = go.Figure(
            data=[
                go.Bar(
                    name="Laerke",
                    x=hist["label"],
                    y=hist["laerke_personal"],
                    marker_color="#E63946",
                    opacity=0.7,
                ),
                go.Bar(
                    name="Hector",
                    x=hist["label"],
                    y=hist["hector_personal"],
                    marker_color="#457B9D",
                    opacity=0.7,
                ),
            ]
        )
        fig2.update_layout(
            barmode="group",
            xaxis_title="Month",
            yaxis_title="€",
            template="plotly_white",
            height=350,
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    summary_key = f"monthly_summary_{month}_{year}"
    if summary_key not in st.session_state:
        st.session_state[summary_key] = db.get_monthly_report(month, year)

    existing_report = st.session_state[summary_key]

    if existing_report:
        st.markdown(existing_report)
        if st.button("🔄 Regenerate summary"):
            with st.spinner("Generating summary…"):
                content = ai_summarizer.generate_monthly_summary(month, year)
            db.upsert_monthly_report(month, year, content)
            st.session_state[summary_key] = content
            st.rerun()
    else:
        st.caption("No summary generated yet for this month.")
        if st.button("🤖 Generate Monthly Summary"):
            with st.spinner("Generating summary…"):
                content = ai_summarizer.generate_monthly_summary(month, year)
            db.upsert_monthly_report(month, year, content)
            st.session_state[summary_key] = content
            st.rerun()
