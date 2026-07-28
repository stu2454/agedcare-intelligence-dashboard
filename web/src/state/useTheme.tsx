/**
 * Light/dark theme, following the OS by default with a manual override.
 *
 * Shared through context so the charts and the toggle agree — ECharts needs to
 * re-read its colours when the theme flips.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "acid-theme";

function systemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function storedChoice(): ThemeChoice {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

interface ThemeContextValue {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setTheme: (next: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoice] = useState<ThemeChoice>(storedChoice);
  const [resolved, setResolved] = useState<ResolvedTheme>(() =>
    storedChoice() === "system" ? systemTheme() : (storedChoice() as ResolvedTheme),
  );

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const next: ResolvedTheme = choice === "system" ? systemTheme() : choice;
      setResolved(next);
      document.documentElement.dataset["theme"] = next;
    };
    apply();

    if (choice !== "system") return;
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [choice]);

  const setTheme = useCallback((next: ThemeChoice) => {
    localStorage.setItem(STORAGE_KEY, next);
    setChoice(next);
  }, []);

  const value = useMemo(
    () => ({ choice, resolved, setTheme }),
    [choice, resolved, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside a ThemeProvider");
  return context;
}

/** Palette shared between CSS and the charts. */
export interface ChartPalette {
  primary: string;
  concern: string;
  strength: string;
  axis: string;
  grid: string;
  text: string;
  muted: string;
  tooltipBg: string;
  series: string[];
  /**
   * Sequential ramp for ordered categories (e.g. Always → Never), where a
   * categorical palette would wrongly imply the levels are unrelated.
   */
  ordered: string[];
}

const LIGHT: ChartPalette = {
  primary: "#2563eb",
  concern: "#dc2626",
  strength: "#059669",
  axis: "#94a3b8",
  grid: "#e2e8f0",
  text: "#0f172a",
  muted: "#64748b",
  tooltipBg: "#ffffff",
  series: ["#2563eb", "#0891b2", "#7c3aed", "#d97706", "#059669", "#dc2626", "#db2777"],
  ordered: ["#1e40af", "#3b82f6", "#93c5fd", "#e0e7ff"],
};

const DARK: ChartPalette = {
  primary: "#60a5fa",
  concern: "#f87171",
  strength: "#34d399",
  axis: "#475569",
  grid: "#1e293b",
  text: "#e2e8f0",
  muted: "#94a3b8",
  tooltipBg: "#1e293b",
  series: ["#60a5fa", "#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#f87171", "#f472b6"],
  ordered: ["#1d4ed8", "#3b82f6", "#7dd3fc", "#cbd5e1"],
};

export function usePalette(): ChartPalette {
  const { resolved } = useTheme();
  return resolved === "dark" ? DARK : LIGHT;
}
