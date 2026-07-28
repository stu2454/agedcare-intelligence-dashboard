/** Extract loading, filter state, and the derived views every tab consumes. */

import { useCallback, useEffect, useMemo, useState } from "react";

import { loadDefaultExtract, readExtract, type Extract } from "../lib/parse";
import { DataLoadError, distinct, str, type Service } from "../lib/types";

export const ALL = "All";

export interface Filters {
  state: string;
  sizes: string[];
  mmms: string[];
  provider: string;
}

export interface Dashboard {
  status: "loading" | "ready" | "error";
  error: string | null;
  /** Where the current data came from, for the sidebar message. */
  sourceLabel: string | null;

  columns: string[];
  filters: Filters;
  setFilters: (update: Partial<Filters>) => void;
  resetFilters: () => void;

  /** Options for each filter control. */
  states: string[];
  sizes: string[];
  mmms: string[];
  providers: string[];

  /** Services matching the state/size/MMM filters — the benchmark peer group. */
  sector: Service[];
  /** `sector` narrowed to the selected provider, or all of `sector`. */
  provider: Service[];
  hasProvider: boolean;
  /** Human-readable summary of the active sector filters. */
  filterDescription: string;

  uploadFile: (file: File) => Promise<void>;
  useDefaultExtract: () => void;
}

/** MMM codes are numeric-looking strings; sort them numerically when possible. */
function sortMmm(values: string[]): string[] {
  return [...values].sort((a, b) => {
    const na = Number(a);
    const nb = Number(b);
    if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    return a.localeCompare(b);
  });
}

const NO_FILTERS: Filters = { state: ALL, sizes: [], mmms: [], provider: ALL };

export function useDashboard(): Dashboard {
  const [extract, setExtract] = useState<Extract | null>(null);
  const [status, setStatus] = useState<Dashboard["status"]>("loading");
  const [error, setError] = useState<string | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);
  const [filters, setFiltersState] = useState<Filters>(NO_FILTERS);

  const applyExtract = useCallback((loaded: Extract, label: string) => {
    setExtract(loaded);
    setSourceLabel(label);
    setStatus("ready");
    setError(null);
    // A new workbook invalidates every selection.
    setFiltersState({
      state: ALL,
      sizes: distinct(loaded.services, "Size"),
      mmms: sortMmm(distinct(loaded.services, "MMM Code")),
      provider: ALL,
    });
  }, []);

  const loadDefault = useCallback(() => {
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    loadDefaultExtract(controller.signal)
      .then((loaded) => applyExtract(loaded, "Default extract loaded"))
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setStatus("error");
        setError(
          cause instanceof DataLoadError || cause instanceof Error
            ? cause.message
            : "Could not load the bundled extract.",
        );
      });
    return () => controller.abort();
  }, [applyExtract]);

  useEffect(() => loadDefault(), [loadDefault]);

  const uploadFile = useCallback(
    async (file: File) => {
      setStatus("loading");
      setError(null);
      try {
        // Parsed in this tab; the file is never uploaded anywhere.
        const loaded = readExtract(await file.arrayBuffer());
        applyExtract(loaded, `Loaded ${file.name}`);
      } catch (cause) {
        setStatus("error");
        setError(
          cause instanceof DataLoadError || cause instanceof Error
            ? cause.message
            : "Could not read that file.",
        );
      }
    },
    [applyExtract],
  );

  const services = extract?.services ?? [];

  const states = useMemo(() => distinct(services, "State/Territory"), [services]);
  const allSizes = useMemo(() => distinct(services, "Size"), [services]);
  const allMmms = useMemo(() => sortMmm(distinct(services, "MMM Code")), [services]);

  const sector = useMemo(() => {
    const sizes = new Set(filters.sizes);
    const mmms = new Set(filters.mmms);
    return services.filter((service) => {
      if (filters.state !== ALL && str(service, "State/Territory") !== filters.state) {
        return false;
      }
      if (sizes.size > 0 && !sizes.has(str(service, "Size") ?? "")) return false;
      if (mmms.size > 0 && !mmms.has(str(service, "MMM Code") ?? "")) return false;
      return true;
    });
  }, [services, filters.state, filters.sizes, filters.mmms]);

  const providers = useMemo(() => distinct(sector, "Provider Name"), [sector]);

  const providerServices = useMemo(() => {
    if (filters.provider === ALL) return sector;
    return sector.filter((s) => str(s, "Provider Name") === filters.provider);
  }, [sector, filters.provider]);

  const filterDescription = useMemo(() => {
    const parts = [filters.state];
    if (filters.sizes.length > 0 && filters.sizes.length < allSizes.length) {
      parts.push(`Sizes: ${filters.sizes.join(", ")}`);
    }
    if (filters.mmms.length > 0 && filters.mmms.length < allMmms.length) {
      parts.push(`MMMs: ${filters.mmms.join(", ")}`);
    }
    return parts.join(" / ");
  }, [filters.state, filters.sizes, filters.mmms, allSizes.length, allMmms.length]);

  const setFilters = useCallback((update: Partial<Filters>) => {
    setFiltersState((current) => {
      const next = { ...current, ...update };
      // A provider that no longer exists under the new sector filters would
      // leave the provider tabs stranded on an empty selection.
      if (update.provider === undefined && next.provider !== ALL) {
        const stillListed =
          update.state === undefined &&
          update.sizes === undefined &&
          update.mmms === undefined;
        if (!stillListed) next.provider = ALL;
      }
      return next;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({
      state: ALL,
      sizes: allSizes,
      mmms: allMmms,
      provider: ALL,
    });
  }, [allSizes, allMmms]);

  return {
    status,
    error,
    sourceLabel,
    columns: extract?.columns ?? [],
    filters,
    setFilters,
    resetFilters,
    states,
    sizes: allSizes,
    mmms: allMmms,
    providers,
    sector,
    provider: providerServices,
    hasProvider: filters.provider !== ALL,
    filterDescription,
    uploadFile,
    useDefaultExtract: loadDefault,
  };
}
