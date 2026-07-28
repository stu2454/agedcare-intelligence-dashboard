"""Sidebar filter widgets and the context object passed to each tab."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

ALL = "All"


@dataclass
class DashboardContext:
    """The filtered views and selections shared by every tab.

    ``sector`` is the extract narrowed by state / size / MMM and acts as the
    peer group for benchmarking. ``provider`` narrows ``sector`` further to the
    selected provider, and equals ``sector`` when no provider is chosen.
    """

    detailed: pd.DataFrame
    sector: pd.DataFrame
    provider: pd.DataFrame
    selected_state: str = ALL
    selected_sizes: list[str] = field(default_factory=list)
    selected_mmms: list[str] = field(default_factory=list)
    selected_provider: str = ALL

    @property
    def has_provider(self) -> bool:
        return self.selected_provider != ALL

    def filter_description(self) -> str:
        """A human-readable summary of the active sector filters."""
        parts = [self.selected_state]
        for label, selected, column in (
            ("Sizes", self.selected_sizes, "Size"),
            ("MMMs", self.selected_mmms, "MMM Code"),
        ):
            if column not in self.detailed.columns or not selected:
                continue
            # Only mention the filter when it actually narrows the data.
            if len(selected) < self.detailed[column].dropna().nunique():
                parts.append(f"{label}: {', '.join(map(str, selected))}")
        return " / ".join(parts)


def _sorted_unique(df: pd.DataFrame, column: str) -> list:
    return sorted(df[column].dropna().unique())


def _multiselect_for(df: pd.DataFrame, column: str, label: str) -> list:
    """Render a multiselect defaulting to every value, or explain its absence."""
    if column not in df.columns:
        st.sidebar.caption(f"'{column}' column not found.")
        return []

    options = _sorted_unique(df, column)
    if column == "MMM Code":
        # MMM codes are numeric-looking strings; sort them numerically when possible.
        try:
            options = sorted(options, key=int)
        except (TypeError, ValueError):
            pass

    if not options:
        st.sidebar.caption(f"No values found in '{column}'.")
        return []
    return st.sidebar.multiselect(label, options=options, default=options)


def render_sidebar_filters(detailed: pd.DataFrame) -> DashboardContext:
    """Render the filter controls and return the resulting context."""
    st.sidebar.header("2. Filter Options")

    selected_state = ALL
    if "State/Territory" in detailed.columns:
        selected_state = st.sidebar.selectbox(
            "Select State/Territory",
            options=[ALL] + _sorted_unique(detailed, "State/Territory"),
            index=0,
        )
    else:
        st.sidebar.caption("State/Territory column not found.")

    selected_sizes = _multiselect_for(detailed, "Size", "Select Service Size(s)")
    selected_mmms = _multiselect_for(detailed, "MMM Code", "Select MMM Code(s)")

    sector = detailed
    if selected_state != ALL and "State/Territory" in sector.columns:
        sector = sector[sector["State/Territory"] == selected_state]
    if selected_sizes and "Size" in sector.columns:
        sector = sector[sector["Size"].isin(selected_sizes)]
    if selected_mmms and "MMM Code" in sector.columns:
        sector = sector[sector["MMM Code"].isin(selected_mmms)]
    sector = sector.copy()

    selected_provider = ALL
    if "Provider Name" in sector.columns:
        providers = _sorted_unique(sector, "Provider Name")
        if providers:
            selected_provider = st.sidebar.selectbox(
                "Select Provider (filtered)", options=[ALL] + providers, index=0
            )
        else:
            st.sidebar.caption("No providers match filters.")
    else:
        st.sidebar.caption("'Provider Name' column not found.")

    provider = sector
    if selected_provider != ALL and "Provider Name" in provider.columns:
        provider = provider[provider["Provider Name"] == selected_provider]

    return DashboardContext(
        detailed=detailed,
        sector=sector,
        provider=provider.copy(),
        selected_state=selected_state,
        selected_sizes=selected_sizes,
        selected_mmms=selected_mmms,
        selected_provider=selected_provider,
    )
