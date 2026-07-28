/** Data input, filters and theme controls. */

import { useId, useRef, useState } from "react";

import type { Dashboard } from "../state/useDashboard";
import { ALL } from "../state/useDashboard";
import { useTheme, type ThemeChoice } from "../state/useTheme";

function MultiChips({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const chosen = new Set(selected);
  const allSelected = options.length > 0 && selected.length === options.length;

  return (
    <div className="field">
      <div
        className="field-label"
        style={{ display: "flex", justifyContent: "space-between" }}
      >
        <span>{label}</span>
        <button
          type="button"
          style={{
            all: "unset",
            cursor: "pointer",
            color: "var(--primary)",
            fontSize: "0.72rem",
          }}
          onClick={() => onChange(allSelected ? [] : options)}
        >
          {allSelected ? "Clear" : "All"}
        </button>
      </div>
      <div className="checkbox-list">
        {options.map((option) => {
          const isSelected = chosen.has(option);
          return (
            <button
              key={option}
              type="button"
              className="chip"
              data-selected={isSelected}
              aria-pressed={isSelected}
              onClick={() =>
                onChange(
                  isSelected
                    ? selected.filter((v) => v !== option)
                    : [...selected, option],
                )
              }
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ThemeToggle() {
  const { choice, setTheme } = useTheme();
  const options: Array<[ThemeChoice, string]> = [
    ["light", "Light"],
    ["dark", "Dark"],
    ["system", "Auto"],
  ];
  return (
    <div className="field">
      <span className="field-label">Appearance</span>
      <div className="theme-toggle" role="group" aria-label="Colour theme">
        {options.map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={choice === value}
            onClick={() => setTheme(value)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Sidebar({ dashboard }: { dashboard: Dashboard }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const uploadId = useId();

  const handleFile = (file: File | undefined) => {
    if (file) void dashboard.uploadFile(file);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">Aged Care Sector Intelligence</div>

      <div className="field">
        <span className="field-label">1. Data input</span>
        <label
          htmlFor={uploadId}
          className="upload-zone"
          data-dragging={dragging}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            handleFile(event.dataTransfer.files[0]);
          }}
        >
          <strong>Drop a quarterly extract</strong>
          <br />
          or click to choose an .xlsx file
          <input
            id={uploadId}
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={(event) => handleFile(event.target.files?.[0])}
          />
        </label>
        <p className="privacy-note">
          <span aria-hidden="true">🔒</span>
          <span>
            Your file is read in this browser tab and never uploaded to a server.
          </span>
        </p>
        {dashboard.sourceLabel && (
          <p style={{ fontSize: "0.8rem", color: "var(--strength)", margin: 0 }}>
            {dashboard.sourceLabel}
          </p>
        )}
        <button
          type="button"
          className="button"
          onClick={dashboard.useDefaultExtract}
        >
          Reload bundled extract
        </button>
      </div>

      <div className="field">
        <span className="field-label">2. Filters</span>
        <label className="field">
          <span style={{ fontSize: "0.85rem" }}>State / Territory</span>
          <select
            value={dashboard.filters.state}
            onChange={(event) => dashboard.setFilters({ state: event.target.value })}
          >
            <option value={ALL}>All</option>
            {dashboard.states.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </select>
        </label>
      </div>

      <MultiChips
        label="Service size"
        options={dashboard.sizes}
        selected={dashboard.filters.sizes}
        onChange={(sizes) => dashboard.setFilters({ sizes })}
      />

      <MultiChips
        label="MMM code"
        options={dashboard.mmms}
        selected={dashboard.filters.mmms}
        onChange={(mmms) => dashboard.setFilters({ mmms })}
      />

      <label className="field">
        <span className="field-label">Provider</span>
        <select
          value={dashboard.filters.provider}
          onChange={(event) => dashboard.setFilters({ provider: event.target.value })}
        >
          <option value={ALL}>All providers</option>
          {dashboard.providers.map((provider) => (
            <option key={provider} value={provider}>
              {provider}
            </option>
          ))}
        </select>
        <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
          {dashboard.providers.length.toLocaleString()} providers match the current
          filters
        </span>
      </label>

      <button type="button" className="button" onClick={dashboard.resetFilters}>
        Reset filters
      </button>

      <ThemeToggle />
    </aside>
  );
}
