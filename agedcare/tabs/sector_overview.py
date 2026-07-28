"""Sector Overview tab: headline metrics and distributions for the filtered sector."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from agedcare import config
from agedcare.filters import DashboardContext


def _metric(label: str, value: float, suffix: str = "") -> None:
    st.metric(label, f"{value:.1f}{suffix}" if pd.notna(value) else "N/A")


def _histogram(df: pd.DataFrame, column: str, nbins: int, title: str) -> None:
    if column in df.columns and df[column].notna().any():
        fig = px.histogram(df.dropna(subset=[column]), x=column, nbins=nbins, title=title)
        st.plotly_chart(fig, width="stretch")
    else:
        st.caption(f"{column} N/A.")


def render(ctx: DashboardContext) -> None:
    st.subheader("Sector Overview")
    description = ctx.filter_description()
    st.markdown(f"#### Metrics for: **{description}**")

    if ctx.sector.empty:
        st.warning(f"No services match the selected filters: {description}")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        _metric("Avg RN Care Compliance (%)", ctx.sector[config.RN_COMPLIANCE].mean(), "%")
    with col2:
        _metric(
            "Avg Total Care Compliance (%)",
            ctx.sector[config.TOTAL_COMPLIANCE].mean(),
            "%",
        )
    with col3:
        rating = ctx.sector.get("Compliance rating")
        non_compliant = (
            int((rating == 1).sum())
            if rating is not None and pd.api.types.is_numeric_dtype(rating)
            else 0
        )
        st.metric("Services with Non-Compliance Rating (1)", non_compliant)

    st.markdown("---")
    st.markdown("#### Distribution Plots")
    left, right = st.columns(2)
    with left:
        _histogram(ctx.sector, config.RN_COMPLIANCE, 30, "RN Care Compliance %")
    with right:
        _histogram(ctx.sector, "Overall Star Rating", 5, "Overall Star Ratings")
