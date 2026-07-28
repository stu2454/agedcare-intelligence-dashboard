import { useState } from "react";

import { Sidebar } from "./components/Sidebar";
import { Callout } from "./components/ui";
import { useDashboard } from "./state/useDashboard";
import { AnomalyDetection } from "./tabs/AnomalyDetection";
import { CompareProviders } from "./tabs/CompareProviders";
import { ComplianceTracker } from "./tabs/ComplianceTracker";
import { Introduction } from "./tabs/Introduction";
import { ProviderProfile } from "./tabs/ProviderProfile";
import { RiskRadar } from "./tabs/RiskRadar";
import { SectorOverview } from "./tabs/SectorOverview";

const TABS = [
  { id: "introduction", label: "Introduction" },
  { id: "sector", label: "Sector Overview" },
  { id: "provider", label: "Provider Profile" },
  { id: "radar", label: "Risk Radar" },
  { id: "anomaly", label: "Anomaly Detection" },
  { id: "compare", label: "Compare Providers" },
  { id: "compliance", label: "Compliance Actions" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function App() {
  const dashboard = useDashboard();
  const [active, setActive] = useState<TabId>("introduction");

  if (dashboard.status === "loading") {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Loading the Star Ratings extract…</p>
      </div>
    );
  }

  return (
    <div className="app">
      <Sidebar dashboard={dashboard} />

      <main className="main">
        <header className="masthead">
          <div>
            <h1>Aged Care Sector Intelligence Dashboard</h1>
            <p>
              Regulatory intelligence across Australia's residential aged care
              providers, from the Star Ratings quarterly data extract.
            </p>
          </div>
        </header>

        {dashboard.error && (
          <Callout tone="concern" title="Could not load that file">
            {dashboard.error}
          </Callout>
        )}

        <div className="tablist" role="tablist" aria-label="Dashboard sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={active === tab.id}
              aria-controls={`panel-${tab.id}`}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div
          role="tabpanel"
          id={`panel-${active}`}
          aria-labelledby={`tab-${active}`}
        >
          {/* Only the active tab renders — unlike the Streamlit version, which
              executed every tab body on every interaction. */}
          {active === "introduction" && <Introduction />}
          {active === "sector" && <SectorOverview dashboard={dashboard} />}
          {active === "provider" && <ProviderProfile dashboard={dashboard} />}
          {active === "radar" && <RiskRadar dashboard={dashboard} />}
          {active === "anomaly" && <AnomalyDetection dashboard={dashboard} />}
          {active === "compare" && <CompareProviders dashboard={dashboard} />}
          {active === "compliance" && <ComplianceTracker dashboard={dashboard} />}
        </div>

        <footer className="footer">
          Demonstrator model for intelligence and policy analysis purposes.
          Verify all data with official sources before making decisions.
        </footer>
      </main>
    </div>
  );
}
