# Aged Care Sector Intelligence Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A regulatory intelligence tool for analysing performance across Australia's
residential aged care providers, built with Streamlit and Plotly.

## Overview

The dashboard explores sector-wide trends and drills into individual provider
profiles using the Australian Government's Star Ratings quarterly data extract.
It combines:

- Star Ratings (Overall, Compliance, Staffing, Quality Measures, Residents' Experience)
- Compliance history and recorded regulatory decisions
- Residents' Experience survey breakdown
- Staffing compliance relative to benchmark care minutes
- Quality Measures (pressure injuries, falls, restrictive practices, medication management, and more)

![Quality Measures Distribution (Box Plot)](boxplots.png)

Providers running multiple sites can use the box plot above to see how each site
performs relative to the others.

## Data source

This dashboard analyses the official **Star Ratings quarterly data extract**
published by the Australian Government.

- **Content:** service-level Star Ratings (overall and component) for
  government-funded residential aged care homes at a point in time. The workbook
  must contain a `Star Ratings` sheet and a `Detailed data` sheet.
- **Origin:** published via the GEN Aged Care Data website and the Department of
  Health and Aged Care resources section.
- **How to obtain:** download the quarterly `.xlsx` manually — the location
  changes with each release. Start at
  [GEN Aged Care Data](https://www.gen-agedcaredata.gov.au/) and look for Star
  Ratings or the quarterly reports.

The February 2025 extract ships with this repository and loads automatically.
To analyse a different quarter, upload it under **1. Data Input** in the sidebar.

> **Important:** accuracy depends entirely on the uploaded workbook matching the
> expected structure. The app validates the required sheets and columns on load
> and reports clearly if something is missing.

## Tabs

| Tab | What it does |
| --- | --- |
| **Introduction** | Data provenance and usage instructions. |
| **Sector Overview** | Headline compliance metrics and distribution plots for the filtered sector. |
| **Provider Profile Drill-Down** | Provider profile, key metrics, Residents' Experience breakdown, quality-measure averages with standard error, per-site box plots, compliance history, and services breaching absolute concern thresholds. |
| **Quality Measures Risk Radar** | Provider percentile ranks per quality measure against filtered sector peers, with a narrative summary of relative strengths and concerns. |
| **Anomaly Detection** | IQR-based outlier screening across seven metrics, with counts by metric and provider. |
| **Compare Providers** | Provider averages against sector median / 75th / 90th percentile benchmarks, excluding the provider itself from its own peer group. |
| **Compliance Actions Tracker** | Recorded regulatory decisions: counts, breakdown by type and state, a monthly timeline, and a searchable, downloadable decision register. |

Sidebar filters (State/Territory, Service Size, MMM Code, Provider) apply across
every tab. The sector filters define the peer group used for all benchmarking.

## Running locally

**Prerequisites:** Python 3.11+ and Git.

```bash
git clone https://github.com/stu2454/agedcare-intelligence-dashboard.git
cd agedcare-intelligence-dashboard

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

The app is served at <http://localhost:8501>.

### With Docker

```bash
docker compose up --build
```

The app is served at <http://localhost:8510>.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers the data pipeline against a synthetic extract built to exercise
the awkward cases (zero and missing care-minutes targets, percent-formatted
text, missing ratings), plus end-to-end runs of the real app through Streamlit's
`AppTest` harness. Because `AppTest` executes every tab body on each run, an
unhandled exception anywhere in the dashboard fails the suite.

## Deploying to Render

The repository includes a [`render.yaml`](render.yaml) blueprint.

1. In the Render dashboard choose **New → Blueprint** and select this repository.
2. Render reads `render.yaml` and creates a Docker web service.
3. Deploy. Subsequent pushes to `main` deploy automatically (`autoDeploy: true`).

Notes:

- The container binds the `$PORT` Render injects; nothing is hardcoded.
- Health checks hit Streamlit's `/_stcore/health` endpoint.
- The blueprint targets the `singapore` region as the closest to Australia.
  Change it before creating the service — the region is fixed afterwards.
- On Render's free plan the service sleeps when idle, so the first request after
  a period of inactivity takes a while to load the extract.

## Project structure

```text
app.py                      Streamlit entrypoint: data source, filters, tab wiring
agedcare/
  config.py                 Column names, thresholds and display constants
  data.py                   Loading, cleaning, benchmarks, outliers, concern flags
  filters.py                Sidebar filters and the DashboardContext passed to tabs
  tabs/                     One module per tab, each exposing render()
tests/
  conftest.py               Synthetic extract fixtures
  test_data.py              Data pipeline and analytical helpers
  test_app.py               End-to-end AppTest runs
render.yaml                 Render blueprint
Dockerfile                  Production image (binds $PORT, runs non-root)
```

The analytical layer in `agedcare/data.py` is plain pandas with no Streamlit
dependencies beyond caching, so it can be tested and reused directly.

## Roadmap

Real-time Star Ratings data, via direct API access to the Department's GEN Aged
Care Data website, or through data shared by participating providers into a
secure Data Clean Room (DCR), potentially facilitated by ARIIA (Aged Care
Research & Industry Innovation Australia).

## Disclaimer

Demonstrator model for intelligence and policy analysis purposes. Verify all
data with official sources before making decisions.

## License

MIT
