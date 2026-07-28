"""Loading and preparation of the Star Ratings quarterly extract.

Everything here is plain pandas so it can be exercised without a Streamlit
runtime; :func:`load_data` adds the caching layer used by the app.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from agedcare import config


class DataLoadError(Exception):
    """Raised when a workbook cannot be used by the dashboard."""


def _to_numeric(series: pd.Series) -> pd.Series:
    """Coerce a column to float, stripping percent signs from text values.

    Checks ``is_numeric_dtype`` rather than comparing against ``object``: under
    pandas 3 a column of strings reports the ``str`` dtype, so an object-only
    check would skip the percent stripping and coerce every value to NaN.
    """
    if not pd.api.types.is_numeric_dtype(series):
        series = series.astype(str).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(series, errors="coerce").astype("float64")


def _ratio_percent(actual: pd.Series, target: pd.Series) -> pd.Series:
    """Return ``actual / target`` as a float64 percentage.

    Zero targets and infinities become NaN. ``np.nan`` is used rather than
    ``pd.NA`` deliberately: ``pd.NA`` poisons the column to object dtype, which
    makes it fail every downstream ``is_numeric_dtype`` guard and silently drop
    the column from the anomaly and radar analyses.
    """
    actual = _to_numeric(actual)
    target = _to_numeric(target).replace(0, np.nan)
    ratio = (actual / target) * 100
    return ratio.replace([np.inf, -np.inf], np.nan).astype("float64")


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse the extract's day-first date strings (e.g. ``26/5/2023``)."""
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def prepare_detailed(detailed: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich the 'Detailed data' sheet.

    Coerces the categorical, rating, staffing and quality-measure columns,
    derives the two care-compliance percentages, and parses compliance dates.
    """
    detailed = detailed.copy()

    for col in config.CATEGORICAL_COLUMNS:
        if col in detailed.columns:
            detailed[col] = detailed[col].fillna("Unknown").astype(str)

    numeric_cols = [
        *config.STAFFING_COLUMNS,
        *config.RATING_COLUMNS,
        *config.QM_FIELDS,
        *residents_experience_columns(detailed),
    ]
    for col in numeric_cols:
        if col in detailed.columns:
            detailed[col] = _to_numeric(detailed[col])

    detailed[config.RN_COMPLIANCE] = _derive_compliance(
        detailed,
        "[S] Registered Nurse Care Minutes - Actual",
        "[S] Registered Nurse Care Minutes - Target",
    )
    detailed[config.TOTAL_COMPLIANCE] = _derive_compliance(
        detailed,
        "[S] Total Care Minutes - Actual",
        "[S] Total Care Minutes - Target",
    )

    for raw, parsed in (
        (config.COMPLIANCE_DATE_APPLIED, config.COMPLIANCE_APPLIED_PARSED),
        (config.COMPLIANCE_DATE_ENDS, config.COMPLIANCE_ENDS_PARSED),
    ):
        if raw in detailed.columns:
            detailed[parsed] = _parse_dates(detailed[raw])

    return detailed


def _derive_compliance(df: pd.DataFrame, actual: str, target: str) -> pd.Series:
    """Compute a care-minutes compliance percentage, or an all-NaN column."""
    if actual in df.columns and target in df.columns:
        return _ratio_percent(df[actual], df[target])
    return pd.Series(np.nan, index=df.index, dtype="float64")


def residents_experience_columns(df: pd.DataFrame) -> list[str]:
    """Return the ``[RE]`` columns that carry a response frequency."""
    return [
        col
        for col in df.columns
        if col.startswith("[RE]")
        and any(freq in col for freq in config.RE_FREQUENCY_ORDER)
    ]


def read_workbook(source) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read and prepare a Star Ratings extract.

    ``source`` is anything ``pd.read_excel`` accepts — a path or an uploaded
    file buffer. Raises :class:`DataLoadError` if the workbook is unusable.
    """
    try:
        sheets = pd.read_excel(source, sheet_name=None, engine="openpyxl")
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {source}") from exc
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        raise DataLoadError(f"Could not read the Excel file: {exc}") from exc

    detailed = sheets.get(config.DETAILED_SHEET, pd.DataFrame())
    if detailed.empty:
        raise DataLoadError(
            f"The workbook is missing the required '{config.DETAILED_SHEET}' sheet."
        )

    missing = [c for c in config.REQUIRED_COLUMNS if c not in detailed.columns]
    if missing:
        raise DataLoadError(
            f"The '{config.DETAILED_SHEET}' sheet is missing essential "
            f"columns: {', '.join(missing)}"
        )

    star_ratings = sheets.get(config.STAR_RATINGS_SHEET, pd.DataFrame())
    return star_ratings, prepare_detailed(detailed)


@st.cache_data(show_spinner="Loading and processing data...")
def load_data(source) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cached wrapper around :func:`read_workbook`."""
    return read_workbook(source)


def numeric_columns_present(df: pd.DataFrame, candidates: list[str]) -> list[str]:
    """Return the candidate columns that exist and hold numeric data."""
    return [
        c
        for c in candidates
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]


@st.cache_data
def compute_sector_benchmarks(df: pd.DataFrame, measures: list[str]) -> pd.DataFrame:
    """Return median / 75th / 90th percentiles for each measure, indexed by measure."""
    benchmarks = {}
    for measure in measures:
        empty = {"median": np.nan, "p75": np.nan, "p90": np.nan}
        if measure not in df.columns:
            benchmarks[measure] = empty
            continue
        values = pd.to_numeric(df[measure], errors="coerce").dropna()
        benchmarks[measure] = (
            empty
            if values.empty
            else {
                "median": values.median(),
                "p75": values.quantile(0.75),
                "p90": values.quantile(0.90),
            }
        )
    return pd.DataFrame(benchmarks).T


def find_iqr_outliers(df: pd.DataFrame, metrics: dict[str, str]) -> pd.DataFrame:
    """Flag services falling outside 1.5x the IQR for each metric.

    ``metrics`` maps a column name to the direction of concern, ``"lower"`` or
    ``"higher"``. Returns an empty frame with the expected columns when nothing
    is flagged.
    """
    columns = ["Provider Name", "Service Name", "Metric", "Value", "Reason", "IQR Range"]
    results: list[dict] = []

    for metric, direction in metrics.items():
        if metric not in df.columns or not pd.api.types.is_numeric_dtype(df[metric]):
            continue
        values = df[metric].dropna()
        if len(values) < config.MIN_SERVICES_FOR_OUTLIERS:
            continue

        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        bound = q1 - 1.5 * iqr if direction == "lower" else q3 + 1.5 * iqr
        mask = df[metric] < bound if direction == "lower" else df[metric] > bound
        reason = (
            f"Low Outlier (< {bound:.2f})"
            if direction == "lower"
            else f"High Outlier (> {bound:.2f})"
        )

        for _, row in df.loc[mask, ["Provider Name", "Service Name", metric]].iterrows():
            results.append(
                {
                    "Provider Name": row["Provider Name"],
                    "Service Name": row["Service Name"],
                    "Metric": metric,
                    "Value": row[metric],
                    "Reason": reason,
                    "IQR Range": f"[{q1:.2f} - {q3:.2f}]",
                }
            )

    return pd.DataFrame(results, columns=columns)


def flag_concerns(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask of services breaching any absolute concern threshold.

    Missing values never raise a flag.
    """
    flags = pd.Series(False, index=df.index)
    for column, predicate in config.CONCERN_THRESHOLDS.items():
        if column in df.columns:
            flags |= predicate(df[column]).fillna(False)
    return flags
