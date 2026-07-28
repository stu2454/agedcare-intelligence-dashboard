/**
 * Sector benchmarks, outlier screening, percentile ranks and concern flags.
 *
 * Pure functions over `Service[]` — no framework dependencies, so they are
 * directly unit-testable.
 */

import * as config from "./config";
import {
  clean,
  iqrBounds,
  mean,
  percentileOfScore,
  quantile,
  sem,
} from "./stats";
import { column, num, str, type Service } from "./types";

export interface Benchmark {
  measure: string;
  median: number | null;
  p75: number | null;
  p90: number | null;
}

/** Median / 75th / 90th percentiles for each measure across the given services. */
export function computeBenchmarks(
  services: Service[],
  measures: readonly string[],
): Benchmark[] {
  return measures.map((measure) => {
    const values = column(services, measure);
    if (values.length === 0) {
      return { measure, median: null, p75: null, p90: null };
    }
    return {
      measure,
      median: quantile(values, 0.5),
      p75: quantile(values, 0.75),
      p90: quantile(values, 0.9),
    };
  });
}

export interface Outlier {
  providerName: string;
  serviceName: string;
  metric: string;
  value: number;
  reason: string;
  iqrRange: string;
}

export interface OutlierReport {
  outliers: Outlier[];
  /** Metrics actually screened. */
  screened: string[];
  /** Metrics skipped because no column had enough numeric data. */
  skipped: string[];
}

/**
 * Flag services outside 1.5x the IQR for each metric.
 *
 * Reports which metrics were skipped rather than dropping them silently — the
 * original Python version quietly screened only five of its seven metrics.
 */
export function findOutliers(
  services: Service[],
  metrics: Record<string, config.ConcernDirection> = config.ANOMALY_METRICS,
): OutlierReport {
  const outliers: Outlier[] = [];
  const screened: string[] = [];
  const skipped: string[] = [];

  for (const [metric, direction] of Object.entries(metrics)) {
    const values = column(services, metric);
    if (values.length < config.MIN_SERVICES_FOR_OUTLIERS) {
      skipped.push(metric);
      continue;
    }
    screened.push(metric);

    const bounds = iqrBounds(values)!;
    const limit = direction === "lower" ? bounds.lower : bounds.upper;
    const range = `[${bounds.q1.toFixed(2)} - ${bounds.q3.toFixed(2)}]`;
    const reason =
      direction === "lower"
        ? `Low Outlier (< ${limit.toFixed(2)})`
        : `High Outlier (> ${limit.toFixed(2)})`;

    for (const service of services) {
      const value = num(service, metric);
      if (value === null) continue;
      if (direction === "lower" ? value < limit : value > limit) {
        outliers.push({
          providerName: str(service, "Provider Name") ?? "Unknown",
          serviceName: str(service, "Service Name") ?? "Unknown",
          metric,
          value,
          reason,
          iqrRange: range,
        });
      }
    }
  }

  return { outliers, screened, skipped };
}

export interface PercentileRank {
  field: string;
  label: string;
  percentile: number;
  providerAvg: number;
}

/** Rank each provider average against the sector distribution for that measure. */
export function percentileRanks(
  providerServices: Service[],
  sectorServices: Service[],
  fields: readonly string[] = config.QM_FIELDS,
): PercentileRank[] {
  const ranks: PercentileRank[] = [];

  for (const field of fields) {
    const providerAvg = mean(column(providerServices, field));
    const distribution = column(sectorServices, field);
    if (providerAvg === null || distribution.length === 0) continue;

    const percentile = percentileOfScore(distribution, providerAvg);
    if (percentile === null) continue;

    ranks.push({
      field,
      label: config.shortenQmLabel(field),
      percentile,
      providerAvg,
    });
  }

  return ranks;
}

/** Which concern thresholds a service breaches. Empty when none. */
export function concernsFor(service: Service): string[] {
  const breached: string[] = [];
  for (const [columnName, predicate] of Object.entries(config.CONCERN_THRESHOLDS)) {
    const value = num(service, columnName);
    if (value !== null && predicate(value)) breached.push(columnName);
  }
  return breached;
}

/** Services breaching at least one absolute concern threshold. */
export function flagConcerns(services: Service[]): Service[] {
  return services.filter((service) => concernsFor(service).length > 0);
}

export interface MeasureSummary {
  field: string;
  label: string;
  mean: number;
  sem: number | null;
}

/** Mean and standard error for each quality measure that has data. */
export function summariseMeasures(
  services: Service[],
  fields: readonly string[] = config.QM_FIELDS,
): MeasureSummary[] {
  const summaries: MeasureSummary[] = [];
  for (const field of fields) {
    const values = column(services, field);
    const average = mean(values);
    if (average === null) continue;
    summaries.push({
      field,
      label: config.shortenQmLabel(field),
      mean: average,
      sem: sem(values),
    });
  }
  return summaries;
}

export interface ReAverage {
  category: string;
  frequency: string;
  average: number;
}

/** Average response percentage per Residents' Experience category and frequency. */
export function residentsExperienceAverages(
  services: Service[],
  reColumns: string[],
  parseColumn: (name: string) => { category: string; frequency: string } | null,
): ReAverage[] {
  const averages: ReAverage[] = [];
  for (const name of reColumns) {
    const parsed = parseColumn(name);
    if (!parsed) continue;
    const average = mean(column(services, name));
    if (average === null) continue;
    averages.push({ ...parsed, average });
  }
  return averages;
}

/** Box-plot five-number summary plus the individual points, per measure. */
export interface BoxSummary {
  field: string;
  label: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  points: Array<{ name: string; value: number }>;
}

export function boxSummaries(
  services: Service[],
  fields: readonly string[] = config.QM_FIELDS,
): BoxSummary[] {
  const summaries: BoxSummary[] = [];

  for (const field of fields) {
    const points: Array<{ name: string; value: number }> = [];
    for (const service of services) {
      const value = num(service, field);
      if (value === null) continue;
      points.push({ name: str(service, "Service Name") ?? "Unknown", value });
    }

    const values = clean(points.map((p) => p.value));
    if (values.length === 0) continue;

    summaries.push({
      field,
      label: config.shortenQmLabel(field),
      min: Math.min(...values),
      q1: quantile(values, 0.25)!,
      median: quantile(values, 0.5)!,
      q3: quantile(values, 0.75)!,
      max: Math.max(...values),
      points,
    });
  }

  return summaries;
}

/** Evenly spaced histogram bins over the values present for a column. */
export interface HistogramBin {
  label: string;
  start: number;
  end: number;
  count: number;
}

export function histogram(values: number[], binCount: number): HistogramBin[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);

  if (min === max) {
    return [{ label: min.toFixed(1), start: min, end: max, count: values.length }];
  }

  const width = (max - min) / binCount;
  const bins: HistogramBin[] = Array.from({ length: binCount }, (_, i) => ({
    label: `${(min + i * width).toFixed(1)}`,
    start: min + i * width,
    end: min + (i + 1) * width,
    count: 0,
  }));

  for (const value of values) {
    // The final bin is closed on the right so the maximum lands inside it.
    const index = Math.min(Math.floor((value - min) / width), binCount - 1);
    bins[index]!.count += 1;
  }

  return bins;
}
