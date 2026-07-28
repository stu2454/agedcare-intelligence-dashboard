"""Compliance Actions Tracker tab.

Summarises the regulatory decisions recorded in the ``[C]`` columns: what was
issued, to whom, when, and whether it was still open as at the extract date.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from agedcare import config
from agedcare.filters import DashboardContext

DISPLAY_COLUMNS = [
    "Provider Name",
    "Service Name",
    "State/Territory",
    config.COMPLIANCE_DECISION_TYPE,
    config.COMPLIANCE_APPLIED_PARSED,
    config.COMPLIANCE_ENDS_PARSED,
    "Status",
    "Compliance rating",
]

OPEN = "Open"
CLOSED = "Closed"
UNDATED = "Undated"


def _decisions(sector: pd.DataFrame) -> pd.DataFrame:
    """Rows carrying a recorded compliance decision."""
    if config.COMPLIANCE_DECISION_TYPE not in sector.columns:
        return pd.DataFrame()
    return sector[sector[config.COMPLIANCE_DECISION_TYPE].notna()].copy()


def _reference_date(decisions: pd.DataFrame) -> pd.Timestamp | None:
    """The latest decision date in the extract, used as the 'as at' point.

    Status is judged against the extract's own currency rather than today's
    date, since a quarterly extract is a historical snapshot.
    """
    dates = []
    for column in (config.COMPLIANCE_APPLIED_PARSED, config.COMPLIANCE_ENDS_PARSED):
        if column in decisions.columns:
            dates.append(decisions[column].max())
    valid = [d for d in dates if pd.notna(d)]
    return max(valid) if valid else None


def _add_status(decisions: pd.DataFrame, reference: pd.Timestamp | None) -> pd.DataFrame:
    """Label each decision Open / Closed / Undated as at the reference date."""
    decisions = decisions.copy()
    ends = decisions.get(config.COMPLIANCE_ENDS_PARSED)

    if ends is None or reference is None:
        decisions["Status"] = UNDATED
        return decisions

    decisions["Status"] = CLOSED
    # No end date recorded means the decision had not been lifted.
    decisions.loc[ends.isna(), "Status"] = OPEN
    decisions.loc[ends.notna() & (ends >= reference), "Status"] = OPEN
    return decisions


def _render_metrics(decisions: pd.DataFrame, reference: pd.Timestamp | None) -> None:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Decisions Recorded", len(decisions))
    with col2:
        st.metric("Services Affected", decisions["Service Name"].nunique())
    with col3:
        st.metric("Providers Affected", decisions["Provider Name"].nunique())
    with col4:
        open_count = int((decisions["Status"] == OPEN).sum())
        st.metric(
            "Open as at Extract",
            open_count,
            help=(
                f"Open at {reference:%d %b %Y}, the latest decision date in this "
                "extract."
                if reference is not None
                else "No parsable decision dates in this extract."
            ),
        )


def _render_by_type(decisions: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### Decisions by Type")
    counts = (
        decisions[config.COMPLIANCE_DECISION_TYPE]
        .value_counts()
        .reset_index(name="Decisions")
    )
    fig = px.bar(
        counts,
        x="Decisions",
        y=config.COMPLIANCE_DECISION_TYPE,
        orientation="h",
        color_discrete_sequence=[config.PRIMARY_COLOR],
        labels={config.COMPLIANCE_DECISION_TYPE: "Decision Type"},
        text="Decisions",
    )
    fig.update_layout(yaxis_title=None, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")


def _render_timeline(decisions: pd.DataFrame) -> None:
    applied = decisions.get(config.COMPLIANCE_APPLIED_PARSED)
    if applied is None or applied.notna().sum() == 0:
        st.info("No parsable decision dates available for the timeline.")
        return

    st.markdown("---")
    st.markdown("#### Decisions Applied Over Time")
    dated = decisions[applied.notna()].copy()
    dated["Month"] = dated[config.COMPLIANCE_APPLIED_PARSED].dt.to_period("M").dt.to_timestamp()
    monthly = (
        dated.groupby(["Month", config.COMPLIANCE_DECISION_TYPE])
        .size()
        .reset_index(name="Decisions")
    )
    fig = px.bar(
        monthly,
        x="Month",
        y="Decisions",
        color=config.COMPLIANCE_DECISION_TYPE,
        labels={config.COMPLIANCE_DECISION_TYPE: "Decision Type"},
    )
    fig.update_layout(xaxis_title=None, legend_title_text="Decision Type")
    st.plotly_chart(fig, width="stretch")


def _render_by_state(decisions: pd.DataFrame) -> None:
    if "State/Territory" not in decisions.columns:
        return
    st.markdown("---")
    st.markdown("#### Decisions by State/Territory")
    counts = decisions["State/Territory"].value_counts().reset_index(name="Decisions")
    fig = px.bar(
        counts,
        x="State/Territory",
        y="Decisions",
        color_discrete_sequence=[config.PRIMARY_COLOR],
        text="Decisions",
    )
    fig.update_layout(xaxis_title=None)
    st.plotly_chart(fig, width="stretch")


def _render_register(decisions: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### Decision Register")

    left, right = st.columns([2, 1])
    with left:
        search = st.text_input(
            "Search provider or service", key="compliance_search"
        ).strip()
    with right:
        types = sorted(decisions[config.COMPLIANCE_DECISION_TYPE].dropna().unique())
        chosen = st.multiselect(
            "Filter by decision type", options=types, default=types,
            key="compliance_types",
        )

    register = decisions[decisions[config.COMPLIANCE_DECISION_TYPE].isin(chosen)]
    if search:
        haystack = (
            register["Provider Name"].astype(str)
            + " "
            + register["Service Name"].astype(str)
        )
        register = register[haystack.str.contains(search, case=False, na=False)]

    if register.empty:
        st.info("No decisions match the current search and filters.")
        return

    columns = [c for c in DISPLAY_COLUMNS if c in register.columns]
    table = register[columns].sort_values(
        config.COMPLIANCE_APPLIED_PARSED
        if config.COMPLIANCE_APPLIED_PARSED in columns
        else columns[0],
        ascending=False,
    )
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            config.COMPLIANCE_APPLIED_PARSED: st.column_config.DateColumn(
                "Applied", format="DD MMM YYYY"
            ),
            config.COMPLIANCE_ENDS_PARSED: st.column_config.DateColumn(
                "Ends", format="DD MMM YYYY"
            ),
            "Compliance rating": st.column_config.NumberColumn(
                "Compliance rating", format="%.0f"
            ),
        },
    )
    st.caption(f"{len(table)} decision(s) shown.")
    st.download_button(
        "Download as CSV",
        table.to_csv(index=False).encode("utf-8"),
        file_name="compliance_decisions.csv",
        mime="text/csv",
    )


def render(ctx: DashboardContext) -> None:
    st.subheader("Compliance Actions Tracker")
    st.markdown(
        "Regulatory decisions recorded against services in the **currently "
        "filtered sector** (State / Size / MMM). Select a provider in the "
        "sidebar to narrow this to their services."
    )

    if config.COMPLIANCE_DECISION_TYPE not in ctx.sector.columns:
        st.warning(
            f"This extract has no '{config.COMPLIANCE_DECISION_TYPE}' column, "
            "so compliance actions cannot be tracked."
        )
        return

    scope = ctx.provider if ctx.has_provider else ctx.sector
    if ctx.has_provider:
        st.caption(f"Showing decisions for **{ctx.selected_provider}** only.")

    decisions = _decisions(scope)
    if decisions.empty:
        st.success("✅ No compliance decisions recorded for the current selection.")
        return

    reference = _reference_date(decisions)
    decisions = _add_status(decisions, reference)

    _render_metrics(decisions, reference)
    if reference is not None:
        st.caption(
            f"Status is assessed as at **{reference:%d %B %Y}** — the latest "
            "decision date in this extract, not today's date."
        )

    _render_by_type(decisions)
    _render_timeline(decisions)
    _render_by_state(decisions)
    _render_register(decisions)
