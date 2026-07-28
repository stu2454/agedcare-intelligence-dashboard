"""End-to-end tests driving the real Streamlit app via AppTest.

Every tab body executes on each run, so an unhandled exception anywhere in the
dashboard fails these tests.
"""

from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from agedcare import config

APP = str(config.REPO_ROOT / "app.py")
TIMEOUT = 300


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=TIMEOUT).run()


def provider_selectbox(at: AppTest):
    return next(s for s in at.selectbox if "Provider" in s.label)


@pytest.fixture(scope="module")
def app(bundled_extract) -> AppTest:
    return run_app()


@pytest.fixture(scope="module")
def with_provider(bundled_extract) -> AppTest:
    """The app with the first real provider selected."""
    at = run_app()
    box = provider_selectbox(at)
    target = next(o for o in box.options if o != "All")
    return box.select(target).run()


class TestAppBoots:
    def test_no_exceptions(self, app):
        assert not app.exception, [str(e.value) for e in app.exception]

    def test_all_tabs_present(self, app):
        labels = {t.label for t in app.tabs}
        for expected in (
            "Introduction",
            "Sector Overview",
            "Provider Profile Drill-Down",
            "Quality Measures Risk Radar",
            "Anomaly Detection",
            "Compare Providers",
            "Compliance Actions Tracker",
        ):
            assert expected in labels

    def test_default_extract_loads(self, app):
        assert any("Default data file loaded" in str(s.value) for s in app.success)

    def test_filters_rendered(self, app):
        labels = [s.label for s in app.selectbox] + [m.label for m in app.multiselect]
        assert any("State/Territory" in label for label in labels)
        assert any("Size" in label for label in labels)
        assert any("Provider" in label for label in labels)


class TestProviderSelection:
    def test_no_exceptions(self, with_provider):
        assert not with_provider.exception, [
            str(e.value) for e in with_provider.exception
        ]

    def test_provider_tabs_render_content(self, with_provider):
        text = " ".join(str(m.value) for m in with_provider.markdown)
        assert "Profile for:" in text

    def test_metrics_rendered(self, with_provider):
        labels = {m.label for m in with_provider.metric}
        assert "Overall Star Rating" in labels
        assert "RN Care Compliance (%)" in labels


class TestStateFilter:
    def test_filtering_by_state_keeps_app_healthy(self, bundled_extract):
        at = run_app()
        box = next(s for s in at.selectbox if "State" in s.label)
        target = next(o for o in box.options if o != "All")
        after = box.select(target).run()
        assert not after.exception, [str(e.value) for e in after.exception]


class TestAnomalyCoverage:
    """The regression this refactor exists to prevent."""

    def _outlier_table(self, at: AppTest) -> pd.DataFrame | None:
        for element in at.dataframe:
            value = element.value
            if isinstance(value, pd.DataFrame) and {"Metric", "Reason"} <= set(
                value.columns
            ):
                return value
        return None

    def test_care_compliance_metrics_are_screened(self, app):
        table = self._outlier_table(app)
        assert table is not None, "Anomaly Detection produced no outlier table"
        screened = set(table["Metric"])
        assert config.RN_COMPLIANCE in screened
        assert config.TOTAL_COMPLIANCE in screened

    def test_no_metrics_silently_skipped(self, app):
        """Anything not screened must be announced, not dropped in silence."""
        table = self._outlier_table(app)
        info = " ".join(str(i.value) for i in app.info)
        for metric in config.ANOMALY_METRICS:
            screened = table is not None and metric in set(table["Metric"])
            assert screened or metric in info, f"{metric} vanished without notice"


class TestComplianceTracker:
    def test_tracker_reports_decisions(self, app):
        labels = {m.label for m in app.metric}
        assert "Decisions Recorded" in labels
        assert "Services Affected" in labels
        assert "Open as at Extract" in labels

    def test_decision_count_is_positive(self, app):
        recorded = next(m for m in app.metric if m.label == "Decisions Recorded")
        assert int(recorded.value) > 0


class TestNoDefaultFile:
    def test_shows_welcome_when_no_data_available(self, monkeypatch, tmp_path):
        """With no bundled extract, the app must explain itself rather than crash."""
        at = AppTest.from_file(APP, default_timeout=TIMEOUT)
        at.session_state["_unused"] = True
        missing = tmp_path / "absent.xlsx"
        monkeypatch.setattr(config, "DEFAULT_DATA_PATH", missing)
        at.run()
        assert not at.exception, [str(e.value) for e in at.exception]
        assert any("Welcome" in str(i.value) for i in at.info)
