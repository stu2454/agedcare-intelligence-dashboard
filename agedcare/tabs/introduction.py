"""Introduction tab: data provenance and usage instructions."""

from __future__ import annotations

import streamlit as st

from agedcare import config

BOXPLOT_IMAGE = config.REPO_ROOT / "boxplots.png"


def render() -> None:
    st.header("Welcome to the Aged Care Sector Intelligence Dashboard")
    st.markdown(
        f"""
**Data Source:** This dashboard analyses the official **Star Ratings quarterly
data extract** published by the Australian Government.

*   **Content:** Service-level Star Ratings (overall and component) for
    government-funded residential aged care homes at a point in time, across the
    'Star Ratings' and 'Detailed data' sheets.
*   **Origin:** Published via the GEN Aged Care Data website and the Department
    of Health and Aged Care resources section. February 2025 data is loaded by
    default.
*   **How to obtain:** Download the quarterly `.xlsx` extract from the official
    source — the exact location changes with each release:
    *   **GEN Aged Care Data:** [https://www.gen-agedcaredata.gov.au/](https://www.gen-agedcaredata.gov.au/)
    *   *Example path (may change):* GEN → quarter report → `health.gov.au`
        publication page → final `.xlsx` link.

**Using the dashboard:**
1.  **Obtain the file** for the quarter you want to analyse.
2.  **Upload** it under **1. Data Input** in the sidebar.
3.  *(Alternative)* The bundled `{config.DEFAULT_DATA_FILENAME}` loads
    automatically when nothing is uploaded.
4.  **Analyse** using the sidebar filters and the tabs above. The dashboard is
    especially useful for providers running multiple services — the
    'Provider Profile Drill-Down' tab uses box plots (example below) to expose
    variation in quality measures across sites.
        """
    )
    st.warning(
        f"**Important:** Use the official, complete "
        f"'{config.DEFAULT_DATA_FILENAME}' (or a later quarterly extract). "
        "The analysis depends on the uploaded data matching the expected structure."
    )
    st.markdown("---")
    st.markdown(
        """
**Future enhancements:**
This dashboard is designed to eventually incorporate real-time Star Rating data via:
*   Direct API access to the Department's GEN Aged Care Data website.
*   Data shared by participating providers into a secure Data Clean Room (DCR),
    potentially facilitated by ARIIA (Aged Care Research & Industry Innovation
    Australia).
        """
    )
    if BOXPLOT_IMAGE.exists():
        st.image(
            str(BOXPLOT_IMAGE),
            caption="Quality Measures Distribution (Box Plot)",
            width="stretch",
        )
