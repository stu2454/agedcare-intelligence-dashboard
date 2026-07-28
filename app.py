"""Aged Care Sector Intelligence Dashboard — Streamlit entrypoint.

Loads a Star Ratings quarterly extract (uploaded, or the bundled default),
applies the sidebar filters, and renders each analytical tab.
"""

from __future__ import annotations

import streamlit as st

from agedcare import config, data, tabs
from agedcare.filters import render_sidebar_filters

st.set_page_config(
    page_title="Aged Care Sector Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

TAB_RENDERERS = [
    ("Introduction", lambda ctx: tabs.introduction.render()),
    ("Sector Overview", tabs.sector_overview.render),
    ("Provider Profile Drill-Down", tabs.provider_profile.render),
    ("Quality Measures Risk Radar", tabs.risk_radar.render),
    ("Anomaly Detection", tabs.anomaly.render),
    ("Compare Providers", tabs.compare_providers.render),
    ("Compliance Actions Tracker", tabs.compliance_tracker.render),
]

WELCOME = f"""
### 📥 Instructions for Using the Dashboard

1. **Obtain the data file**
This dashboard analyses the **Star Ratings quarterly data extract** published by
the Australian Government.

- **Content:** Service-level Star Ratings (overall and component scores) for
  government-funded residential aged care homes, plus service characteristics
  and quality indicators.
- **Sheets required:** the workbook must include `'{config.STAR_RATINGS_SHEET}'`
  and `'{config.DETAILED_SHEET}'`.

2. **How to obtain the file**
Download the `.xlsx` from official government sources, starting at:
- **GEN Aged Care Data:** [https://www.gen-agedcaredata.gov.au/](https://www.gen-agedcaredata.gov.au/)
- Navigate to **Star Ratings** or the quarter you want.
- Follow the links to the **Department of Health and Aged Care** publication page.
- Download the extract (typically named like `{config.DEFAULT_DATA_FILENAME}`).

*⚠️ Note:* the specific download URL changes each quarter.

3. **Upload or auto-load**
- Upload your `.xlsx` under **"1. Data Input"** in the sidebar.
- If the default extract ships with this deployment, it loads automatically.
"""


def resolve_source():
    """Return ``(source, kind)`` for the uploaded file or bundled default."""
    uploaded = st.sidebar.file_uploader(
        "Upload Star Ratings Excel File (optional if the default file is present)",
        type=["xlsx", "xls"],
        help=(
            "Upload a quarterly data extract (.xlsx or .xls). If omitted, the "
            f"app loads '{config.DEFAULT_DATA_FILENAME}' when available."
        ),
    )
    if uploaded is not None:
        return uploaded, "uploaded"
    if config.DEFAULT_DATA_PATH.exists():
        return str(config.DEFAULT_DATA_PATH), "default"
    return None, "none"


def main() -> None:
    st.title("Aged Care Sector Intelligence Dashboard")
    st.sidebar.header("1. Data Input")

    source, kind = resolve_source()
    if source is None:
        st.info(
            "📈 **Welcome!** Upload a Star Ratings Excel file using the sidebar, "
            f"or make '{config.DEFAULT_DATA_FILENAME}' available alongside the app."
        )
        st.markdown(WELCOME)
        return

    try:
        _star_ratings, detailed = data.load_data(source)
    except data.DataLoadError as exc:
        st.sidebar.error("Failed to load data.")
        st.error(str(exc))
        if kind == "uploaded":
            st.warning(
                "Check the file's format and content, and that it contains the "
                f"'{config.DETAILED_SHEET}' and '{config.STAR_RATINGS_SHEET}' sheets."
            )
        return

    st.sidebar.success(
        "Uploaded data loaded!" if kind == "uploaded" else "Default data file loaded!"
    )
    st.sidebar.markdown("---")

    ctx = render_sidebar_filters(detailed)

    st.sidebar.markdown("---")
    st.sidebar.header("3. Navigate Sections")
    st.sidebar.caption("Use the tabs across the top of the page.")

    for tab, (_label, renderer) in zip(
        st.tabs([label for label, _ in TAB_RENDERERS]), TAB_RENDERERS
    ):
        with tab:
            renderer(ctx)


main()

st.markdown("---")
st.caption(
    "Disclaimer: Demonstrator model for intelligence and policy analysis "
    "purposes. Verify all data with official sources before making decisions."
)
