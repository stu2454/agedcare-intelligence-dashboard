"""Provider Profile Drill-Down tab."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from agedcare import config, data
from agedcare.filters import DashboardContext

CONCERN_STYLE = "color: red; font-weight: bold;"


def _profile_caption(provider_data: pd.DataFrame) -> str:
    suburbs = (
        provider_data["Service Suburb"].nunique()
        if "Service Suburb" in provider_data.columns
        else "N/A"
    )
    sizes = (
        provider_data["Size"].value_counts().to_dict()
        if "Size" in provider_data.columns
        else {}
    )
    return (
        f"Services Found (matching filters): {len(provider_data)} | "
        f"Unique Suburbs: {suburbs}\n"
        f"Size - Small: {sizes.get('Small', 0)} | "
        f"Medium: {sizes.get('Medium', 0)} | Large: {sizes.get('Large', 0)}"
    )


def _metric(label: str, series: pd.Series | None, suffix: str = "") -> None:
    value = series.mean() if series is not None else None
    st.metric(label, f"{value:.1f}{suffix}" if pd.notna(value) else "N/A")


def _render_residents_experience(provider_data: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### Resident Experience Breakdown (Average %)")

    re_columns = data.residents_experience_columns(provider_data)
    if not re_columns:
        st.warning("No Residents' Experience columns found.")
        return

    averages = provider_data[re_columns].mean().reset_index()
    averages.columns = ["Metric", "Average Percentage"]
    averages = averages.dropna(subset=["Average Percentage"])

    # Split "[RE] Respect - Always" into its category and frequency parts.
    parsed = averages["Metric"].str.extract(
        r"^\[RE\]\s+(.*?)\s+-\s+(Always|Most of the time|Some of the time|Never)$",
        expand=True,
    )
    parsed.columns = ["Category", "Frequency"]
    plot_data = pd.concat([parsed, averages["Average Percentage"]], axis=1).dropna(
        subset=["Category", "Frequency"]
    )

    if plot_data.empty:
        st.info("No valid Residents' Experience data.")
        return

    fig = px.bar(
        plot_data,
        x="Category",
        y="Average Percentage",
        color="Frequency",
        title="Average Residents' Experience Responses",
        labels={"Average Percentage": "Avg. Response %", "Category": "Category"},
        category_orders={"Frequency": config.RE_FREQUENCY_ORDER},
        color_discrete_sequence=px.colors.sequential.Blues_r,
        text_auto=".1f",
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        yaxis_title="Avg Response (%)",
        legend_title_text="Frequency",
    )
    fig.update_traces(textangle=0, textposition="inside", textfont_size=10)
    st.plotly_chart(fig, width="stretch")


def _render_quality_measures(provider_data: pd.DataFrame, qm_fields: list[str]) -> None:
    st.markdown("---")
    st.markdown("#### Average Quality Measures (with Standard Error)")
    if not qm_fields:
        st.warning("No valid quality-measure columns for the bar chart.")
        return

    summary = provider_data[qm_fields].agg(["mean", "sem"]).T.reset_index()
    summary.columns = ["Quality Indicator", "Mean", "SEM"]
    summary = summary.dropna(subset=["Mean"])
    if summary.empty:
        st.info("No data for the quality-measure bar chart.")
        return

    fig = px.bar(
        summary,
        x="Quality Indicator",
        y="Mean",
        error_y="SEM",
        title="Average Quality Indicators",
        color_discrete_sequence=[config.PRIMARY_COLOR],
        labels={"Mean": "Avg Value", "Quality Indicator": "Indicator"},
        hover_data={"SEM": ":.2f"},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch")


def _render_distribution(provider_data: pd.DataFrame, qm_fields: list[str]) -> None:
    st.markdown("---")
    st.markdown("#### Quality Measures Distribution (Box Plot)")
    if not qm_fields or "Service Name" not in provider_data.columns:
        st.warning("Required columns missing for the box plot.")
        return

    melted = provider_data[["Service Name"] + qm_fields].melt(
        id_vars="Service Name", var_name="Quality Indicator", value_name="Value"
    )
    melted = melted.dropna(subset=["Value"])
    if melted.empty:
        st.info("No data points for the quality-measure box plot.")
        return

    fig = px.box(
        melted,
        x="Quality Indicator",
        y="Value",
        points="all",
        hover_name="Service Name",
        title="Quality Measure Distributions",
    )
    fig.update_traces(
        marker_color=config.PRIMARY_COLOR,
        marker_outliercolor="red",
        line_color=config.PRIMARY_COLOR,
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch")


def _render_compliance_history(provider_data: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### Compliance History")

    available = [c for c in config.COMPLIANCE_COLUMNS if c in provider_data.columns]
    if config.COMPLIANCE_DECISION_TYPE not in available:
        st.warning("Compliance decision column not found.")
        return

    history = provider_data[available].dropna(
        subset=[config.COMPLIANCE_DECISION_TYPE], how="all"
    )
    if history.empty:
        st.info("No recorded compliance decisions found.")
        return

    ordered = ["Service Name"] + [c for c in available if c != "Service Name"]
    st.dataframe(history[ordered], width="stretch", hide_index=True)


def _highlight_concerns(row: pd.Series) -> list[str]:
    """Style the individual cells that breach a concern threshold."""
    styles = [""] * len(row)
    positions = {col: i for i, col in enumerate(row.index)}
    for column, predicate in config.CONCERN_THRESHOLDS.items():
        if column in positions and pd.notna(row[column]) and predicate(row[column]):
            styles[positions[column]] = CONCERN_STYLE
    return styles


def _render_concerns(provider_data: pd.DataFrame, provider_name: str) -> None:
    st.markdown("---")
    st.markdown("#### Performance Summary & Concerns")
    st.markdown(
        f"""The metrics above show average performance for **{provider_name}**
