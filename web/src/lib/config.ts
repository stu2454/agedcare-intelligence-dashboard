/**
 * Column names, thresholds and display constants.
 *
 * The Star Ratings quarterly extract prefixes column names: `[QM]` quality
 * measures, `[RE]` residents' experience, `[S]` staffing, `[C]` compliance.
 */

export const DEFAULT_DATA_FILENAME =
  "star-ratings-quarterly-data-extract-february-2025.xlsx";

export const DETAILED_SHEET = "Detailed data";
export const STAR_RATINGS_SHEET = "Star Ratings";

export const REQUIRED_COLUMNS = [
  "Provider Name",
  "Service Name",
  "State/Territory",
] as const;

export const CATEGORICAL_COLUMNS = [
  "Size",
  "MMM Code",
  "State/Territory",
  "Provider Name",
] as const;

export const RATING_COLUMNS = [
  "Overall Star Rating",
  "Compliance rating",
  "Residents' Experience rating",
  "Staffing rating",
  "Quality Measures rating",
] as const;

export const STAFFING_COLUMNS = [
  "[S] Registered Nurse Care Minutes - Actual",
  "[S] Registered Nurse Care Minutes - Target",
  "[S] Total Care Minutes - Actual",
  "[S] Total Care Minutes - Target",
] as const;

export const QM_FIELDS = [
  "[QM] Pressure injuries*",
  "[QM] Restrictive practices",
  "[QM] Unplanned weight loss*",
  "[QM] Falls and major injury - falls*",
  "[QM] Falls and major injury - major injury from a fall*",
  "[QM] Medication management - polypharmacy",
  "[QM] Medication management - antipsychotic",
] as const;

/** Derived columns computed during parsing. */
export const RN_COMPLIANCE = "RN Care Compliance %";
export const TOTAL_COMPLIANCE = "Total Care Compliance %";

/** Measures compared against sector benchmarks in the Compare Providers tab. */
export const QUALITY_MEASURES = [
  "Overall Star Rating",
  RN_COMPLIANCE,
  TOTAL_COMPLIANCE,
] as const;

export const COMPLIANCE_DECISION_TYPE = "[C] Decision type";
export const COMPLIANCE_DATE_APPLIED = "[C] Date Decision Applied";
export const COMPLIANCE_DATE_ENDS = "[C] Date Decision Ends";

export const RE_FREQUENCY_ORDER = [
  "Always",
  "Most of the time",
  "Some of the time",
  "Never",
] as const;

export type ConcernDirection = "lower" | "higher";

/**
 * Absolute thresholds that flag a service as a serious concern.
 * Missing values never raise a flag.
 */
export const CONCERN_THRESHOLDS: Record<string, (value: number) => boolean> = {
  "Overall Star Rating": (v) => v <= 2,
  "Compliance rating": (v) => v === 1,
  "Residents' Experience rating": (v) => v <= 2,
  "Staffing rating": (v) => v <= 2,
  "Quality Measures rating": (v) => v <= 2,
};

/** Metrics screened for IQR outliers, and the direction indicating concern. */
export const ANOMALY_METRICS: Record<string, ConcernDirection> = {
  "Overall Star Rating": "lower",
  [RN_COMPLIANCE]: "lower",
  [TOTAL_COMPLIANCE]: "lower",
  "[QM] Pressure injuries*": "higher",
  "[QM] Restrictive practices": "higher",
  "[QM] Falls and major injury - falls*": "higher",
  "[QM] Medication management - antipsychotic": "higher",
};

/** Minimum sample sizes before a statistic is worth showing. */
export const MIN_SERVICES_FOR_BENCHMARK = 3;
export const MIN_SERVICES_FOR_OUTLIERS = 5;

export const RADAR_CONCERN_PERCENTILE = 80;
export const RADAR_STRENGTH_PERCENTILE = 20;

const QM_LABEL_REPLACEMENTS: Array<[string, string]> = [
  ["[QM] ", ""],
  ["Medication management - ", "Med Mgmt-"],
  ["Falls and major injury - ", ""],
  [" restrictive practices", " restraint"],
  [" pressure injuries", " pressure inj."],
];

/** Compact label for a quality-measure column, for cramped chart axes. */
export function shortenQmLabel(field: string): string {
  return QM_LABEL_REPLACEMENTS.reduce(
    (label, [from, to]) => label.replace(from, to),
    field,
  );
}
