/**
 * Reads and prepares a Star Ratings quarterly extract, entirely in the browser.
 *
 * The bundled default file and user uploads go through this exact same path,
 * so there is no second implementation to drift out of sync. Nothing is sent
 * to a server — uploaded provider data never leaves the machine.
 */

import { read, utils } from "@e965/xlsx";

import * as config from "./config";
import { DataLoadError, type Cell, type Service } from "./types";

/**
 * Coerce a cell to a number, stripping percent signs and thousands separators.
 * Returns null for blanks and anything non-numeric.
 *
 * The Python version originally gated this on `dtype == 'object'`, which under
 * pandas 3 stopped matching string columns and silently turned percent-
 * formatted values into NaN. Coercing unconditionally avoids that class of bug.
 */
export function toNumber(value: Cell | undefined): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (value instanceof Date) return null;

  const cleaned = value.replace(/%/g, "").replace(/,/g, "").trim();
  if (cleaned === "" || cleaned === "-" || cleaned === "n/a") return null;

  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Parse the extract's day-first dates (e.g. `26/5/2023`).
 *
 * SheetJS may hand back a Date already when the cell is a real Excel date;
 * otherwise the value is a day-first string, which `new Date()` would misread
 * as month-first.
 */
export function toDate(value: Cell | undefined): Date | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value !== "string") return null;

  const match = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return null;

  const [, day, month, year] = match;
  const parsed = new Date(Number(year), Number(month) - 1, Number(day));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Percentage ratio of actual to target care minutes.
 *
 * A zero or missing target yields null rather than Infinity. In the Python
 * version this was built with `pd.NA`, which forced the column to object dtype
 * and silently excluded it from every numeric-gated analysis.
 */
export function ratioPercent(actual: number | null, target: number | null): number | null {
  if (actual === null || target === null || target === 0) return null;
  const ratio = (actual / target) * 100;
  return Number.isFinite(ratio) ? ratio : null;
}

/** The `[RE]` columns that carry a response frequency. */
export function residentsExperienceColumns(columns: string[]): string[] {
  return columns.filter(
    (name) =>
      name.startsWith("[RE]") &&
      config.RE_FREQUENCY_ORDER.some((freq) => name.includes(freq)),
  );
}

/** Split "[RE] Respect - Always" into its category and frequency parts. */
export function parseReColumn(
  name: string,
): { category: string; frequency: string } | null {
  const match = name.match(
    /^\[RE\]\s+(.*?)\s+-\s+(Always|Most of the time|Some of the time|Never)$/,
  );
  if (!match) return null;
  return { category: match[1]!, frequency: match[2]! };
}

/** Clean and enrich raw rows from the 'Detailed data' sheet. */
export function prepareServices(rows: Record<string, Cell>[]): Service[] {
  const columns = rows.length > 0 ? Object.keys(rows[0]!) : [];
  const numericColumns = new Set<string>([
    ...config.STAFFING_COLUMNS,
    ...config.RATING_COLUMNS,
    ...config.QM_FIELDS,
    ...residentsExperienceColumns(columns),
  ]);
  const categorical = new Set<string>(config.CATEGORICAL_COLUMNS);

  return rows.map((row) => {
    const service: Service = {};

    for (const [key, value] of Object.entries(row)) {
      if (categorical.has(key)) {
        const text = value === null || value === undefined ? "" : String(value).trim();
        service[key] = text === "" ? "Unknown" : text;
      } else if (numericColumns.has(key)) {
        service[key] = toNumber(value);
      } else if (
        key === config.COMPLIANCE_DATE_APPLIED ||
        key === config.COMPLIANCE_DATE_ENDS
      ) {
        service[key] = toDate(value);
      } else {
        service[key] = value === undefined || value === "" ? null : value;
      }
    }

    service[config.RN_COMPLIANCE] = ratioPercent(
      toNumber(row["[S] Registered Nurse Care Minutes - Actual"]),
      toNumber(row["[S] Registered Nurse Care Minutes - Target"]),
    );
    service[config.TOTAL_COMPLIANCE] = ratioPercent(
      toNumber(row["[S] Total Care Minutes - Actual"]),
      toNumber(row["[S] Total Care Minutes - Target"]),
    );

    return service;
  });
}

export interface Extract {
  services: Service[];
  /** Every column name present in the source sheet, in order. */
  columns: string[];
}

/** Read an .xlsx buffer into prepared services. Throws {@link DataLoadError}. */
export function readExtract(buffer: ArrayBuffer): Extract {
  let workbook;
  try {
    workbook = read(buffer, { cellDates: true });
  } catch (error) {
    throw new DataLoadError(
      `Could not read the Excel file: ${error instanceof Error ? error.message : error}`,
    );
  }

  const sheet = workbook.Sheets[config.DETAILED_SHEET];
  if (!sheet) {
    throw new DataLoadError(
      `The workbook is missing the required '${config.DETAILED_SHEET}' sheet.`,
    );
  }

  const rows = utils.sheet_to_json<Record<string, Cell>>(sheet, {
    defval: null,
    raw: true,
  });
  if (rows.length === 0) {
    throw new DataLoadError(`The '${config.DETAILED_SHEET}' sheet is empty.`);
  }

  const columns = Object.keys(rows[0]!);
  const missing = config.REQUIRED_COLUMNS.filter((name) => !columns.includes(name));
  if (missing.length > 0) {
    throw new DataLoadError(
      `The '${config.DETAILED_SHEET}' sheet is missing essential columns: ${missing.join(", ")}`,
    );
  }

  return { services: prepareServices(rows), columns };
}

/** Fetch and parse the extract bundled with the deployment. */
export async function loadDefaultExtract(signal?: AbortSignal): Promise<Extract> {
  const url = `${import.meta.env.BASE_URL}${config.DEFAULT_DATA_FILENAME}`;
  const response = await fetch(url, signal ? { signal } : {});
  if (!response.ok) {
    throw new DataLoadError(
      `Could not download the bundled extract (HTTP ${response.status}).`,
    );
  }
  return readExtract(await response.arrayBuffer());
}
