"""Column names, thresholds and display constants for the dashboard.

The Star Ratings quarterly extract uses prefixed column names: ``[QM]`` for
quality measures, ``[RE]`` for residents' experience, ``[S]`` for staffing and
``[C]`` for compliance decisions.
"""

from __future__ import annotations

from pathlib import Path

PRIMARY_COLOR = "#1f77b4"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILENAME = "star-ratings-quarterly-data-extract-february-2025.xlsx"
DEFAULT_DATA_PATH = REPO_ROOT / DEFAULT_DATA_FILENAME

DETAILED_SHEET = "Detailed data"
STAR_RATINGS_SHEET = "Star Ratings"

# Columns the app cannot function without.
REQUIRED_COLUMNS = ["Provider Name", "Service Name", "State/Territory"]

# Categorical columns coerced to string so filter widgets behave predictably.
CATEGORICAL_COLUMNS = ["Size", "MMM Code", "State/Territory", "Provider Name"]

RATING_COLUMNS = [
    "Overall Star Rating",
    "Compliance rating",
    "Residents' Experience rating",
    "Staffing rating",
    "Quality Measures rating",
]

STAFFING_COLUMNS = [
    "[S] Registered Nurse Care Minutes - Actual",
    "[S] Registered Nurse Care Minutes - Target",
    "[S] Total Care Minutes - Actual",
    "[S] Total Care Minutes - Target",
]

QM_FIELDS = [
    "[QM] Pressure injuries*",
    "[QM] Restrictive practices",
    "[QM] Unplanned weight loss*",
    "[QM] Falls and major injury - falls*",
    "[QM] Falls and major injury - major injury from a fall*",
    "[QM] Medication management - polypharmacy",
    "[QM] Medication management - antipsychotic",
]

# Derived columns computed in agedcare.data.
RN_COMPLIANCE = "RN Care Compliance %"
TOTAL_COMPLIANCE = "Total Care Compliance %"
DERIVED_COLUMNS = [RN_COMPLIANCE, TOTAL_COMPLIANCE]

# Measures compared against sector benchmarks in the Compare Providers tab.
QUALITY_MEASURES = ["Overall Star Rating", RN_COMPLIANCE, TOTAL_COMPLIANCE]

COMPLIANCE_DECISION_TYPE = "[C] Decision type"
COMPLIANCE_DATE_APPLIED = "[C] Date Decision Applied"
COMPLIANCE_DATE_ENDS = "[C] Date Decision Ends"
COMPLIANCE_COLUMNS = [
    "Service Name",
    "Compliance rating",
    COMPLIANCE_DECISION_TYPE,
    COMPLIANCE_DATE_APPLIED,
    COMPLIANCE_DATE_ENDS,
]
# Parsed date columns added by agedcare.data.
COMPLIANCE_APPLIED_PARSED = "Decision Applied"
COMPLIANCE_ENDS_PARSED = "Decision Ends"

FLAGGED_DISPLAY_COLUMNS = [
    "Service Name",
    "Overall Star Rating",
    "Compliance rating",
    "Residents' Experience rating",
    "Staffing rating",
    "Quality Measures rating",
]

RE_FREQUENCY_ORDER = ["Always", "Most of the time", "Some of the time", "Never"]

# Absolute thresholds flagging a service as a serious concern. Each entry maps a
# column to a predicate over its value.
CONCERN_THRESHOLDS = {
    "Overall Star Rating": lambda s: s <= 2.0,
    "Compliance rating": lambda s: s == 1,
    "Residents' Experience rating": lambda s: s <= 2.0,
    "Staffing rating": lambda s: s <= 2.0,
    "Quality Measures rating": lambda s: s <= 2.0,
}

# Metrics screened for IQR outliers, and the direction that indicates concern.
ANOMALY_METRICS = {
    "Overall Star Rating": "lower",
    RN_COMPLIANCE: "lower",
    TOTAL_COMPLIANCE: "lower",
    "[QM] Pressure injuries*": "higher",
    "[QM] Restrictive practices": "higher",
    "[QM] Falls and major injury - falls*": "higher",
    "[QM] Medication management - antipsychotic": "higher",
}

# Minimum sample sizes before a statistic is worth showing.
MIN_SERVICES_FOR_BENCHMARK = 3
MIN_SERVICES_FOR_OUTLIERS = 5

RADAR_CONCERN_PERCENTILE = 80
RADAR_STRENGTH_PERCENTILE = 20

# Abbreviations applied to QM labels so the radar chart stays legible.
QM_LABEL_REPLACEMENTS = [
    ("[QM] ", ""),
    ("Medication management - ", "Med Mgmt-"),
    ("Falls and major injury - ", ""),
    (" restrictive practices", " restraint"),
    (" pressure injuries", " pressure inj."),
]

# Benchmark table cell colours (Compare Providers tab).
COLOUR_TOP_DECILE = "#C9A66B"
COLOUR_ABOVE_MEDIAN = "#3A7CA5"
COLOUR_BELOW_MEDIAN = "#FDD"


def shorten_qm_label(field: str) -> str:
    """Return a compact label for a quality-measure column."""
    label = field
    for old, new in QM_LABEL_REPLACEMENTS:
        label = label.replace(old, new)
    return label
