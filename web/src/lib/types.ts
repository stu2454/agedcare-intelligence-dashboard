/** Shared row/value types and safe accessors. */

export type Cell = string | number | Date | null;

/**
 * One service (one row of the 'Detailed data' sheet).
 *
 * A record rather than a fixed interface because the extract carries ~78
 * columns, including a variable set of `[RE]` response columns that differ
 * between quarters. Use the accessors below rather than indexing directly.
 */
export type Service = Record<string, Cell>;

/** Numeric value for a column, or null when absent or non-numeric. */
export function num(service: Service, column: string): number | null {
  const value = service[column];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** String value for a column, or null when absent. */
export function str(service: Service, column: string): string | null {
  const value = service[column];
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return null;
}

/** Date value for a column, or null when absent or unparsable. */
export function date(service: Service, column: string): Date | null {
  const value = service[column];
  return value instanceof Date && !Number.isNaN(value.getTime()) ? value : null;
}

/** Every numeric value present for a column across the given services. */
export function column(services: Service[], name: string): number[] {
  const values: number[] = [];
  for (const service of services) {
    const value = num(service, name);
    if (value !== null) values.push(value);
  }
  return values;
}

/** Distinct non-empty string values for a column, sorted. */
export function distinct(services: Service[], name: string): string[] {
  const seen = new Set<string>();
  for (const service of services) {
    const value = str(service, name);
    if (value !== null && value !== "") seen.add(value);
  }
  return [...seen].sort((a, b) => a.localeCompare(b));
}

export class DataLoadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DataLoadError";
  }
}
