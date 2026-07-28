"""Quality Measures Risk Radar tab: provider percentile ranks against sector peers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import percentileofscore

from agedcare import config, data
from agedcare.filters import DashboardContext

INTRO = """This radar chart shows the selected provider's performance on key
Quality Measures (QMs) relative to peers in the **currently filtered sector**
(State / Size / MMM).

**How to interpret the chart:**
*   **Axis values are percentile ranks:** each point is the provider's
    **percentile rank** for that QM against the filtered sector.
*   **Lower QM values are better** for most measures shown.
*   **Percentile interpretation:**
    *   **50% = sector median:** the <span style='color:red;'>red dashed
        line</span> marks median performance in the filtered sector.
    *   **Below 50% = better than median.** Closer to 0% is significantly better.
    *   **Above 50% = worse than median.** Closer to 100% suggests higher
        relative risk."""

GUIDE = """*   **Points INSIDE the <span style='color:red;'>red dashed line</span>
    (median):** the provider performs better (lower QM value, lower percentile)
    than the median service in the filtered sector.
*   **Points OUTSIDE the <span style='color:red;'>red dashed line</span>
    (median):** the provider performs worse than the median service. Further out
    indicates higher relative risk."""


def _percentile_ranks(
    provider_data: pd.DataFrame, benchmark: pd.DataFrame, fields: list[str]
) -> pd.DataFrame:
    """Rank each provider average against the sector distribution for that measure."""
    rows = []
    for field in fields:
        provider_avg = provider_data[field].mean()
        distribution = benchmark[field].dropna()
        if pd.isna(provider_avg) or distribution.empty:
            continue
        rows.append(
            {
                "Label": config.shorten_qm_label(field),
                "Percentile": percentileofscore(distribution, provider_avg, kind="weak"),
                "Provider Avg": provider_avg,
            }
        )
    return pd.DataFrame(rows, columns=["Label", "Percentile", "Provider Avg"])


def _build_figure(ranks: pd.DataFrame, provider_name: str) -> go.Figure:
    labels = ranks["Label"].tolist()
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=ranks["Percentile"].tolist(),
            theta=labels,
            fill="toself",
            name=f"{provider_name} (Percentile Rank)",
            customdata=[f"{avg:.2f}" for avg in ranks["Provider Avg"]],
            hovertemplate=(
                "<b>%{theta}</b><br>Percentile Rank: %{r:.1f}"
                "<br>Provider Avg: %{customdata}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=[50] * len(labels),
            theta=labels,
            mode="lines",
            line=dict(color="red", dash="dash", width=1),
            name="Sector Median (50th Percentile)",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="black")
            ),
            angularaxis=dict(tickfont=dict(size=10)),
        ),
        title=(
            f"QM Risk Radar for {provider_name}<br>"
            "(Percentile Rank vs Filtered Sector)"
        ),
        showlegend=True,
        legend=dict(yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )
    return fig


def _narrative(ranks: pd.DataFrame, provider_name: str) -> str:
    def describe(subset: pd.DataFrame) -> list[str]:
        return [
            f"**{row['Label']}** (Pctl: {row['Percentile']:.0f}%, "
            f"Avg: {row['Provider Avg']:.2f})"
            for _, row in subset.iterrows()
        ]

    high = describe(ranks[ranks["Percentile"] >= config.RADAR_CONCERN_PERCENTILE])
    low = describe(ranks[ranks["Percentile"] <= config.RADAR_STRENGTH_PERCENTILE])

    text = f"For **{provider_name}** compared to the filtered sector:\n"
    if high:
        text += (
            f"\n*   **Potential Areas of Concern "
            f"(Rank ≥ {config.RADAR_CONCERN_PERCENTILE}th Pctl):**\n"
        )
        text += "".join(f"    *   {item}\n" for item in high)
    else:
        text += (
            f"\n*   No QMs ranked at or above the "
            f"{config.RADAR_CONCERN_PERCENTILE}th percentile concern threshold.\n"
        )
    if low:
        text += (
            f"\n*   **Potential Areas of Strength "
            f"(Rank ≤ {config.RADAR_STRENGTH_PERCENTILE}th Pctl):**\n"
        )
        text += "".join(f"    *   {item}\n" for item in low)
    else:
        text += (
            f"\n*   No QMs ranked at or below the "
            f"{config.RADAR_STRENGTH_PERCENTILE}th percentile strength threshold.\n"
        )
    return text


def render(ctx: DashboardContext) -> None:
    st.subheader("Quality Measures Risk Radar")
    st.markdown(INTRO, unsafe_allow_html=True)
    st.caption("Note: percentile calculation requires the 'scipy' library.")

    if not ctx.has_provider:
        st.info("Please select a specific provider to generate their Risk Radar.")
        return
    if ctx.provider.empty:
        st.warning(
            f"No data for provider '{ctx.selected_provider}' matching filters."
        )
        return
    if ctx.sector.empty:
        st.warning("No benchmark data for the current filters.")
        return
    if len(ctx.sector) < config.MIN_SERVICES_FOR_BENCHMARK:
        st.warning(
            f"Insufficient benchmark data "
            f"(< {config.MIN_SERVICES_FOR_BENCHMARK} services)."
        )
        return

    fields = [
        f
        for f in data.numeric_columns_present(ctx.provider, config.QM_FIELDS)
        if f in data.numeric_columns_present(ctx.sector, config.QM_FIELDS)
        and ctx.sector[f].notna().any()
    ]
    if not fields:
        st.warning("No valid quality-measure columns with benchmark data found.")
        return

    ranks = _percentile_ranks(ctx.provider, ctx.sector, fields)
    if ranks.empty:
        st.warning("Could not calculate percentiles for any quality measure.")
        return

    st.plotly_chart(_build_figure(ranks, ctx.selected_provider), width="stretch")

    st.markdown("---")
    st.markdown("#### Radar Chart Interpretation Summary:")
    st.markdown(_narrative(ranks, ctx.selected_provider))
    st.caption("(Based on available QMs with calculable percentiles)")

    st.markdown("---")
    st.subheader("Quick Interpretation Guide:")
    st.markdown(GUIDE, unsafe_allow_html=True)
