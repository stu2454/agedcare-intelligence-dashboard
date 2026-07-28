import { describe, expect, it } from "vitest";

import {
  iqrBounds,
  mean,
  median,
  percentileOfScore,
  quantile,
  sem,
  stdDev,
  valueCounts,
} from "../src/lib/stats";

describe("quantile", () => {
  it("matches numpy's linear interpolation", () => {
    const values = [1, 2, 3, 4];
    // numpy.quantile([1,2,3,4], 0.25) == 1.75
    expect(quantile(values, 0.25)).toBeCloseTo(1.75, 10);
    expect(quantile(values, 0.5)).toBeCloseTo(2.5, 10);
    expect(quantile(values, 0.75)).toBeCloseTo(3.25, 10);
  });

  it("handles unsorted input", () => {
    expect(quantile([4, 1, 3, 2], 0.5)).toBeCloseTo(2.5, 10);
  });

  it("returns the single value for a one-element sample", () => {
    expect(quantile([7], 0.9)).toBe(7);
  });

  it("returns null for an empty sample", () => {
    expect(quantile([], 0.5)).toBeNull();
  });
});

describe("median / mean", () => {
  it("computes the median of an odd-length sample", () => {
    expect(median([3, 1, 2])).toBe(2);
  });

  it("returns null for empty input", () => {
    expect(mean([])).toBeNull();
    expect(median([])).toBeNull();
  });
});

describe("stdDev / sem", () => {
  it("uses the sample standard deviation (ddof=1)", () => {
    // pandas Series([1,2,3,4]).std() == 1.2909944487358056
    expect(stdDev([1, 2, 3, 4])).toBeCloseTo(1.2909944487358056, 10);
  });

  it("matches pandas sem()", () => {
    // pandas Series([1,2,3,4]).sem() == 0.6454972243679028
    expect(sem([1, 2, 3, 4])).toBeCloseTo(0.6454972243679028, 10);
  });

  it("returns null when there is fewer than one degree of freedom", () => {
    expect(stdDev([5])).toBeNull();
    expect(sem([5])).toBeNull();
  });
});

describe("percentileOfScore", () => {
  it("matches scipy's kind='weak'", () => {
    const distribution = [1, 2, 3, 4, 5];
    expect(percentileOfScore(distribution, 3)).toBeCloseTo(60, 10);
    expect(percentileOfScore(distribution, 5)).toBeCloseTo(100, 10);
    expect(percentileOfScore(distribution, 0)).toBeCloseTo(0, 10);
  });

  it("returns null for an empty distribution", () => {
    expect(percentileOfScore([], 1)).toBeNull();
  });
});

describe("iqrBounds", () => {
  it("computes Tukey fences at 1.5x IQR", () => {
    const bounds = iqrBounds([1, 2, 3, 4, 5])!;
    expect(bounds.q1).toBeCloseTo(2, 10);
    expect(bounds.q3).toBeCloseTo(4, 10);
    expect(bounds.lower).toBeCloseTo(-1, 10);
    expect(bounds.upper).toBeCloseTo(7, 10);
  });
});

describe("valueCounts", () => {
  it("orders by descending count", () => {
    expect(valueCounts(["a", "b", "a", "c", "a", "b"])).toEqual([
      ["a", 3],
      ["b", 2],
      ["c", 1],
    ]);
  });
});
