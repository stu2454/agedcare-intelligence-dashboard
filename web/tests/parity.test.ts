/**
 * Parity with the Python implementation.
 *
 * `python-reference.json` is generated from the pandas/scipy dashboard against
 * the same bundled extract. These tests assert the TypeScript port reproduces
 * those figures, so the rewrite is provably not a behaviour change.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  computeBenchmarks,
  findOutliers,
  flagConcerns,
  summariseMeasures,
} from "../src/lib/analytics";
import * as config from "../src/lib/config";
import { readExtract } from "../src/lib/parse";
import { mean, quantile } from "../src/lib/stats";
import { column, distinct, str } from "../src/lib/types";

const here = dirname(fileURLToPath(import.meta.url));
const reference = JSON.parse(
  readFileSync(join(here, "python-reference.json"), "utf-8"),
) as {
  rowCount: number;
  providerCount: number;
  rnMean: number;
  totalMean: number;
  rnNotNull: number;
  starMedian: number;
  starP90: number;
  rnP75: number;
  outlierCount: number;
  outliersByMetric: Record<string, number>;
  concernCount: number;
  decisionCount: number;
  qmMeans: Record<string, number>;
  qmSem: Record<string, number>;
};

function loadBundledExtract() {
  const path = join(here, "..", "..", config.DEFAULT_DATA_FILENAME);
  const file = readFileSync(path);
  // Copy into a plain ArrayBuffer so the parser sees exactly what fetch yields.
  const buffer = file.buffer.slice(
    file.byteOffset,
    file.byteOffset + file.byteLength,
  ) as ArrayBuffer;
  return readExtract(buffer);
}

const { services } = loadBundledExtract();

describe("parsing the real extract", () => {
  it("reads every service row", () => {
    expect(services.length).toBe(reference.rowCount);
  });

  it("finds the same number of providers", () => {
    expect(distinct(services, "Provider Name").length).toBe(reference.providerCount);
  });

  it("derives care compliance for the same number of services", () => {
    expect(column(services, config.RN_COMPLIANCE).length).toBe(reference.rnNotNull);
  });

  it("matches the Python care-compliance means", () => {
    expect(mean(column(services, config.RN_COMPLIANCE))!).toBeCloseTo(
      reference.rnMean,
      8,
    );
    expect(mean(column(services, config.TOTAL_COMPLIANCE))!).toBeCloseTo(
      reference.totalMean,
      8,
    );
  });

  it("records the same number of compliance decisions", () => {
    const decisions = services.filter(
      (s) => str(s, config.COMPLIANCE_DECISION_TYPE) !== null,
    );
    expect(decisions.length).toBe(reference.decisionCount);
  });
});

describe("benchmarks", () => {
  it("matches Python percentiles", () => {
    const stars = column(services, "Overall Star Rating");
    expect(quantile(stars, 0.5)).toBeCloseTo(reference.starMedian, 10);
    expect(quantile(stars, 0.9)).toBeCloseTo(reference.starP90, 10);
    expect(quantile(column(services, config.RN_COMPLIANCE), 0.75)).toBeCloseTo(
      reference.rnP75,
      8,
    );
  });

  it("produces a benchmark row per quality measure", () => {
    const benchmarks = computeBenchmarks(services, config.QUALITY_MEASURES);
    expect(benchmarks.map((b) => b.measure)).toEqual([...config.QUALITY_MEASURES]);
    for (const benchmark of benchmarks) {
      expect(benchmark.median).not.toBeNull();
    }
  });
});

describe("quality measure summaries", () => {
  it("matches Python means and standard errors", () => {
    const summaries = summariseMeasures(services);
    expect(summaries.length).toBe(config.QM_FIELDS.length);

    for (const summary of summaries) {
      expect(summary.mean).toBeCloseTo(reference.qmMeans[summary.field]!, 8);
      expect(summary.sem!).toBeCloseTo(reference.qmSem[summary.field]!, 8);
    }
  });
});

describe("outlier screening", () => {
  const report = findOutliers(services);

  it("screens every configured metric", () => {
    expect(report.skipped).toEqual([]);
    expect(new Set(report.screened)).toEqual(new Set(Object.keys(config.ANOMALY_METRICS)));
  });

  it("finds the same total as Python", () => {
    expect(report.outliers.length).toBe(reference.outlierCount);
  });

  it("finds the same breakdown per metric", () => {
    const byMetric: Record<string, number> = {};
    for (const outlier of report.outliers) {
      byMetric[outlier.metric] = (byMetric[outlier.metric] ?? 0) + 1;
    }
    expect(byMetric).toEqual(reference.outliersByMetric);
  });

  it("includes both care-compliance metrics", () => {
    // The regression this rewrite inherited a fix for: these were silently
    // dropped when the columns came out as object dtype in pandas.
    const metrics = new Set(report.outliers.map((o) => o.metric));
    expect(metrics.has(config.RN_COMPLIANCE)).toBe(true);
    expect(metrics.has(config.TOTAL_COMPLIANCE)).toBe(true);
  });
});

describe("concern flags", () => {
  it("flags the same number of services as Python", () => {
    expect(flagConcerns(services).length).toBe(reference.concernCount);
  });
});
