import { useMemo } from "react";

import { Chart, type ChartOption } from "../components/Chart";
import {
  EmptyState,
  MetricCard,
  MetricRow,
  Section,
  formatPercent,
} from "../components/ui";
import { histogram } from "../lib/analytics";
import * as config from "../lib/config";
import { mean } from "../lib/stats";
import { column, num } from "../lib/types";
import type { Dashboard } from "../state/useDashboard";
import { usePalette } from "../state/useTheme";

export function SectorOverview({ dashboard }: { dashboard: Dashboard }) {
  const palette = usePalette();
  const { sector } = dashboard;

  const rnValues = useMemo(() => column(sector, config.RN_COMPLIANCE), [sector]);
  const totalValues = useMemo(
    () => column(sector, config.TOTAL_COMPLIANCE),
    [sector],
  );
  const starValues = useMemo(() => column(sector, "Overall Star Rating"), [sector]);

  const nonCompliant = useMemo(
    () => sector.filter((s) => num(s, "Compliance rating") === 1).length,
    [sector],
  );

  const rnHistogram = useMemo<ChartOption>(() => {
    const bins = histogram(rnValues, 30);
    return {
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      grid: { left: 56, right: 20, top: 24, bottom: 46 },
      xAxis: {
        type: "category",
        data: bins.map((b) => b.label),
        name: "RN care compliance (%)",
        nameLocation: "middle",
        nameGap: 30,
        axisLabel: { color: palette.muted, interval: 4 },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Services",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "bar",
          data: bins.map((b) => b.count),
          itemStyle: { color: palette.primary },
          barCategoryGap: "10%",
        },
      ],
    };
  }, [rnValues, palette]);

  const starHistogram = useMemo<ChartOption>(() => {
    // Star ratings are whole numbers 1-5, so count them directly rather than
    // binning a continuous range.
    const counts = [1, 2, 3, 4, 5].map(
      (star) => starValues.filter((v) => Math.round(v) === star).length,
    );
    return {
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      grid: { left: 56, right: 20, top: 24, bottom: 46 },
      xAxis: {
        type: "category",
        data: ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"],
        name: "Overall star rating",
        nameLocation: "middle",
        nameGap: 30,
        axisLabel: { color: palette.muted },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Services",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "bar",
          data: counts.map((count, index) => ({
            value: count,
            // Low ratings read as concerning, so colour them accordingly.
            itemStyle: {
              color: index <= 1 ? palette.concern : palette.primary,
            },
          })),
        },
      ],
    };
  }, [starValues, palette]);

  if (sector.length === 0) {
    return (
      <EmptyState>
        No services match the selected filters ({dashboard.filterDescription}).
        Widen the filters in the sidebar.
      </EmptyState>
    );
  }

  return (
    <>
      <Section
        title={`Metrics for: ${dashboard.filterDescription}`}
        description={`${sector.length.toLocaleString()} services in the current peer group.`}
      >
        <MetricRow>
          <MetricCard
            label="Avg RN care compliance"
            value={formatPercent(mean(rnValues))}
            hint={`${rnValues.length.toLocaleString()} services reporting`}
          />
          <MetricCard
            label="Avg total care compliance"
            value={formatPercent(mean(totalValues))}
            hint={`${totalValues.length.toLocaleString()} services reporting`}
          />
          <MetricCard
            label="Non-compliance rating (1)"
            value={nonCompliant.toLocaleString()}
            tone={nonCompliant > 0 ? "concern" : "neutral"}
            hint="Services rated 1 for compliance"
          />
          <MetricCard
            label="Avg overall star rating"
            value={mean(starValues)?.toFixed(1) ?? "N/A"}
            hint={`${starValues.length.toLocaleString()} services rated`}
          />
        </MetricRow>
      </Section>

      <Section
        title="RN care compliance distribution"
        description="Actual registered nurse care minutes as a percentage of target. 100% means the target was met exactly."
      >
        <Chart option={rnHistogram} ariaLabel="Histogram of RN care compliance" />
      </Section>

      <Section
        title="Overall star rating distribution"
        description="Count of services at each overall star rating."
      >
        <Chart
          option={starHistogram}
          ariaLabel="Distribution of overall star ratings"
        />
      </Section>
    </>
  );
}
