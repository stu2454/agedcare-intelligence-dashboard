"""Tests for loading, cleaning and the analytical helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agedcare import config, data


class TestPrepareDetailed:
    def test_derived_compliance_columns_are_float(self, prepared):
        """Regression: pd.NA once made these object dtype, which silently
        excluded them from every is_numeric_dtype-gated analysis."""
        for column in (config.RN_COMPLIANCE, config.TOTAL_COMPLIANCE):
            assert prepared[column].dtype == np.dtype("float64")
            assert pd.api.types.is_numeric_dtype(prepared[column])

    def test_compliance_percentage_values(self, prepared):
        rn = prepared[config.RN_COMPLIANCE]
        assert rn.iloc[0] == pytest.approx(100.0)  # 40 / 40
        assert rn.iloc[2] == pytest.approx(125.0)  # 50 / 40
        assert rn.iloc[3] == pytest.approx(90.0)   # 45 / 50

    def test_zero_target_becomes_nan_not_inf(self, prepared):
        assert pd.isna(prepared[config.RN_COMPLIANCE].iloc[1])    # target 0
        assert pd.isna(prepared[config.TOTAL_COMPLIANCE].iloc[5])  # target 0
        assert not np.isinf(prepared[config.RN_COMPLIANCE].dropna()).any()

    def test_missing_target_becomes_nan(self, prepared):
        assert pd.isna(prepared[config.RN_COMPLIANCE].iloc[4])

    def test_percent_text_columns_coerced_to_numbers(self, prepared):
        """'70%' must become 70.0, not NaN."""
        column = prepared["[RE] Respect - Always"]
        assert pd.api.types.is_numeric_dtype(column)
        assert column.iloc[0] == pytest.approx(70.0)
        assert column.notna().all()

    def test_categorical_columns_are_strings(self, prepared):
        for column in config.CATEGORICAL_COLUMNS:
            assert prepared[column].map(type).eq(str).all()

    def test_compliance_dates_parsed_day_first(self, prepared):
        applied = prepared[config.COMPLIANCE_APPLIED_PARSED]
        assert applied.iloc[1] == pd.Timestamp("2024-05-10")  # 10/5/2024
        assert applied.iloc[3] == pd.Timestamp("2024-07-01")  # 1/7/2024
        assert pd.isna(applied.iloc[0])

    def test_derived_columns_exist_without_source_columns(self):
        minimal = pd.DataFrame(
            {
                "Provider Name": ["A"],
                "Service Name": ["A1"],
                "State/Territory": ["NSW"],
            }
        )
        result = data.prepare_detailed(minimal)
        for column in config.DERIVED_COLUMNS:
            assert column in result.columns
            assert result[column].isna().all()

    def test_does_not_mutate_input(self, raw_detailed):
        before = raw_detailed.copy()
        data.prepare_detailed(raw_detailed)
        pd.testing.assert_frame_equal(raw_detailed, before)


class TestReadWorkbook:
    def test_reads_valid_workbook(self, workbook):
        star_ratings, detailed = data.read_workbook(workbook)
        assert not detailed.empty
        assert len(detailed) == 6
        assert config.RN_COMPLIANCE in detailed.columns
        assert not star_ratings.empty

    def test_missing_file(self):
        with pytest.raises(data.DataLoadError, match="Could not read|not found"):
            data.read_workbook("no-such-file.xlsx")

    def test_missing_detailed_sheet(self, tmp_path):
        path = tmp_path / "bad.xlsx"
        pd.DataFrame({"a": [1]}).to_excel(path, sheet_name="Wrong", index=False)
        with pytest.raises(data.DataLoadError, match=config.DETAILED_SHEET):
            data.read_workbook(path)

    def test_missing_required_columns(self, tmp_path):
        path = tmp_path / "bad.xlsx"
        pd.DataFrame({"Provider Name": ["A"]}).to_excel(
            path, sheet_name=config.DETAILED_SHEET, index=False
        )
        with pytest.raises(data.DataLoadError, match="Service Name"):
            data.read_workbook(path)


class TestNumericColumnsPresent:
    def test_filters_to_numeric_and_present(self, prepared):
        result = data.numeric_columns_present(
            prepared, config.QM_FIELDS + ["Service Name", "Does Not Exist"]
        )
        assert result == config.QM_FIELDS

    def test_compliance_metrics_are_screenable(self, prepared):
        """The bug fix that matters: both compliance metrics reach the analyses."""
        screened = data.numeric_columns_present(prepared, list(config.ANOMALY_METRICS))
        assert config.RN_COMPLIANCE in screened
        assert config.TOTAL_COMPLIANCE in screened
        assert set(screened) == set(config.ANOMALY_METRICS)


class TestSectorBenchmarks:
    def test_percentiles(self, prepared):
        result = data.compute_sector_benchmarks.__wrapped__(
            prepared, ["Overall Star Rating"]
        )
        ratings = prepared["Overall Star Rating"]
        assert result.loc["Overall Star Rating", "median"] == ratings.median()
        assert result.loc["Overall Star Rating", "p90"] == ratings.quantile(0.90)

    def test_missing_measure_yields_nan_row(self, prepared):
        result = data.compute_sector_benchmarks.__wrapped__(prepared, ["Nope"])
        assert result.loc["Nope"].isna().all()

    def test_all_nan_measure_yields_nan_row(self):
        df = pd.DataFrame({"m": [np.nan, np.nan]})
        result = data.compute_sector_benchmarks.__wrapped__(df, ["m"])
        assert result.loc["m"].isna().all()


class TestIqrOutliers:
    def test_flags_low_and_high_outliers(self, prepared):
        result = data.find_iqr_outliers(prepared, config.ANOMALY_METRICS)
        assert not result.empty
        # G1 is the deliberately extreme service.
        assert "G1" in set(result["Service Name"])
        assert set(result.columns) == {
            "Provider Name", "Service Name", "Metric", "Value", "Reason", "IQR Range",
        }

    def test_direction_respected(self, prepared):
        result = data.find_iqr_outliers(prepared, config.ANOMALY_METRICS)
        for _, row in result.iterrows():
            expected = config.ANOMALY_METRICS[row["Metric"]]
            assert row["Reason"].startswith(
                "Low" if expected == "lower" else "High"
            )

    def test_returns_empty_frame_with_columns_when_nothing_flagged(self):
        df = pd.DataFrame(
            {
                "Provider Name": ["A"] * 6,
                "Service Name": [f"S{i}" for i in range(6)],
                "Overall Star Rating": [3.0] * 6,
            }
        )
        result = data.find_iqr_outliers(df, {"Overall Star Rating": "lower"})
        assert result.empty
        assert "Reason" in result.columns

    def test_skips_undersized_samples(self, prepared):
        result = data.find_iqr_outliers(prepared.head(3), config.ANOMALY_METRICS)
        assert result.empty

    def test_skips_absent_columns(self, prepared):
        result = data.find_iqr_outliers(prepared, {"Not A Column": "higher"})
        assert result.empty


class TestFlagConcerns:
    def test_flags_breaching_services(self, prepared):
        flags = data.flag_concerns(prepared)
        flagged = set(prepared.loc[flags, "Service Name"])
        assert "A2" in flagged  # star rating 2.0 and compliance rating 1
        assert "G1" in flagged  # star rating 1.0
        assert "B1" not in flagged  # all ratings healthy

    def test_missing_values_never_flag(self):
        df = pd.DataFrame(
            {"Overall Star Rating": [np.nan], "Compliance rating": [np.nan]}
        )
        assert not data.flag_concerns(df).any()

    def test_returns_all_false_without_threshold_columns(self):
        df = pd.DataFrame({"Unrelated": [1, 2, 3]})
        flags = data.flag_concerns(df)
        assert len(flags) == 3
        assert not flags.any()


class TestBundledExtract:
    """Guards against the real file drifting from what the app expects."""

    def test_loads_and_derives(self, bundled_extract):
        _star, detailed = data.read_workbook(bundled_extract)
        assert len(detailed) > 1000
        for column in config.DERIVED_COLUMNS:
            assert detailed[column].dtype == np.dtype("float64")
            assert detailed[column].notna().any()

    def test_all_expected_analysis_columns_present(self, bundled_extract):
        _star, detailed = data.read_workbook(bundled_extract)
        missing = [c for c in config.QM_FIELDS if c not in detailed.columns]
        assert not missing

    def test_every_anomaly_metric_is_screened(self, bundled_extract):
        _star, detailed = data.read_workbook(bundled_extract)
        screened = data.numeric_columns_present(detailed, list(config.ANOMALY_METRICS))
        assert set(screened) == set(config.ANOMALY_METRICS)
