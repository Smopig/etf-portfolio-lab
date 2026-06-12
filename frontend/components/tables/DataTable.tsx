"use client";

import { useMemo, useState } from "react";
import { EmptyState, LoadingSkeleton } from "@/components/common/States";
import {
  formatCurrencyTWD,
  formatDate,
  formatNumber,
  formatPercent,
} from "@/lib/format";

export type ColumnFormat = "text" | "number" | "percent" | "currency" | "date";

export interface Column {
  key: string;
  label: string;
  align?: "left" | "right" | "center";
  format?: ColumnFormat;
  sortable?: boolean;
  sticky?: boolean;
  /** decimals for number/percent formats */
  decimals?: number;
}

export interface DataTableFilter {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

export interface DataTableEmptyState {
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
}

export interface DataTableProps {
  columns: Column[];
  rows: Record<string, unknown>[];
  searchable?: boolean;
  filters?: DataTableFilter[];
  exportCsv?: boolean;
  emptyState?: DataTableEmptyState;
  loading?: boolean;
  dataDate?: string | null;
  title?: string;
}

function formatCell(value: unknown, column: Column): string {
  if (value === null || value === undefined) return "—";
  switch (column.format) {
    case "number":
      return formatNumber(value as number, { decimals: column.decimals });
    case "percent":
      return formatPercent(value as number, { decimals: column.decimals ?? 2 });
    case "currency":
      return formatCurrencyTWD(value as number, { decimals: column.decimals });
    case "date":
      return formatDate(value as string);
    default:
      return String(value);
  }
}

function exportToCsv(columns: Column[], rows: Record<string, unknown>[]) {
  const header = columns.map((c) => c.label).join(",");
  const lines = rows.map((row) =>
    columns
      .map((c) => {
        const raw = row[c.key];
        const cell = formatCell(raw, c).replace(/,/g, "");
        return `"${cell}"`;
      })
      .join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function DataTable({
  columns,
  rows,
  searchable,
  filters,
  exportCsv,
  emptyState,
  loading,
  dataDate,
  title,
}: DataTableProps) {
  const [search, setSearch] = useState("");
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({});
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = useMemo(() => {
    let result = rows;

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((row) =>
        columns.some((c) => String(row[c.key] ?? "").toLowerCase().includes(q))
      );
    }

    for (const [key, value] of Object.entries(activeFilters)) {
      if (!value) continue;
      result = result.filter((row) => String(row[key]) === value);
    }

    if (sortKey) {
      result = [...result].sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av === bv) return 0;
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      });
    }

    return result;
  }, [rows, search, activeFilters, sortKey, sortDir, columns]);

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  if (loading) {
    return <LoadingSkeleton variant="table" rows={5} />;
  }

  return (
    <div className="rounded-md border border-border-subtle bg-bg-surface">
      {(title || searchable || filters?.length || exportCsv || dataDate) && (
        <div className="flex flex-wrap items-center justify-between gap-space-2 border-b border-border-subtle p-space-3">
          <div className="flex items-center gap-space-2">
            {title && <h2 className="text-h2 text-text-primary">{title}</h2>}
            {dataDate && <span className="text-small text-text-muted">資料日期：{dataDate}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-space-2">
            {searchable && (
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜尋..."
                className="rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary placeholder:text-text-muted focus:border-accent-primary focus:outline-none"
              />
            )}
            {filters?.map((f) => (
              <select
                key={f.key}
                value={activeFilters[f.key] ?? ""}
                onChange={(e) =>
                  setActiveFilters((prev) => ({ ...prev, [f.key]: e.target.value }))
                }
                className="rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
              >
                <option value="">{f.label}：全部</option>
                {f.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ))}
            {exportCsv && (
              <button
                onClick={() => exportToCsv(columns, filtered)}
                className="rounded-sm border border-border-strong px-space-3 py-1 text-body text-text-primary hover:bg-bg-surface-raised"
              >
                匯出 CSV
              </button>
            )}
          </div>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="p-space-6">
          <EmptyState
            title={emptyState?.title ?? "沒有資料"}
            description={emptyState?.description}
            actionLabel={emptyState?.actionLabel}
            actionHref={emptyState?.actionHref}
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead className="bg-bg-inset text-small uppercase text-text-secondary">
              <tr>
                {columns.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => c.sortable && toggleSort(c.key)}
                    className={`sticky top-0 whitespace-nowrap px-space-3 py-space-2 text-${c.align ?? "left"} ${
                      c.sticky ? "left-0 z-10 bg-bg-inset" : ""
                    } ${c.sortable ? "cursor-pointer select-none" : ""}`}
                  >
                    {c.label}
                    {c.sortable && sortKey === c.key && (sortDir === "asc" ? " ▲" : " ▼")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr
                  key={i}
                  className="h-9 border-b border-border-subtle text-body text-text-primary hover:bg-bg-surface-raised"
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className={`whitespace-nowrap px-space-3 text-${c.align ?? "left"} ${
                        c.format === "number" || c.format === "percent" || c.format === "currency"
                          ? "font-mono-num"
                          : ""
                      } ${c.sticky ? "sticky left-0 z-10 bg-bg-surface font-mono-num" : ""}`}
                    >
                      {formatCell(row[c.key], c)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
