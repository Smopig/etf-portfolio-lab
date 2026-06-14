"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import SourceFooter from "@/components/common/SourceFooter";
import Badge, { BadgeTone } from "@/components/common/Badge";
import { EmptyState, ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import DataTable, { Column } from "@/components/tables/DataTable";
import { getDividendRankingWithMeta } from "@/lib/api";
import { formatNumber, formatPercent, formatDate } from "@/lib/format";
import type { DividendRankingRow, DividendRankingMeta } from "@/lib/types";

const FREQUENCY_OPTIONS = ["全部", "月配", "季配", "半年配", "年配"] as const;

function frequencyTone(freq: string | null | undefined): BadgeTone {
  switch (freq) {
    case "月配":
      return "info";
    case "季配":
      return "success";
    case "半年配":
      return "warning";
    case "年配":
      return "neutral";
    default:
      return "neutral";
  }
}

const COLUMNS: Column[] = [
  {
    key: "etf_symbol",
    label: "ETF 代號",
    sortable: true,
    render: (value) => (
      <a
        href={`/etf/${encodeURIComponent(String(value))}`}
        onClick={(e) => e.stopPropagation()}
        className="text-accent-primary hover:underline"
      >
        {String(value)}
      </a>
    ),
  },
  { key: "name", label: "名稱", sortable: true },
  {
    key: "frequency",
    label: "配息週期",
    render: (value) =>
      value ? <Badge label={String(value)} tone={frequencyTone(String(value))} /> : "—",
  },
  {
    key: "latest_dividend",
    label: "最近配息",
    sortable: true,
    align: "right",
    render: (value) =>
      value === null || value === undefined ? "—" : formatNumber(Number(value), { decimals: 3 }),
  },
  {
    key: "ttm_yield_pct",
    label: "TTM 年殖利率",
    sortable: true,
    align: "right",
    render: (value) =>
      value === null || value === undefined ? "—" : formatPercent(Number(value), { decimals: 2 }),
  },
  {
    key: "payout_per_100k",
    label: "投 10 萬能領",
    sortable: true,
    align: "right",
    render: (value) =>
      value === null || value === undefined
        ? "—"
        : `${formatNumber(Number(value), { decimals: 0 })} 元`,
  },
  {
    key: "latest_ex_date",
    label: "資料日期",
    sortable: true,
    align: "right",
    render: (value) => formatDate(value as string | null),
  },
];

export default function DividendsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<DividendRankingRow[]>([]);
  const [meta, setMeta] = useState<DividendRankingMeta | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [err, setErr] = useState<{ code: string; message: string } | null>(null);

  const [frequency, setFrequency] = useState<(typeof FREQUENCY_OPTIONS)[number]>("全部");
  const [search, setSearch] = useState("");

  function load() {
    setState("loading");
    // Default sort is TTM yield desc — request order=desc so the API also
    // returns yield-descending; client sorting via DataTable mirrors this.
    getDividendRankingWithMeta({ order: "desc" })
      .then(({ rows, meta }) => {
        setRows(rows);
        setMeta(meta);
        setState("ok");
      })
      .catch((e: unknown) => {
        setErr(errorToFriendlyMessage(e));
        setState("error");
      });
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    let result = [...rows];
    if (frequency !== "全部") {
      result = result.filter((r) => r.frequency === frequency);
    }
    const q = search.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (r) =>
          r.etf_symbol.toLowerCase().includes(q) ||
          (r.name ?? "").toLowerCase().includes(q)
      );
    }
    // Default ordering: TTM yield desc, nulls last.
    result.sort((a, b) => {
      const av = a.ttm_yield_pct;
      const bv = b.ttm_yield_pct;
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return bv - av;
    });
    return result;
  }, [rows, frequency, search]);

  const sourceName = useMemo(() => {
    const first = rows.find((r) => r.source_name)?.source_name;
    return first ?? "Yahoo奇摩股市";
  }, [rows]);

  const priceDate = useMemo(() => rows.find((r) => r.price_date)?.price_date ?? null, [rows]);

  return (
    <div>
      <PageHeader
        title="配息排行"
        subtitle="全 ETF 依近 12 個月 (TTM) 殖利率排行"
      />

      {/* §7 disclosure — TTM explanation, shown prominently above the table. */}
      {meta?.disclosure && (
        <div className="mb-space-4 rounded-md border border-status-warning/30 bg-status-warning/5 p-space-3 text-small text-text-secondary">
          {meta.disclosure}
        </div>
      )}

      {state === "loading" && <LoadingSkeleton variant="table" />}

      {state === "error" && <ErrorState code={err?.code} message={err?.message} retry={load} />}

      {state === "ok" && rows.length === 0 && (
        <EmptyState
          title="尚無配息資料，請先到『資料來源』頁更新"
          description="系統中目前沒有任何 ETF 的配息資料。"
          actionLabel="前往資料來源"
          actionHref="/data-sources"
        />
      )}

      {state === "ok" && rows.length > 0 && (
        <>
          {/* Controls row — wraps on mobile. */}
          <div className="mb-space-3 flex flex-wrap items-center gap-space-2">
            <div className="flex flex-wrap items-center gap-space-1">
              {FREQUENCY_OPTIONS.map((opt) => {
                const active = frequency === opt;
                return (
                  <button
                    key={opt}
                    onClick={() => setFrequency(opt)}
                    className={`rounded-sm px-space-3 py-1 text-body transition-colors ${
                      active
                        ? "bg-accent-primary/10 text-accent-primary"
                        : "border border-border-subtle text-text-secondary hover:bg-bg-surface-raised"
                    }`}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜尋代號或名稱..."
              className="ml-auto rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary placeholder:text-text-muted focus:border-accent-primary focus:outline-none"
            />
          </div>

          <DataTable
            columns={COLUMNS}
            rows={filtered}
            exportCsv
            dataDate={priceDate}
            onRowClick={(row) =>
              router.push(`/etf/${encodeURIComponent(String(row.etf_symbol))}`)
            }
            emptyState={{
              title: "沒有符合條件的 ETF",
              description: "請調整週期篩選或搜尋關鍵字。",
            }}
          />

          <SourceFooter
            sourceName={sourceName}
            dataDate={priceDate}
            disclaimer="殖利率為近 12 個月 (TTM) 累計配息除以最新收盤價，配息不代表未來績效，亦不構成投資建議。"
          />
        </>
      )}
    </div>
  );
}
