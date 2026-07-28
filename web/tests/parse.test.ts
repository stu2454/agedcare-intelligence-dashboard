import { describe, expect, it } from "vitest";

import * as config from "../src/lib/config";
import {
  parseReColumn,
  prepareServices,
  ratioPercent,
  residentsExperienceColumns,
  toDate,
  toNumber,
} from "../src/lib/parse";
import { num, str, type Cell } from "../src/lib/types";

describe("toNumber", () => {
  it("passes through finite numbers", () => {
    expect(toNumber(42)).toBe(42);
    expect(toNumber(0)).toBe(0);
    expect(toNumber(-1.5)).toBe(-1.5);
  });

  it("strips percent signs and thousands separators", () => {
    expect(toNumber("70%")).toBe(70);
    expect(toNumber(" 12.5 % ")).toBe(12.5);
    expect(toNumber("1,234")).toBe(1234);
  });

  it("returns null for blanks and non-numeric text", () => {
    expect(toNumber(null)).toBeNull();
    expect(toNumber(undefined)).toBeNull();
    expect(toNumber("")).toBeNull();
    expect(toNumber("-")).toBeNull();
    expect(toNumber("Not applicable")).toBeNull();
  });

  it("returns null for non-finite numbers", () => {
    expect(toNumber(Number.POSITIVE_INFINITY)).toBeNull();
    expect(toNumber(Number.NaN)).toBeNull();
  });
});

describe("toDate", () => {
  it("parses day-first strings", () => {
    const parsed = toDate("26/5/2023")!;
    expect(parsed.getFullYear()).toBe(2023);
    expect(parsed.getMonth()).toBe(4); // May
    expect(parsed.getDate()).toBe(26);
  });

  it("does not misread day-first dates as month-first", () => {
    // 10/5/2024 is 10 May, not 5 October.
    const parsed = toDate("10/5/2024")!;
    expect(parsed.getMonth()).toBe(4);
    expect(parsed.getDate()).toBe(10);
  });

  it("passes through Date objects from the parser", () => {
    const source = new Date(2024, 0, 15);
    expect(toDate(source)).toBe(source);
  });

  it("returns null for blanks and unparsable values", () => {
    expect(toDate(null)).toBeNull();
    expect(toDate("")).toBeNull();
    expect(toDate("not a date")).toBeNull();
    expect(toDate("2024-05-10")).toBeNull();
  });
});

describe("ratioPercent", () => {
  it("computes a percentage", () => {
    expect(ratioPercent(40, 40)).toBe(100);
    expect(ratioPercent(50, 40)).toBe(125);
    expect(ratioPercent(45, 50)).toBe(90);
  });

  it("returns null rather than Infinity for a zero target", () => {
    expect(ratioPercent(30, 0)).toBeNull();
  });

  it("returns null when either side is missing", () => {
    expect(ratioPercent(null, 40)).toBeNull();
    expect(ratioPercent(40, null)).toBeNull();
  });
});

describe("residentsExperienceColumns / parseReColumn", () => {
  it("selects only [RE] columns carrying a frequency", () => {
    const columns = [
      "[RE] Respect - Always",
      "[RE] Respect - Never",
      "[RE] Some Other Field",
      "Service Name",
    ];
    expect(residentsExperienceColumns(columns)).toEqual([
      "[RE] Respect - Always",
      "[RE] Respect - Never",
    ]);
  });

  it("splits a column into category and frequency", () => {
    expect(parseReColumn("[RE] Follow Up - Most of the time")).toEqual({
      category: "Follow Up",
      frequency: "Most of the time",
    });
  });

  it("returns null for a non-matching column", () => {
    expect(parseReColumn("Service Name")).toBeNull();
  });
});

describe("prepareServices", () => {
  const rows: Record<string, Cell>[] = [
    {
      "Provider Name": "Alpha",
      "Service Name": "A1",
      "State/Territory": "NSW",
      Size: "Small",
      "MMM Code": "1",
      "Overall Star Rating": 4,
      "[S] Registered Nurse Care Minutes - Actual": 40,
      "[S] Registered Nurse Care Minutes - Target": 40,
      "[S] Total Care Minutes - Actual": 200,
      "[S] Total Care Minutes - Target": 200,
      "[RE] Respect - Always": "70%",
      "[C] Decision type": "Notice to Remedy (NTR)",
      "[C] Date Decision Applied": "10/5/2024",
      "[C] Date Decision Ends": null,
    },
    {
      "Provider Name": null,
      "Service Name": "A2",
      "State/Territory": "NSW",
      Size: null,
      "MMM Code": "2",
      "Overall Star Rating": 2,
      "[S] Registered Nurse Care Minutes - Actual": 30,
      // Zero target: must not produce Infinity.
      "[S] Registered Nurse Care Minutes - Target": 0,
      "[S] Total Care Minutes - Actual": 180,
      "[S] Total Care Minutes - Target": 200,
      "[RE] Respect - Always": "65%",
      "[C] Decision type": null,
      "[C] Date Decision Applied": null,
      "[C] Date Decision Ends": null,
    },
  ];

  const services = prepareServices(rows);

  it("derives both care-compliance percentages as numbers", () => {
    expect(num(services[0]!, config.RN_COMPLIANCE)).toBe(100);
    expect(num(services[0]!, config.TOTAL_COMPLIANCE)).toBe(100);
    expect(num(services[1]!, config.TOTAL_COMPLIANCE)).toBe(90);
  });

  it("yields null for a zero care-minutes target", () => {
    expect(services[1]![config.RN_COMPLIANCE]).toBeNull();
  });

  it("coerces percent-formatted text to numbers", () => {
    expect(num(services[0]!, "[RE] Respect - Always")).toBe(70);
  });

  it("fills blank categorical values with 'Unknown'", () => {
    expect(str(services[1]!, "Provider Name")).toBe("Unknown");
    expect(str(services[1]!, "Size")).toBe("Unknown");
  });

  it("parses compliance dates day-first", () => {
    const applied = services[0]![config.COMPLIANCE_DATE_APPLIED] as Date;
    expect(applied.getMonth()).toBe(4);
    expect(applied.getDate()).toBe(10);
    expect(services[1]![config.COMPLIANCE_DATE_APPLIED]).toBeNull();
  });

  it("does not mutate the input rows", () => {
    expect(rows[1]!["Provider Name"]).toBeNull();
  });
});
