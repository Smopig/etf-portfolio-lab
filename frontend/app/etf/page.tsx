"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import DataTable, { Column } from "@/components/tables/DataTable";
import { listEtfs } from "@/lib/api";
import { formatCurrencyTWD, formatPercent } from "@/lib/format";
import type { EtfListItem } from "@/lib/types";

const COLUMNS: Column[] = [
  { key: "symbol", label: "代號", sortable: true },
  { key: "name", label: "名稱", sortable: true },
  { key: "issuer", label: "發行商", sortable: true },
  { key: "management_type", label: "管理類型", sortable: true },
  { key: "asset_class", label: "資產類別", sortable: true },
  {
    key: "latest_close",
    label: "最新價",
    sortable: true,
    align: "right",
    render: (value) =>
      value === null || value === undefined ? "—" : formatCurrencyTWD(Number(value)),
  },
  {
    key: "change_pct",
    label: "漲跌幅",
    sortable: true,
    align: "right",
    render: (value) => {
      if (value === null || value === undefined) return "—";
      const num = Number(value);
      const color = num > 0 ? "#e23b3b" : num < 0 ? "#18a058" : undefined;
      return (
        <span style={{ color }} className={color ? undefined : "text-text-muted"}>
          {formatPercent(num, { decimals: 2 })}
        </span>
      );
    },
  },
  { key: "has_holdings", label: "成分股資料", sortable: true },
  { key: "has_price_data", label: "價格資料", sortable: true },
];

export default function EtfListPage() {
  const router = useRouter();
  const [etfs, setEtfs] = useState<EtfListItem[]>([]);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [err, setErr] = useState<{ code: string; message: string } | null>(null);

  function load() {
    setState("loading");
    listEtfs()
      .then((data) => {
        setEtfs(data);
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

  const rows = etfs.map((e) => ({
    ...e,
    management_type: e.management_type ?? "—",
    asset_class: e.asset_class ?? "—",
    has_holdings: e.has_holdings ? "✓" : "✗",
    has_price_data: e.has_price_data ? "✓" : "✗",
    __symbol: e.symbol,
  }));

  return (
    <div>
      <PageHeader title="ETF 明細" subtitle="瀏覽所有已匯入的 ETF，點選代號可查看詳細研究頁面。" />

      {state === "loading" && <LoadingSkeleton variant="table" />}

      {state === "error" && <ErrorState code={err?.code} message={err?.message} retry={load} />}

      {state === "ok" && (
        <DataTable
          columns={COLUMNS}
          rows={rows}
          searchable
          onRowClick={(row) => router.push(`/etf/${encodeURIComponent(String(row.symbol))}`)}
          emptyState={{
            title: "尚無 ETF 資料",
            description: "系統中目前沒有已匯入的 ETF，請至資料來源頁查看匯入狀態。",
            actionLabel: "前往資料來源",
            actionHref: "/data-sources",
          }}
        />
      )}

      {state === "ok" && rows.length > 0 && (
        <div className="mt-space-2 text-small text-text-muted">點選任一列以查看該 ETF 詳細資訊。</div>
      )}
    </div>
  );
}
