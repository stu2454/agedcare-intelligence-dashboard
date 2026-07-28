import { useMemo } from "react";

import { DataTable } from "../components/DataTable";
import {
  Callout,
  EmptyState,
  MetricCard,
  MetricRow,
  Section,
} from "../components/ui";
import { findOutliers, type Outlier } from "../lib/analytics";
import * as config from "../lib/config";
import { valueCounts } from "../lib/stats";
import type { Dashboard } from "../state/useDashboard";

export function AnomalyDetection({ dashboard }: { dashboard: Dashboard }) {
  const { sector } = dashboard;
  const report = useMemo(() => findOutliers(sector), [sector]);

  const byMetric = useMemo(
    () => valueCounts(report.outliers.map((o) => o.metric)),
    [report.outliers],
  );
  const byProvider = useMemo(
    () => valueCounts(report.outliers.map((o) => o.providerName)),
    [report.outliers],
  );

  if (sector.length < config.MIN_SERVICES_FOR_OUTLIERS) {
    return (
      <EmptyState>
        Not enough services for robust outlier detection — the filtered sector
        has {sector.length}, and at least {config.MIN_SERVICES_FOR_OUTLIERS} are
        needed.
      </EmptyState>
    );
  }

  return (
    <>
      <Section
        title="Anomaly detection"
        description={`Services outside 1.5× the interquartile range within the filtered sector (${dashboard.filterDescription}).`}
      >
        <MetricRow>
          <MetricCard
            label="Outlier findings"
            value={report.outliers.length.toLocaleString()}
            tone={report.outliers.length > 0 ? "concern" : "strength"}
          />
          <MetricCard
            label="Metrics screened"
            value={`${report.screened.length} of ${Object.keys(config.ANOMALY_METRICS).length}`}
          />
          <MetricCard
            label="Services in peer group"
            value={sector.length.toLocaleString()}
          />
        </MetricRow>

        {report.skipped.length > 0 && (
          <Callout tone="warning" title="Some metrics could not be screened">
            Not enough numeric data in this extract for: {report.skipped.join(", ")}.
          </Callout>
        )}
      </Section>

      {report.outliers.length === 0 ? (
        <Callout tone="success">
          No outlier concerns identified by the IQR method.
        </Callout>
      ) : (
        <>
          <Section title="Findings">
            <DataTable<Outlier>
              rows={report.outliers}
              columns={[
                {
                  key: "provider",
                  header: "Provider",
                  render: (row) => row.providerName,
                  value: (row) => row.providerName,
                },
                {
                  key: "service",
                  header: "Service",
                  render: (row) => row.serviceName,
                  value: (row) => row.serviceName,
                },
                {
                  key: "metric",
                  header: "Metric",
                  render: (row) => row.metric,
                  value: (row) => row.metric,
                },
                {
                  key: "value",
                  header: "Value",
                  numeric: true,
                  render: (row) => row.value.toFixed(2),
                  value: (row) => row.value,
                },
                {
                  key: "reason",
                  header: "Reason",
                  render: (row) => row.reason,
                  value: (row) => row.reason,
                  cellClass: () => "concern",
                },
                {
                  key: "range",
                  header: "Sector IQR",
                  render: (row) => row.iqrRange,
                  value: (row) => row.iqrRange,
                },
              ]}
              initialSort={{ key: "provider", direction: "asc" }}
              csvName="anomaly-findings"
            />
          </Section>

          <Section title="Findings by metric">
            <DataTable
              rows={byMetric}
              columns={[
                {
                  key: "metric",
                  header: "Metric",
                  render: ([metric]) => metric,
                  value: ([metric]) => metric,
                },
                {
                  key: "count",
                  header: "Findings",
                  numeric: true,
                  render: ([, count]) => count,
                  value: ([, count]) => count,
                },
              ]}
            />
          </Section>

          <Section
            title="Providers with the most findings"
            description="A provider appearing repeatedly may warrant a closer look than any single finding suggests."
          >
            <DataTable
              rows={byProvider}
              columns={[
                {
                  key: "provider",
                  header: "Provider",
                  render: ([provider]) => provider,
                  value: ([provider]) => provider,
                },
                {
                  key: "count",
                  header: "Findings",
                  numeric: true,
                  render: ([, count]) => count,
                  value: ([, count]) => count,
                },
              ]}
              maxRows={25}
              csvName="anomaly-by-provider"
            />
          </Section>
        </>
      )}
    </>
  );
}
