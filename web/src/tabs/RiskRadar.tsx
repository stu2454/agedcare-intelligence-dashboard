import { useMemo } from "react";

import { Chart, type ChartOption } from "../components/Chart";
import { Callout, EmptyState, Section } from "../components/ui";
import { percentileRanks } from "../lib/analytics";
import * as config from "../lib/config";
import type { Dashboard } from "../state/useDashboard";
import { usePalette } from "../state/useTheme";

export function RiskRadar({ dashboard }: { dashboard: Dashboard }) {
  const palette = usePalette();
  const { provider, sector, hasProvider, filters } = dashboard;

  const ranks = useMemo(
    () => (hasProvider ? percentileRanks(provider, sector) : []),
    [provider, sector, hasProvider],
  );

  const option = useMemo<ChartOption>(() => {
    return {
      tooltip: {
        backgroundColor: palette.tooltipBg,
        formatter: (param: unknown) => {
          const p = param as { data: { value: number[] } };
          return ranks
            .map(
              (rank, index) =>
                `${rank.label}: ${(p.data.value[index] ?? 0).toFixed(0)}th pctl (avg ${rank.providerAvg.toFixed(2)})`,
            )
            .join("<br/>");
        },
      },
      legend: {
        bottom: 0,
        data: [filters.provider, "Sector median"],
        textStyle: { color: palette.text },
      },
      radar: {
        indicator: ranks.map((rank) => ({
          name: rank.label,
          max: 100,
        })),
        shape: "polygon",
        radius: "68%",
        center: ["50%", "54%"],
        axisName: { color: palette.muted, fontSize: 11 },
        splitLine: { lineStyle: { color: palette.grid } },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: ranks.map((rank) => rank.percentile),
              name: filters.provider,
              areaStyle: { color: palette.primary, opacity: 0.25 },
              lineStyle: { color: palette.primary, width: 2 },
              itemStyle: { color: palette.primary },
            },
            {
              value: ranks.map(() => 50),
              name: "Sector median",
              lineStyle: { color: palette.concern, type: "dashed", width: 1.5 },
              itemStyle: { color: palette.concern },
              symbol: "none",
            },
          ],
        },
      ],
    };
  }, [ranks, palette, filters.provider]);

  if (!hasProvider) {
    return (
      <EmptyState>Select a provider in the sidebar to build their risk radar.</EmptyState>
    );
  }
  if (provider.length === 0) {
    return <EmptyState>No services for this provider match the current filters.</EmptyState>;
  }
  if (sector.length < config.MIN_SERVICES_FOR_BENCHMARK) {
    return (
      <EmptyState>
        Not enough peers to benchmark against — the filtered sector has{" "}
        {sector.length} service(s), and at least {config.MIN_SERVICES_FOR_BENCHMARK}{" "}
        are needed.
      </EmptyState>
    );
  }
  if (ranks.length === 0) {
    return <EmptyState>No quality measures have enough data to rank.</EmptyState>;
  }

  const concerns = ranks.filter((r) => r.percentile >= config.RADAR_CONCERN_PERCENTILE);
  const strengths = ranks.filter((r) => r.percentile <= config.RADAR_STRENGTH_PERCENTILE);

  return (
    <>
      <Section
        title={`Risk radar — ${filters.provider}`}
        description={`Percentile rank on each quality measure against ${sector.length.toLocaleString()} services in the filtered sector.`}
      >
        <Callout tone="info" title="Lower is better">
          For these quality measures a lower value is better, so a{" "}
          <strong>lower percentile is better</strong>. Points inside the dashed
          median ring beat the sector median; points outside it suggest higher
          relative risk.
        </Callout>
        <Chart option={option} height={460} ariaLabel="Quality measure percentile radar" />
      </Section>

      <Section title="Interpretation">
        <div className="prose">
          {concerns.length > 0 ? (
            <>
              <p>
                <strong>
                  Potential areas of concern (≥ {config.RADAR_CONCERN_PERCENTILE}th
                  percentile):
                </strong>
              </p>
              <ul>
                {concerns.map((rank) => (
                  <li key={rank.field}>
                    <strong>{rank.label}</strong> — {rank.percentile.toFixed(0)}th
                    percentile, provider average {rank.providerAvg.toFixed(2)}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p>
              No quality measure reached the {config.RADAR_CONCERN_PERCENTILE}th
              percentile concern threshold.
            </p>
          )}

          {strengths.length > 0 ? (
            <>
              <p>
                <strong>
                  Potential areas of strength (≤ {config.RADAR_STRENGTH_PERCENTILE}th
                  percentile):
                </strong>
              </p>
              <ul>
                {strengths.map((rank) => (
                  <li key={rank.field}>
                    <strong>{rank.label}</strong> — {rank.percentile.toFixed(0)}th
                    percentile, provider average {rank.providerAvg.toFixed(2)}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p>
              No quality measure reached the {config.RADAR_STRENGTH_PERCENTILE}th
              percentile strength threshold.
            </p>
          )}
        </div>
      </Section>
    </>
  );
}
