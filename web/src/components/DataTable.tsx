/** Sortable table with an optional CSV export. */

import { useMemo, useState, type ReactNode } from "react";

import { TableScroll } from "./ui";

export interface Column<Row> {
  key: string;
  header: string;
  /** Rendered cell content. */
  render: (row: Row) => ReactNode;
  /** Sort key and CSV value. Omit to make the column unsortable. */
  value?: (row: Row) => string | number | null;
  numeric?: boolean;
  /** Extra class for the cell, e.g. to highlight a breached threshold. */
  cellClass?: (row: Row) => string | undefined;
}

interface DataTableProps<Row> {
  rows: Row[];
  columns: Column<Row>[];
  /** Column key to sort by initially. */
  initialSort?: { key: string; direction: "asc" | "desc" };
  emptyMessage?: string;
  /** Filename (without extension) enables a CSV download button. */
  csvName?: string;
  maxRows?: number;
}

function toCsv<Row>(rows: Row[], columns: Column<Row>[]): string {
  const escape = (value: string | number | null) => {
    const text = value === null ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };

  const header = columns.map((c) => escape(c.header)).join(",");
  const body = rows
    .map((row) =>
      columns.map((c) => escape(c.value ? c.value(row) : null)).join(","),
    )
    .join("\n");
  return `${header}\n${body}`;
}

export function DataTable<Row>({
  rows,
  columns,
  initialSort,
  emptyMessage = "No rows to display.",
  csvName,
  maxRows,
}: DataTableProps<Row>) {
  const [sort, setSort] = useState(initialSort ?? null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const column = columns.find((c) => c.key === sort.key);
    if (!column?.value) return rows;

    const direction = sort.direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = column.value!(a);
      const vb = column.value!(b);
      // Missing values always sort last, regardless of direction.
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * direction;
      }
      return String(va).localeCompare(String(vb)) * direction;
    });
  }, [rows, columns, sort]);

  const visible = maxRows ? sorted.slice(0, maxRows) : sorted;

  if (rows.length === 0) {
    return <div className="empty-state">{emptyMessage}</div>;
  }

  const toggleSort = (key: string) => {
    setSort((current) =>
      current?.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "asc" },
    );
  };

  const download = () => {
    const blob = new Blob([toCsv(sorted, columns)], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${csvName}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <TableScroll>
        <table>
          <thead>
            <tr>
              {columns.map((column) => {
                const active = sort?.key === column.key;
                return (
                  <th
                    key={column.key}
                    className={column.numeric ? "numeric" : undefined}
                    aria-sort={
                      active
                        ? sort.direction === "asc"
                          ? "ascending"
                          : "descending"
                        : undefined
                    }
                  >
                    {column.value ? (
                      <button
                        type="button"
                        className="button"
                        style={{
                          all: "unset",
                          cursor: "pointer",
                          fontWeight: "inherit",
                        }}
                        onClick={() => toggleSort(column.key)}
                      >
                        {column.header}
                        {active ? (sort.direction === "asc" ? " ▲" : " ▼") : ""}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={
                      [column.numeric ? "numeric" : "", column.cellClass?.(row) ?? ""]
                        .filter(Boolean)
                        .join(" ") || undefined
                    }
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableScroll>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          {maxRows && sorted.length > maxRows
            ? `Showing ${visible.length} of ${sorted.length} rows`
            : `${sorted.length} row${sorted.length === 1 ? "" : "s"}`}
        </span>
        {csvName && (
          <button type="button" className="button" onClick={download}>
            Download CSV
          </button>
        )}
      </div>
    </>
  );
}
