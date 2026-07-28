"""Anomaly Detection tab: IQR-based outlier screening across the filtered sector."""

from __future__ import annotations

import streamlit as st

from agedcare import config, data
from agedcare.filters import DashboardContext


def render(ctx: DashboardContext) -> None:
    st.subheader("Anomaly Detection (IQR Outliers)")
    st.markdown(
        "Identifies services performing outside the typical range "
        "(Q1 - 1.5*IQR to Q3 + 1.5*IQR) within the **currently filtered sector** "
        "(State / Size / MMM)."
    )

    if ctx.sector.empty:
        st.warning("No benchmark data for the current filters.")
        return
    if len(ctx.sector) < config.MIN_SERVICES_FOR_OUTLIERS:
        st.warning(
            f"Insufficient data (< {config.MIN_SERVICES_FOR_OUTLIERS} services) "
            "for robust outlier detection."
        )
        return

    outliers = data.find_iqr_outliers(ctx.sector, config.ANOMALY_METRICS)

    screened = data.numeric_columns_present(ctx.sector, list(config.ANOMALY_METRICS))
    skipped = [m for m in config.ANOMALY_METRICS if m not in screened]
    if skipped:
        st.info(
            "Not screened (column absent or non-numeric in this extract): "
            + ", ".join(skipped)
        )

    if outliers.empty:
        st.success("No potential outlier concerns identified by the IQR method.")
        return

    st.error(f"**{len(outliers)} Potential Outlier Concerns Identified (IQR Method)**")
    display = outliers.copy()
    display["Value"] = display["Value"].map("{:.2f}".format)
    st.dataframe(display, width="stretch", hide_index=True)

    st.markdown("---")
    st.write("Summary Counts:")
    left, right = st.columns(2)
    with left:
        st.dataframe(
            outliers["Metric"].value_counts().reset_index(name="Outlier Count"),
            hide_index=True,
            width="stretch",
        )
    with right:
        st.dataframe(
            outliers["Provider Name"].value_counts().reset_index(name="Outlier Count"),
            hide_index=True,
            width="stretch",
        )
