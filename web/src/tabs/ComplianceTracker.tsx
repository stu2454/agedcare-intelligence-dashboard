import { useMemo, useState } from "react";

import { Chart, type ChartOption } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import {
  Callout,
  EmptyState,
  MetricCard,
  MetricRow,
  Section,
  formatDate,
} from "../components/ui";
import * as config from "../lib/config";
import { valueCounts } from "../lib/stats";
import { date, num, str, type Service } from "../lib/types";
import type { Dashboard } from "../state/useDashboard";
import { usePalette } from "../state/useTheme";

type Status = "Open" | "Closed";

interface Decision {
  service: Service;
  providerName: string;
  serviceName: string;
  state: string;
  decisionType: string;
  applied: Date | null;
  ends: Date | null;
  status: Status;
}

/**
 * The extract is a historical snapshot, so a decision's status is judged
 * against the latest decision date it contains rather than today's date —
 * otherwise every decision in an older extract reads as expired.
 */
function referenceDate(decisions: Decision[]): Date | null {
  let latest: Date | null = null;
  for (const decision of decisions) {
    for (const value of [decision.applied, decision.ends]) {
      if (value && (latest === null || value > latest)) latest = value;
    }
  }
  return latest;
}

export function ComplianceTracker({ dashboard }: { dashboard: Dashboard }) {
  const palette = usePalette();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");

  const scope = dashboard.hasProvider ? dashboard.provider : dashboard.sector;

  const decisions = useMemo<Decision[]>(() => {
    const rows: Decision[] = [];
    for (const service of scope) {
      const decisionType = str(service, config.COMPLIANCE_DECISION_TYPE);
      if (decisionType === null) continue;
      rows.push({
        service,
        providerName: str(service, "Provider Name") ?? "Unknown",
        serviceName: str(service, "Service Name") ?? "Unknown",
        state: str(service, "State/Territory") ?? "Unknown",
        decisionType,
        applied: date(service, config.COMPLIANCE_DATE_APPLIED),
        ends: date(service, config.COMPLIANCE_DATE_ENDS),
        status: "Closed",
      });
    }

    const reference = referenceDate(rows);
    for (const row of rows) {
      // No end date recorded means the decision had not been lifted.
      row.status =
        row.ends === null || (reference !== null && row.ends >= reference)
          ? "Open"
          : "Closed";
    }
    return rows;
  }, [scope]);

  const reference = useMemo(() => referenceDate(decisions), [decisions]);

  const byType = useMemo(
    () => valueCounts(decisions.map((d) => d.decisionType)),
    [decisions],
  );
  const byState = useMemo(
    () => valueCounts(decisions.map((d) => d.state)),
    [decisions],
  );

  const typeOption = useMemo<ChartOption>(() => {
    const ordered = [...byType].reverse();
    return {
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      grid: { left: 8, right: 40, top: 16, bottom: 20, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      yAxis: {
        type: "category",
        data: ordered.map(([type]) => type),
        axisLabel: { color: palette.muted, width: 260, overflow: "truncate" },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      series: [
        {
          type: "bar",
          data: ordered.map(([, count]) => count),
          itemStyle: { color: palette.primary },
          label: { show: true, position: "right", color: palette.text },
        },
      ],
    };
  }, [byType, palette]);

  const timelineOption = useMemo<ChartOption>(() => {
    const monthly = new Map<string, number>();
    for (const decision of decisions) {
      if (!decision.applied) continue;
      const key = `${decision.applied.getFullYear()}-${String(decision.applied.getMonth() + 1).padStart(2, "0")}`;
      monthly.set(key, (monthly.get(key) ?? 0) + 1);
    }
    const months = [...monthly.entries()].sort((a, b) => a[0].localeCompare(b[0]));

    return {
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      grid: { left: 50, right: 20, top: 20, bottom: 60 },
      xAxis: {
        type: "category",
        data: months.map(([month]) => month),
        axisLabel: { color: palette.muted, rotate: 45, fontSize: 10 },
        axisLine: { lineStyle: { color: palette.axis } },
      },
      yAxis: {
        type: "value",
        name: "Decisions",
        axisLabel: { color: palette.muted },
        splitLine: { lineStyle: { color: palette.grid } },
      },
      series: [
        {
          type: "bar",
          data: months.map(([, count]) => count),
          itemStyle: { color: palette.primary },
        },
      ],
    };
  }, [decisions, palette]);

  const stateOption = useMemo<ChartOption>(
    () => ({
      tooltip: { trigger: "axis", backgroundColor: palette.tooltipBg },
      grid: { left: 50, right: 20, top: 20, bottom: 40 },
      xAxis: {
        type: "category",
        data: byState.map(([state]) => state),
        axisLabel: { color: palette.muted },
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
          data: byState.map(([, count]) => count),
          itemStyle: { color: palette.primary },
          label: { show: true, position: "top", color: palette.text },
        },
      ],
    }),
    [byState, palette],
  );

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return decisions.filter((decision) => {
      if (typeFilter !== "All" && decision.decisionType !== typeFilter) return false;
      if (!needle) return true;
      return (
        decision.providerName.toLowerCase().includes(needle) ||
        decision.serviceName.toLowerCase().includes(needle)
      );
    });
  }, [decisions, search, typeFilter]);

  if (decisions.length === 0) {
    return (
      <Callout tone="success" title="No compliance decisions recorded">
        Nothing is recorded against{" "}
        {dashboard.hasProvider ? dashboard.filters.provider : "the current selection"}.
      </Callout>
    );
  }

  const openCount = decisions.filter((d) => d.status === "Open").length;
  const services = new Set(decisions.map((d) => d.serviceName)).size;
  const providers = new Set(decisions.map((d) => d.providerName)).size;

  return (
    <>
      <Section
        title="Compliance actions"
        description={
          dashboard.hasProvider
            ? `Decisions recorded against ${dashboard.filters.provider}.`
            : `Decisions recorded across the filtered sector (${dashboard.filterDescription}).`
        }
      >
        <MetricRow>
          <MetricCard label="Decisions recorded" value={decisions.length.toLocaleString()} />
          <MetricCard label="Services affected" value={services.toLocaleString()} />
          <MetricCard label="Providers affected" value={providers.toLocaleString()} />
          <MetricCard
            label="Open at extract date"
            value={openCount.toLocaleString()}
            tone={openCount > 0 ? "concern" : "neutral"}
          />
        </MetricRow>
        {reference && (
          <Callout tone="info">
            Status is assessed as at <strong>{formatDate(reference)}</strong> — the
            latest decision date in this extract, not today's date. A quarterly
            extract is a historical snapshot.
          </Callout>
        )}
      </Section>

      <Section title="Decisions by type">
        <Chart
          option={typeOption}
          height={Math.max(220, byType.length * 46)}
          ariaLabel="Compliance decisions by type"
        />
      </Section>

      <Section
        title="Decisions applied over time"
        description="Month the decision took effect."
      >
        <Chart option={timelineOption} height={300} ariaLabel="Compliance decisions over time" />
      </Section>

      {byState.length > 1 && (
        <Section title="Decisions by state and territory">
          <Chart option={stateOption} height={280} ariaLabel="Compliance decisions by state" />
        </Section>
      )}

      <Section title="Decision register">
        <div className="toolbar">
          <label className="field">
            <span className="field-label">Search provider or service</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Start typing…"
            />
          </label>
          <label className="field">
            <span className="field-label">Decision type</span>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              <option value="All">All types</option>
              {byType.map(([type]) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
        </div>

        {filtered.length === 0 ? (
          <EmptyState>No decisions match the current search and filters.</EmptyState>
        ) : (
          <DataTable<Decision>
            rows={filtered}
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
                key: "state",
                header: "State",
                render: (row) => row.state,
                value: (row) => row.state,
              },
              {
                key: "type",
                header: "Decision type",
                render: (row) => row.decisionType,
                value: (row) => row.decisionType,
              },
              {
                key: "applied",
                header: "Applied",
                render: (row) => formatDate(row.applied),
                value: (row) => row.applied?.getTime() ?? null,
              },
              {
                key: "ends",
                header: "Ends",
                render: (row) => formatDate(row.ends),
                value: (row) => row.ends?.getTime() ?? null,
              },
              {
                key: "status",
                header: "Status",
                render: (row) => (
                  <span
                    className={`badge ${row.status === "Open" ? "badge-open" : "badge-closed"}`}
                  >
                    {row.status}
                  </span>
                ),
                value: (row) => row.status,
              },
              {
                key: "rating",
                header: "Compliance rating",
                numeric: true,
                render: (row) => num(row.service, "Compliance rating")?.toFixed(0) ?? "—",
                value: (row) => num(row.service, "Compliance rating"),
              },
            ]}
            initialSort={{ key: "applied", direction: "desc" }}
            csvName="compliance-decisions"
          />
        )}
      </Section>
    </>
  );
}
