import * as config from "../lib/config";
import { Callout, Section } from "../components/ui";

export function Introduction() {
  return (
    <>
      <Section title="About this dashboard">
        <div className="prose">
          <p>
            This dashboard analyses the official <strong>Star Ratings quarterly
            data extract</strong> published by the Australian Government. It
            provides service-level Star Ratings (overall and component) for
            government-funded residential aged care homes at a point in time.
          </p>
          <p>
            The February 2025 extract is bundled and loads automatically. To
            analyse a different quarter, drop its <code>.xlsx</code> onto the
            sidebar.
          </p>
        </div>
      </Section>

      <Section title="Getting the data">
        <div className="prose">
          <ul>
            <li>
              <strong>Source:</strong>{" "}
              <a
                href="https://www.gen-agedcaredata.gov.au/"
                target="_blank"
                rel="noreferrer noopener"
              >
                GEN Aged Care Data
              </a>{" "}
              — look for Star Ratings or the quarterly reports.
            </li>
            <li>
              <strong>Path (may change):</strong> GEN → the quarter's report →
              the <code>health.gov.au</code> publication page → the final{" "}
              <code>.xlsx</code> link.
            </li>
            <li>
              <strong>Required sheets:</strong> the workbook must contain{" "}
              <code>{config.STAR_RATINGS_SHEET}</code> and{" "}
              <code>{config.DETAILED_SHEET}</code>.
            </li>
          </ul>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            The download URL changes every quarter, so the file has to be
            fetched manually.
          </p>
        </div>
      </Section>

      <Section title="Your data stays on your machine">
        <Callout tone="success" title="Nothing is uploaded">
          Workbooks you open are parsed entirely inside this browser tab. There
          is no server and no request carrying your data — you can confirm this
          in your browser's network panel. The whole dashboard is static files,
          so it also works offline once loaded.
        </Callout>
      </Section>

      <Section title="Using the tabs">
        <div className="prose">
          <ul>
            <li>
              <strong>Sector Overview</strong> — headline compliance metrics and
              distributions for the filtered sector.
            </li>
            <li>
              <strong>Provider Profile</strong> — a single provider's services,
              quality measures and recorded concerns. Especially useful for
              providers running multiple sites.
            </li>
            <li>
              <strong>Risk Radar</strong> — percentile rank per quality measure
              against filtered sector peers.
            </li>
            <li>
              <strong>Anomaly Detection</strong> — statistical outliers by the
              interquartile range method.
            </li>
            <li>
              <strong>Compare Providers</strong> — provider values against sector
              median, 75th and 90th percentile benchmarks.
            </li>
            <li>
              <strong>Compliance Actions</strong> — recorded regulatory decisions
              with a searchable register.
            </li>
          </ul>
          <p>
            The sidebar filters (state, size, MMM code) define the peer group
            used for every benchmark, so narrowing them changes what
            "sector average" means throughout.
          </p>
        </div>
      </Section>

      <Section title="Roadmap">
        <div className="prose">
          <p>
            Real-time Star Ratings data, either through direct API access to the
            Department's GEN Aged Care Data website, or via data shared by
            participating providers into a secure Data Clean Room (DCR) —
            potentially facilitated by ARIIA.
          </p>
        </div>
      </Section>
    </>
  );
}
