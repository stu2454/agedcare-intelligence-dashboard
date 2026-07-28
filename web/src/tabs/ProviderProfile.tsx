import { useMemo } from "react";

import { Chart, type ChartOption } from "../components/Chart";
import { DataTable, type Column } from "../components/DataTable";
import {
  Callout,
  EmptyState,
  MetricCard,
  MetricRow,
  Section,
  formatDate,
  formatNumber,
  formatPercent,
} from "../components/ui";
import {
  boxSummaries,
  concernsFor,
  flagConcerns,
  residentsExperienceAverages,
  summariseMeasures,
} from "../lib/analytics";
import * as config from "../lib/config";
import { parseReColumn, residentsExperienceColumns } from "../lib/parse";
import { mean } from "../lib/stats";
import { column, date, num, str, type Service } from "../lib/types";
import type { Dashboard } from "../state/useDashboard";
import { usePalette } from "../state/useTheme";

export function ProviderProfile({ dashboard }: { dashboard: Dashboard }) {
  const palette = usePalette();
  const { provider, hasProvider, filters, columns } = dashboard;

  const summaries = useMemo(() => summariseMeasures(provider), [provider]);
  const boxes = useMemo(() => boxSummaries(provider), [provider]);
  const flagged = useMemo(() => flagConcerns(provider), [provider]);

  const reAverages = useMemo(() => {
    const reColumns = residentsExperienceColumns(columns);
    return residentsExperienceAverages(provider, reColumns, parseReColumn);
  }, [provider, columns]);

  const reOption = useMemo<ChartOption>(() => {
    const categories = [...new Set(reAverages.map((r) => r.category))];
    return {
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      legend: { bottom: 0, textStyle: { color: palette.text } },
      grid: { left: 56, right: 20, top: 24, bottom: 70 },
      xAxis: {
        type: "category",
        data: categories,
        axisLabel: { color: palette.muted, rotate: 30 },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Avg response (%)",
        max: 100,
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: config.RE_FREQUENCY_ORDER.map((frequency, index) => ({
        name: frequency,
        type: "bar",
        stack: "responses",
        data: categories.map(
          (category) =>
            reAverages.find(
              (r) => r.category === category && r.frequency === frequency,
            )?.average ?? 0,
        ),
        itemStyle: { color: palette.ordered[index % palette.ordered.length] },
      })),
    };
  }, [reAverages, palette]);

  const qmOption = useMemo<ChartOption>(() => {
    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: palette.tooltipBg,
        formatter: (params: unknown) => {
          const entries = params as Array<{ dataIndex: number }>;
          const summary = summaries[entries[0]?.dataIndex ?? 0];
          if (!summary) return "";
          return `<strong>${summary.label}</strong><br/>Mean: ${summary.mean.toFixed(2)}<br/>Std. error: ${
            summary.sem === null ? "n/a" : summary.sem.toFixed(3)
          }`;
        },
      },
      grid: { left: 56, right: 20, top: 24, bottom: 90 },
      xAxis: {
        type: "category",
        data: summaries.map((s) => s.label),
        axisLabel: { color: palette.muted, rotate: 35, fontSize: 11 },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Average value",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "bar",
          data: summaries.map((s) => s.mean),
          itemStyle: { color: palette.primary },
        },
        {
          // Error bars: one vertical whisker per category, drawn as a custom
          // series because ECharts has no built-in error-bar type.
          type: "custom",
          renderItem: (_params: never, api: never) => {
            const apiTyped = api as unknown as {
              value: (index: number) => number;
              coord: (point: [number, number]) => [number, number];
              size: (value: [number, number]) => [number, number];
            };
            const index = apiTyped.value(0);
            const low = apiTyped.value(1);
            const high = apiTyped.value(2);
            const [x, yLow] = apiTyped.coord([index, low]);
            const [, yHigh] = apiTyped.coord([index, high]);
            const halfWidth = apiTyped.size([1, 0])[0] * 0.12;

            const line = (x1: number, y1: number, x2: number, y2: number) => ({
              type: "line" as const,
              shape: { x1, y1, x2, y2 },
              style: { stroke: palette.text, lineWidth: 1.5 },
            });

            return {
              type: "group",
              children: [
                line(x, yLow, x, yHigh),
                line(x - halfWidth, yLow, x + halfWidth, yLow),
                line(x - halfWidth, yHigh, x + halfWidth, yHigh),
              ],
            };
          },
          data: summaries.map((s, index) => [
            index,
            s.mean - (s.sem ?? 0),
            s.mean + (s.sem ?? 0),
          ]),
          silent: true,
          z: 10,
        },
      ],
    };
  }, [summaries, palette]);

  const boxOption = useMemo<ChartOption>(() => {
    return {
      tooltip: { backgroundColor: palette.tooltipBg },
      grid: { left: 56, right: 20, top: 24, bottom: 90 },
      xAxis: {
        type: "category",
        data: boxes.map((b) => b.label),
        axisLabel: { color: palette.muted, rotate: 35, fontSize: 11 },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Value",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "boxplot",
          data: boxes.map((b) => [b.min, b.q1, b.median, b.q3, b.max]),
          itemStyle: { color: "transparent", borderColor: palette.primary },
          tooltip: {
            formatter: (param: unknown) => {
              const p = param as { dataIndex: number };
              const box = boxes[p.dataIndex];
              if (!box) return "";
              return `<strong>${box.label}</strong><br/>Max: ${box.max.toFixed(2)}<br/>Q3: ${box.q3.toFixed(2)}<br/>Median: ${box.median.toFixed(2)}<br/>Q1: ${box.q1.toFixed(2)}<br/>Min: ${box.min.toFixed(2)}`;
            },
          },
        },
        {
          // Individual sites overlaid, so a provider can spot which service
          // sits outside the pack.
          type: "scatter",
          data: boxes.flatMap((box, index) =>
            box.points.map((point) => ({
              value: [index, point.value],
              name: point.name,
            })),
          ),
          symbolSize: 5,
          itemStyle: { color: palette.primary, opacity: 0.45 },
          tooltip: {
            formatter: (param: unknown) => {
              const p = param as { name: string; value: [number, number] };
              return `${p.name}<br/>Value: ${p.value[1].toFixed(2)}`;
            },
          },
        },
      ],
    };
  }, [boxes, palette]);

  const decisions = useMemo(
    () => provider.filter((s) => str(s, config.COMPLIANCE_DECISION_TYPE) !== null),
    [provider],
  );

  if (!hasProvider) {
    return (
      <EmptyState>
        Select a provider in the sidebar to see their profile.
      </EmptyState>
    );
  }

  if (provider.length === 0) {
    return (
      <EmptyState>
        No services for <strong>{filters.provider}</strong> match the current
        filters.
      </EmptyState>
    );
  }

  const suburbs = new Set(
    provider.map((s) => str(s, "Service Suburb")).filter(Boolean),
  ).size;
  const sizeCounts = new Map<string, number>();
  for (const service of provider) {
    const size = str(service, "Size") ?? "Unknown";
    sizeCounts.set(size, (sizeCounts.get(size) ?? 0) + 1);
  }

  const concernColumns: Column<Service>[] = [
    {
      key: "service",
      header: "Service",
      render: (row) => str(row, "Service Name") ?? "—",
      value: (row) => str(row, "Service Name"),
    },
    ...config.RATING_COLUMNS.map(
      (rating): Column<Service> => ({
        key: rating,
        header: rating.replace(" rating", "").replace("Overall Star Rating", "Star"),
        numeric: true,
        render: (row) => formatNumber(num(row, rating), 0),
        value: (row) => num(row, rating),
        cellClass: (row) =>
          concernsFor(row).includes(rating) ? "concern" : undefined,
      }),
    ),
  ];

  return (
    <>
      <Section
        title={filters.provider}
        description={`${provider.length} service${provider.length === 1 ? "" : "s"} matching the current filters, across ${suburbs} suburb${suburbs === 1 ? "" : "s"}. ${[...sizeCounts.entries()]
          .map(([size, count]) => `${size}: ${count}`)
          .join(" · ")}`}
      >
        <MetricRow>
          <MetricCard
            label="Overall star rating"
            value={formatNumber(mean(column(provider, "Overall Star Rating")))}
          />
          <MetricCard
            label="RN care compliance"
            value={formatPercent(mean(column(provider, config.RN_COMPLIANCE)))}
          />
          <MetricCard
            label="Total care compliance"
            value={formatPercent(mean(column(provider, config.TOTAL_COMPLIANCE)))}
          />
          <MetricCard
            label="Services flagged"
            value={String(flagged.length)}
            tone={flagged.length > 0 ? "concern" : "strength"}
            hint="Against absolute thresholds"
          />
        </MetricRow>
        <Callout tone="info">
          These are averages across the provider's services. For peer-relative
          risk see the <strong>Risk Radar</strong> and{" "}
          <strong>Anomaly Detection</strong> tabs — an average can look healthy
          while an individual site does not.
        </Callout>
      </Section>

      {reAverages.length > 0 && (
        <Section
          title="Residents' experience"
          description="Average response mix across the provider's services."
        >
          <Chart
            option={reOption}
            height={380}
            ariaLabel="Residents' experience responses by category"
          />
        </Section>
      )}

      {summaries.length > 0 && (
        <Section
          title="Average quality measures"
          description="Bars show the provider mean; whiskers show one standard error of the mean."
        >
          <Chart
            option={qmOption}
            height={400}
            ariaLabel="Average quality measures with standard error"
          />
        </Section>
      )}

      {boxes.length > 0 && (
        <Section
          title="Quality measure distribution across sites"
          description="Each dot is one service. Wide spread means performance varies materially between sites."
        >
          <Chart
            option={boxOption}
            height={420}
            ariaLabel="Box plot of quality measures across services"
          />
        </Section>
      )}

      <Section title="Compliance history">
        {decisions.length === 0 ? (
          <EmptyState>No recorded compliance decisions.</EmptyState>
        ) : (
          <DataTable
            rows={decisions}
            columns={[
              {
                key: "service",
                header: "Service",
                render: (row) => str(row, "Service Name") ?? "—",
                value: (row) => str(row, "Service Name"),
              },
              {
                key: "decision",
                header: "Decision type",
                render: (row) => str(row, config.COMPLIANCE_DECISION_TYPE) ?? "—",
                value: (row) => str(row, config.COMPLIANCE_DECISION_TYPE),
              },
              {
                key: "applied",
                header: "Applied",
                render: (row) => formatDate(date(row, config.COMPLIANCE_DATE_APPLIED)),
                value: (row) =>
                  date(row, config.COMPLIANCE_DATE_APPLIED)?.getTime() ?? null,
              },
              {
                key: "ends",
                header: "Ends",
                render: (row) => formatDate(date(row, config.COMPLIANCE_DATE_ENDS)),
                value: (row) =>
                  date(row, config.COMPLIANCE_DATE_ENDS)?.getTime() ?? null,
              },
            ]}
            initialSort={{ key: "applied", direction: "desc" }}
          />
        )}
      </Section>

      <Section
        title="Serious concerns"
        description="Services breaching an absolute threshold: star, experience, staffing or quality rating of 2 or below, or a compliance rating of 1."
      >
        {flagged.length === 0 ? (
          <Callout tone="success">
            No services meet the absolute serious-concern criteria.
          </Callout>
        ) : (
          <>
            <Callout tone="concern" title={`${flagged.length} service(s) flagged`}>
              Breaching values are shown in red.
            </Callout>
            <DataTable rows={flagged} columns={concernColumns} csvName="flagged-services" />
          </>
        )}
      </Section>
    </>
  );
}
