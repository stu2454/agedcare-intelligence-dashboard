"""Compare Providers tab: provider values against sector percentile benchmarks."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from agedcare import config, data
from agedcare.filters import DashboardContext

BENCHMARK_COLUMNS = ["Sector Median", "Sector 75th pct", "Sector 90th pct"]
PROVIDER_COLUMN = "Provider Value"

STYLING_GUIDE = (
    "**Table Styling Guide (Provider Value column):**\n"
    f"- <span style='background-color: {config.COLOUR_TOP_DECILE}; color: black; "
    "padding: 2px;'>Gold Background</span>: Top-decile performance "
    "(≥ 90th percentile of sector)\n"
    f"- <span style='background-color: {config.COLOUR_ABOVE_MEDIAN}; color: black; "
    "padding: 2px;'>Blue Background</span>: At or above median "
    "(but below 90th percentile)\n"
    f"- <span style='background-color: {config.COLOUR_BELOW_MEDIAN}; color: black; "
    "padding: 2px;'>Red Background</span>: Below median of sector"
)


def _build_comparison(
    provider_data: pd.DataFrame, peers: pd.DataFrame
) -> pd.DataFrame:
    """Join provider averages onto sector percentile benchmarks."""
    measures = [
        m
        for m in config.QUALITY_MEASURES
        if m in provider_data.columns and provider_data[m].notna().any()
    ]
    if not measures:
        return pd.DataFrame()

    benchmarks = data.compute_sector_benchmarks(peers, config.QUALITY_MEASURES)
    measures = [m for m in measures if m in benchmarks.index]
    if not measures:
        return pd.DataFrame()

    provider_values = pd.DataFrame(
        {PROVIDER_COLUMN: [provider_data[m].mean() for m in measures]}, index=measures
    )
    comparison = (
        benchmarks.loc[measures]
        .join(provider_values)
        .rename(
            columns={
                "median": "Sector Median",
                "p75": "Sector 75th pct",
                "p90": "Sector 90th pct",
            }
        )
    )
    comparison.index.name = "Quality Measure"
    return comparison.reset_index()


def _style_provider_cell(row: pd.Series) -> list[str]:
    """Shade the Provider Value cell by where it sits against the sector."""
    styles = [""] * len(row)
    value = row.get(PROVIDER_COLUMN)
    median = row.get("Sector Median")
    p90 = row.get("Sector 90th pct")

    if pd.isna(value):
        return styles
    if pd.notna(p90) and value >= p90:
        shade = f"background-color: {config.COLOUR_TOP_DECILE}; color: black;"
    elif pd.notna(median) and value >= median:
        shade = f"background-color: {config.COLOUR_ABOVE_MEDIAN}; color: black;"
    elif pd.notna(median) and value < median:
        shade = f"background-color: {config.COLOUR_BELOW_MEDIAN}; color: black;"
    else:
        shade = "color: black;"

    styles[list(row.index).index(PROVIDER_COLUMN)] = shade
    return styles


def _render_charts(comparison: pd.DataFrame, provider_name: str) -> None:
    st.write("### Provider vs Sector Benchmark Charts")
    value_columns = [
        c for c in BENCHMARK_COLUMNS + [PROVIDER_COLUMN] if c in comparison.columns
    ]

    for measure in config.QUALITY_MEASURES:
        rows = comparison[comparison["Quality Measure"] == measure]
        if rows.empty:
            st.caption(f"Data for {measure} not found in the comparison table.")
            continue

        chart_data = rows.melt(
            id_vars="Quality Measure",
            value_vars=value_columns,
            var_name="Metric",
            value_name="Score",
        ).dropna(subset=["Score"])
        if chart_data.empty:
            st.caption(f"No data to display chart for {measure}.")
            continue

        st.markdown(f"#### {measure}")
        fig = px.bar(
            chart_data,
            x="Metric",
            y="Score",
            color="Metric",
            labels={"Score": f"{measure} Score"},
            title=f"{provider_name} vs Sector for {measure}",
        )
        fig.update_layout(xaxis_title=None, showlegend=False)
        st.plotly_chart(fig, width="stretch")


def render(ctx: DashboardContext) -> None:
    st.subheader(f"Benchmark Comparison for {ctx.selected_provider}")

    if not ctx.has_provider:
        st.info("Please select a specific provider from the sidebar to compare.")
        return
    if ctx.provider.empty:
        st.warning(
            f"No data found for provider '{ctx.selected_provider}' matching filters."
        )
        return
    if ctx.sector.empty:
        st.warning("No data found for the selected sector filters (State/Size/MMM).")
        return
    if "Provider Name" not in ctx.sector.columns:
        st.warning("'Provider Name' column not found. Cannot perform comparison.")
        return

    # Benchmark against everyone except the provider itself.
    peers = ctx.sector[ctx.sector["Provider Name"] != ctx.selected_provider]
    if peers.empty:
        st.warning(
            f"No other providers in the filtered sector "
            f"(State: {ctx.selected_state}, Size: {ctx.selected_sizes}, "
            f"MMM: {ctx.selected_mmms}) to benchmark '{ctx.selected_provider}' against."
        )
        return

    comparison = _build_comparison(ctx.provider, peers)
    if comparison.empty:
        st.warning(
            f"Provider '{ctx.selected_provider}' has no comparable data for: "
            f"{', '.join(config.QUALITY_MEASURES)}."
        )
        return

    formats = {
        c: "{:.1f}"
        for c in BENCHMARK_COLUMNS + [PROVIDER_COLUMN]
        if c in comparison.columns
    }
    styled = comparison.style.apply(_style_provider_cell, axis=1).format(
        formats, na_rep="N/A"
    )

    st.write("### Summary Table")
    st.dataframe(styled, width="stretch", hide_index=True)

    _render_charts(comparison, ctx.selected_provider)
    st.markdown(STYLING_GUIDE, unsafe_allow_html=True)
