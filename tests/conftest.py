"""Shared fixtures: a synthetic extract plus the bundled real one."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agedcare import config


@pytest.fixture
def raw_detailed() -> pd.DataFrame:
    """A small 'Detailed data' sheet exercising the awkward cases.

    Includes a zero care-minutes target (division by zero), a missing target,
    percent-formatted text ratings, and a service breaching concern thresholds.
    """
    return pd.DataFrame(
        {
            "Provider Name": ["Alpha", "Alpha", "Beta", "Beta", "Gamma", "Gamma"],
            "Service Name": ["A1", "A2", "B1", "B2", "G1", "G2"],
            "Service Suburb": ["Ada", "Bay", "Cog", "Dee", "Eve", "Fig"],
            "State/Territory": ["NSW", "NSW", "VIC", "VIC", "QLD", "QLD"],
            "Size": ["Small", "Large", "Medium", "Large", "Small", "Medium"],
            "MMM Code": ["1", "2", "10", "3", "1", "7"],
            "Overall Star Rating": [4.0, 2.0, 5.0, 3.0, 1.0, 4.0],
            "Compliance rating": [5.0, 1.0, 4.0, 5.0, 3.0, np.nan],
            "Residents' Experience rating": [4.0, 3.0, 5.0, 4.0, 2.0, 4.0],
            "Staffing rating": [3.0, 2.0, 5.0, 4.0, 1.0, 3.0],
            "Quality Measures rating": [4.0, 3.0, 4.0, 5.0, 2.0, 4.0],
            "[S] Registered Nurse Care Minutes - Actual": [40.0, 30.0, 50.0, 45.0, 20.0, 35.0],
            # Second entry is a zero target; fifth is missing entirely.
            "[S] Registered Nurse Care Minutes - Target": [40.0, 0.0, 40.0, 50.0, np.nan, 40.0],
            "[S] Total Care Minutes - Actual": [200.0, 180.0, 220.0, 210.0, 150.0, 190.0],
            "[S] Total Care Minutes - Target": [200.0, 200.0, 200.0, 200.0, 200.0, 0.0],
            "[QM] Pressure injuries*": [0.5, 0.8, 0.2, 0.4, 9.9, 0.3],
            "[QM] Restrictive practices": [18.0, 22.0, 15.0, 19.0, 60.0, 17.0],
            "[QM] Unplanned weight loss*": [4.0, 5.0, 3.0, 4.5, 12.0, 3.5],
            "[QM] Falls and major injury - falls*": [30.0, 35.0, 28.0, 31.0, 80.0, 29.0],
            "[QM] Falls and major injury - major injury from a fall*": [
                2.0, 3.0, 1.5, 2.5, 8.0, 2.0,
            ],
            "[QM] Medication management - polypharmacy": [40.0, 45.0, 38.0, 41.0, 70.0, 39.0],
            "[QM] Medication management - antipsychotic": [20.0, 25.0, 18.0, 21.0, 55.0, 19.0],
            # Percent-formatted text: must survive coercion to numeric.
            "[RE] Respect - Always": ["70%", "65%", "80%", "75%", "40%", "72%"],
            "[RE] Respect - Never": ["2%", "5%", "1%", "3%", "20%", "2%"],
            "Compliance rating notes": [None] * 6,
            config.COMPLIANCE_DECISION_TYPE: [
                None,
                "Notice to Remedy (NTR)",
                None,
                "Notice of Requirement to Agree (NTA)",
                "Notice of Decision to impose Sanction (Sanction)",
                None,
            ],
            config.COMPLIANCE_DATE_APPLIED: [
                None, "10/5/2024", None, "1/7/2024", "26/5/2023", None,
            ],
            config.COMPLIANCE_DATE_ENDS: [
                None, "14/6/2024", None, None, "5/2/2024", None,
            ],
        }
    )


@pytest.fixture
def prepared(raw_detailed):
    from agedcare import data

    return data.prepare_detailed(raw_detailed)


@pytest.fixture
def workbook(tmp_path, raw_detailed) -> str:
    """Write the synthetic frame out as a two-sheet .xlsx and return its path."""
    path = tmp_path / "extract.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"Info": ["Star Ratings summary"]}).to_excel(
            writer, sheet_name=config.STAR_RATINGS_SHEET, index=False
        )
        raw_detailed.to_excel(writer, sheet_name=config.DETAILED_SHEET, index=False)
    return str(path)


@pytest.fixture(scope="session")
def bundled_extract() -> str:
    """Path to the real bundled extract, skipping if it is absent."""
    if not config.DEFAULT_DATA_PATH.exists():
        pytest.skip("Bundled extract not present")
    return str(config.DEFAULT_DATA_PATH)
