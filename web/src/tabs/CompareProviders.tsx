import { useMemo } from "react";

import { Chart, type ChartOption } from "../components/Chart";
import { Callout, EmptyState, Section, TableScroll } from "../components/ui";
import { computeBenchmarks } from "../lib/analytics";
import * as config from "../lib/config";
import { mean } from "../lib/stats";
import { column, str } from "../lib/types";
import type { Dashboard } from "../state/useDashboard";
import { usePalette } from "../state/useTheme";

interface ComparisonRow {
  measure: string;
  median: number | null;
  p75: number | null;
  p90: number | null;
  providerValue: number | null;
}

/** Where a provider value sits relative to the sector, for cell shading. */
function standing(row: ComparisonRow): string | undefined {
  const { providerValue, median, p90 } = row;
  if (providerValue === null) return undefined;
  if (p90 !== null && providerValue >= p90) return "cell-top-decile";
  if (median !== null && providerValue >= median) return "cell-above-median";
  if (median !== null && providerValue < median) return "cell-below-median";
  return undefined;
}

export function CompareProviders({ dashboard }: { dashboard: Dashboard }) {
  const palette = usePalette();
  const { provider, sector, hasProvider, filters } = dashboard;

  // Benchmark against everyone except the provider itself, so a large provider
  // is not compared against a peer group it dominates.
  const peers = useMemo(
    () => sector.filter((s) => str(s, "Provider Name") !== filters.provider),
    [sector, filters.provider],
  );

  const rows = useMemo<ComparisonRow[]>(() => {
    const benchmarks = computeBenchmarks(peers, config.QUALITY_MEASURES);
    return benchmarks.map((benchmark) => ({
      measure: benchmark.measure,
      median: benchmark.median,
      p75: benchmark.p75,
      p90: benchmark.p90,
      providerValue: mean(column(provider, benchmark.measure)),
    }));
  }, [peers, provider]);

  const charts = useMemo(
    () =>
      rows.map((row) => {
        const labels = ["Sector median", "Sector 75th", "Sector 90th", filters.provider];
        const values = [row.median, row.p75, row.p90, row.providerValue];
        const option: ChartOption = {
          tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
          grid: { left: 60, right: 20, top: 20, bottom: 60 },
          xAxis: {
            type: "category",
            data: labels,
            axisLabel: { color: palette.muted, rotate: 15, fontSize: 11 },
            axisLine: { lineStyle: { color: palette.axis } },
          },
          yAxis: {
            type: "value",
            axisLabel: { color: palette.muted },
            splitLine: { lineStyle: { color: palette.grid } },
          },
          series: [
            {
              type: "bar",
              data: values.map((value, index) => ({
                value,
                itemStyle: {
                  // The provider's own bar is highlighted against the benchmarks.
                  color: index === 3 ? palette.primary : palette.axis,
                },
              })),
              label: {
                show: true,
                position: "top",
                color: palette.text,
                formatter: (param: unknown) => {
                  const p = param as { value: number | null };
                  return p.value === null ? "" : p.value.toFixed(1);
                },
              },
            },
          ],
        };
        return { measure: row.measure, option };
      }),
    [rows, palette, filters.provider],
  );

  if (!hasProvider) {
    return <EmptyState>Select a provider in the sidebar to compare them against the sector.</EmptyState>;
  }
  if (provider.length === 0) {
    return <EmptyState>No services for this provider match the current filters.</EmptyState>;
  }
  if (peers.length === 0) {
    return (
      <EmptyState>
        No other providers in the filtered sector to benchmark against. Widen the
        filters in the sidebar.
      </EmptyState>
    );
  }

  return (
    <>
      <Section
        title={`${filters.provider} vs sector`}
        description={`Benchmarked against ${peers.length.toLocaleString()} services from other providers in the filtered sector.`}
      >
        <TableScroll>
          <table>
            <thead>
              <tr>
                <th>Quality measure</th>
                <th className="numeric">Sector median</th>
                <th className="numeric">Sector 75th pct</th>
                <th className="numeric">Sector 90th pct</th>
                <th className="numeric">Provider value</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.measure}>
                  <td>{row.measure}</td>
                  <td className="numeric">{row.median?.toFixed(1) ?? "N/A"}</td>
                  <td className="numeric">{row.p75?.toFixed(1) ?? "N/A"}</td>
                  <td className="numeric">{row.p90?.toFixed(1) ?? "N/A"}</td>
                  <td className={`numeric ${standing(row) ?? ""}`}>
                    {row.providerValue?.toFixed(1) ?? "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>

        <div className="legend-swatches">
          <span
            className="swatch"
            style={{ ["--swatch-color" as string]: "var(--strength)" }}
          >
            Top decile (≥ 90th percentile)
          </span>
          <span
            className="swatch"
            style={{ ["--swatch-color" as string]: "var(--primary)" }}
          >
            At or above median
          </span>
          <span
            className="swatch"
            style={{ ["--swatch-color" as string]: "var(--concern)" }}
          >
            Below median
          </span>
        </div>

        <Callout tone="info">
          For star ratings and care compliance a <strong>higher</strong> value is
          better, so above-median shading is favourable here. This is the
          opposite of the quality measures on the Risk Radar tab.
        </Callout>
      </Section>

      {charts.map(({ measure, option }) => (
        <Section key={measure} title={measure}>
          <Chart option={option} height={280} ariaLabel={`${measure} against sector benchmarks`} />
        </Section>
      ))}
    </>
  );
}