across its services (matching current filters).

**Important:** These averages are a high-level overview only. For risks,
peer-relative performance and outliers, consult:
*   the **'Quality Measures Risk Radar'** tab (comparison to filtered sector peers),
*   the **'Anomaly Detection'** tab (statistical outliers),
*   the **'Serious Concerns' table** below (absolute risk thresholds)."""
    )
    st.markdown("---")

    flagged = provider_data[data.flag_concerns(provider_data)]
    if flagged.empty:
        st.success("✅ No services met **absolute** serious concern criteria.")
        return

    st.error("⚠️ **Serious Concerns Identified (Absolute Thresholds)**")
    st.markdown(
        f"""<div style='padding: 0.5rem; border: 1px solid #d9534f;
        border-radius: 5px; background-color: #f2dede; margin-bottom: 1rem;
        color: #a94442;'><strong>{len(flagged)} service(s) meet one or more
        absolute criteria for potential concern.</strong> Review details
        below.</div>""",
        unsafe_allow_html=True,
    )

    columns = [c for c in config.FLAGGED_DISPLAY_COLUMNS if c in flagged.columns]
    if not columns:
        st.warning("Cannot display the flagged services table.")
        return

    formats = {
        c: "{:.0f}" for c in columns if "rating" in c.lower() or "star" in c.lower()
    }
    styled = (
        flagged[columns]
        .style.apply(_highlight_concerns, axis=1)
        .format(formats, na_rep="N/A")
        .set_properties(**{"text-align": "center"})
    )
    st.dataframe(styled, width="stretch", hide_index=True)


def render(ctx: DashboardContext) -> None:
    st.subheader("Provider Profile Drill-Down")

    if not ctx.has_provider:
        st.info("Please select a specific provider from the sidebar filter.")
        return
    if ctx.provider.empty:
        st.warning(
            f"No data found for provider '{ctx.selected_provider}' matching filters."
        )
        return

    provider_data = ctx.provider
    st.markdown(f"### Profile for: **{ctx.selected_provider}**")
    st.caption(_profile_caption(provider_data))

    st.markdown("---")
    st.markdown("#### Key Performance Metrics (Provider Average)")
    col1, col2, col3 = st.columns(3)
    with col1:
        _metric("Overall Star Rating", provider_data.get("Overall Star Rating"))
    with col2:
        _metric("RN Care Compliance (%)", provider_data.get(config.RN_COMPLIANCE), "%")
    with col3:
        _metric(
            "Total Care Compliance (%)", provider_data.get(config.TOTAL_COMPLIANCE), "%"
        )

    qm_fields = data.numeric_columns_present(provider_data, config.QM_FIELDS)

    _render_residents_experience(provider_data)
    _render_quality_measures(provider_data, qm_fields)
    _render_distribution(provider_data, qm_fields)
    _render_compliance_history(provider_data)
    _render_concerns(provider_data, ctx.selected_provider)
