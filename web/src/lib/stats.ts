/**
 * Small statistics helpers.
 *
 * These replace the pandas/scipy calls from the Python version. Quantiles use
 * linear interpolation to match `numpy.quantile`'s default, so benchmark
 * figures stay identical to the previous dashboard.
 */

/** Finite numbers only — drops null, undefined and NaN. */
export function clean(values: Array<number | null | undefined>): number[] {
  return values.filter((v): v is number => v !== null && v !== undefined && Number.isFinite(v));
}

export function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/**
 * Linear-interpolation quantile, matching numpy's default method.
 * `q` is in [0, 1]. Input need not be sorted.
 */
export function quantile(values: number[], q: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 1) return sorted[0]!;

  const position = (sorted.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower]!;
  return sorted[lower]! + (sorted[upper]! - sorted[lower]!) * (position - lower);
}

export function median(values: number[]): number | null {
  return quantile(values, 0.5);
}

/** Sample standard deviation (ddof=1), matching pandas' default. */
export function stdDev(values: number[]): number | null {
  if (values.length < 2) return null;
  const m = mean(values)!;
  const variance =
    values.reduce((acc, v) => acc + (v - m) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

/** Standard error of the mean, matching pandas' `Series.sem()`. */
export function sem(values: number[]): number | null {
  if (values.length < 2) return null;
  return stdDev(values)! / Math.sqrt(values.length);
}

/**
 * Percentile rank of `score` within `distribution`, equivalent to
 * scipy's `percentileofscore(..., kind="weak")`: the percentage of values
 * less than or equal to the score.
 */
export function percentileOfScore(distribution: number[], score: number): number | null {
  if (distribution.length === 0) return null;
  const atOrBelow = distribution.filter((v) => v <= score).length;
  return (atOrBelow / distribution.length) * 100;
}

export interface IqrBounds {
  q1: number;
  q3: number;
  lower: number;
  upper: number;
}

/** Tukey fences at 1.5x the interquartile range. */
export function iqrBounds(values: number[]): IqrBounds | null {
  if (values.length === 0) return null;
  const q1 = quantile(values, 0.25)!;
  const q3 = quantile(values, 0.75)!;
  const iqr = q3 - q1;
  return { q1, q3, lower: q1 - 1.5 * iqr, upper: q3 + 1.5 * iqr };
}

/** Counts of each distinct value, ordered by count descending. */
export function valueCounts<T extends string>(values: T[]): Array<[T, number]> {
  const counts = new Map<T, number>();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}
