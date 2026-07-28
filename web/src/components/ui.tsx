/** Small presentational building blocks shared across tabs. */

import type { ReactNode } from "react";

export function Section({
  title,
  description,
  children,
}: {
  title?: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section">
      {title && <h3 className="section-title">{title}</h3>}
      {description && <div className="section-description">{description}</div>}
      {children}
    </section>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "concern" | "strength";
}) {
  return (
    <div className={`metric metric-${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {hint && <div className="metric-hint">{hint}</div>}
    </div>
  );
}

export function MetricRow({ children }: { children: ReactNode }) {
  return <div className="metric-row">{children}</div>;
}

export function Callout({
  tone,
  title,
  children,
}: {
  tone: "info" | "warning" | "concern" | "success";
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className={`callout callout-${tone}`}>
      {title && <strong className="callout-title">{title}</strong>}
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}

/** A horizontally scrollable wrapper so wide tables never break the page. */
export function TableScroll({ children }: { children: ReactNode }) {
  return <div className="table-scroll">{children}</div>;
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "N/A";
  return value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "N/A";
  return `${value.toFixed(digits)}%`;
}

export function formatDate(value: Date | null): string {
  if (!value) return "—";
  return value.toLocaleDateString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
