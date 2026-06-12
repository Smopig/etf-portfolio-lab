"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";
import MetricCard from "@/components/common/MetricCard";
import SourceFooter from "@/components/common/SourceFooter";
import DataTable, { Column } from "@/components/tables/DataTable";
import { ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import { getDashboardSummary, rankEtfs, listDataQuality } from "@/lib/api";
import type { DashboardSummary, RankingItem, DataQualityCheck } from "@/lib/types";
import { formatDate, formatPercent, formatInteger, formatNumber } from "@/lib/format";

interface RankingCardConfig {
  title: string;
  explanation: string;
  fetcher: () => Promise<RankingItem[]>;
  formatValue: (item: RankingItem) => string;
}

const RANKING_CARDS: RankingCardConfig[] = [
  {
    title: "半導體曝險最高 ETF",
    explanation: "依「半導體」產業（level 1）持股權重排序，數字越高代表該 ETF 越集中投資半導體相關個股。",
    fetcher: () => rankEtfs({ metric: "industry_exposure", industry: "半導體", level: 1, limit: 1 }),
    formatValue: (item) => formatPercent(item.value, { decimals: 2, isFraction: item.value <= 1 }),
  },
  {
    title: "金融曝險最高 ETF",
    explanation: "依「金融」產業（level 1）持股權重排序，數字越高代表該 ETF 越集中投資金融相關個股。",
    fetcher: () => rankEtfs({ metric: "industry_exposure", industry: "金融", level: 1, limit: 1 }),
    formatValue: (item) => formatPercent(item.value, { decimals: 2, isFraction: item.value <= 1 }),
  },
  {
    title: "成分股最集中 ETF",
    explanation: "依 HHI（持股集中度指標）由高到低排序，數字越高代表該 ETF 持股越集中於少數標的。",
    fetcher: () => rankEtfs({ metric: "hhi", order: "desc", limit: 1 }),
    formatValue: (item) => formatNumber(item.value, { decimals: 4 }),
  },
  {
    title: "產業最分散 ETF",
    explanation: "依產業分散程度由低到高排序（數值越低代表產業分布越分散）。",
    fetcher: () => rankEtfs({ metric: "industry_diversification", order: "asc", limit: 1 }),
    formatValue: (item) => formatNumber(item.value, { decimals: 4 }),
  },
];

function RankingCard({ config }: { config: RankingCardConfig }) {
  const [state, setState] = useState<"loading" | "ok" | "empty" | "error">("loading");
  const [item, setItem] = useState<RankingItem | null>(null);
  const [err, setErr] = useState<{ code: string; message: string } | null>(null);

  function load() {
    setState("loading");
    config
      .fetcher()
      .then((items) => {
        if (!items || items.length === 0) {
          setState("empty");
          return;
        }
        setItem(items[0]);
        setState("ok");
      })
      .catch((e: unknown) => {
        setErr(errorToFriendlyMessage(e));
        setState("error");
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-space-2 rounded-md border border-border-subtle bg-bg-surface p-space-4">
      <h2 className="text-h3 text-text-primary">{config.title}</h2>

      {state === "loading" && <LoadingSkeleton variant="text" />}

      {state === "error" && <ErrorState code={err?.code} message={err?.message} retry={load} />}

      {state === "empty" && <p className="text-body text-text-muted">無資料</p>}

      {state === "ok" && item && (
        <Link
          href={`/etf/${encodeURIComponent(item.symbol)}`}
          className="flex flex-col gap-space-1 rounded-sm hover:bg-bg-surface-raised"
        >
          <span className="font-mono-num text-h2 text-accent-primary">
            {item.symbol} {item.name ?? ""}
          </span>
          <span className="font-mono-num text-display text-text-primary">{config.formatValue(item)}</span>
        </Link>
      )}

      <p className="text-small text-text-secondary">{config.explanation}</p>
    </div>
  );
}

const QUALITY_COLUMNS: Column[] = [
  { key: "dataset_type", label: "資料類型" },
  { key: "dataset_key", label: "資料對象" },
  { key: "check_name", label: "檢查項目" },
  { key: "severity", label: "嚴重程度" },
  { key: "message", label: "訊息" },
  { key: "checked_at", label: "檢查時間", format: "date" },
];

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryState, setSummaryState] = useState<"loading" | "ok" | "error">("loading");
  const [summaryErr, setSummaryErr] = useState<{ code: string; message: string } | null>(null);

  const [quality, setQuality] = useState<DataQualityCheck[]>([]);
  const [qualityState, setQualityState] = useState<"loading" | "ok" | "error">("loading");
  const [qualityErr, setQualityErr] = useState<{ code: string; message: string } | null>(null);

  function loadSummary() {
    setSummaryState("loading");
    getDashboardSummary()
      .then((data) => {
        setSummary(data);
        setSummaryState("ok");
      })
      .catch((e: unknown) => {
        setSummaryErr(errorToFriendlyMessage(e));
        setSummaryState("error");
      });
  }

  function loadQuality() {
    setQualityState("loading");
    Promise.all([listDataQuality({ status: "FAIL" }), listDataQuality({ status: "WARN" })])
      .then(([fails, warns]) => {
        setQuality([...fails, ...warns]);
        setQualityState("ok");
      })
      .catch((e: unknown) => {
        setQualityErr(errorToFriendlyMessage(e));
        setQualityState("error");
      });
  }

  useEffect(() => {
    loadSummary();
    loadQuality();
  }, []);

  return (
    <div>
      <PageHeader title="研究入口" subtitle="ETF 研究分析工具：成分股、產業曝險、比較、投資組合與回測分析" />

      {/* 上方：4 個 MetricCard */}
      {summaryState === "loading" && (
        <div className="mb-space-8 grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingSkeleton key={i} variant="card" />
          ))}
        </div>
      )}

      {summaryState === "error" && (
        <div className="mb-space-8">
          <ErrorState code={summaryErr?.code} message={summaryErr?.message} retry={loadSummary} />
        </div>
      )}

      {summaryState === "ok" && summary && (
        <div className="mb-space-8 grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="ETF 總數"
            value={formatInteger(summary.total_etfs)}
            explanation="系統中已匯入的 ETF 數量（含啟用與未啟用）。"
          />
          <MetricCard
            label="已匯入成分股 ETF 數"
            value={formatInteger(summary.etfs_with_holdings)}
            explanation="已有成分股持股資料可供分析的 ETF 數量。"
          />
          <MetricCard
            label="已有價格資料 ETF 數"
            value={formatInteger(summary.etfs_with_prices)}
            explanation="已有歷史價格資料，可用於回測與推算的 ETF 數量。"
          />
          <MetricCard
            label="最後更新時間"
            value={summary.last_updated ? formatDate(summary.last_updated) : "尚無資料"}
            explanation="最近一次資料品質檢查的時間，可大致反映資料更新狀態。"
          />
        </div>
      )}

      {/* 中間：排行卡 2x2 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">排行榜</h2>
        <div className="grid grid-cols-1 gap-space-4 sm:grid-cols-2">
          {RANKING_CARDS.map((config) => (
            <RankingCard key={config.title} config={config} />
          ))}
        </div>
      </div>

      {/* 下方：資料品質警告表 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">資料品質警告</h2>
        {qualityState === "loading" && <LoadingSkeleton variant="table" />}
        {qualityState === "error" && (
          <ErrorState code={qualityErr?.code} message={qualityErr?.message} retry={loadQuality} />
        )}
        {qualityState === "ok" && (
          <DataTable
            columns={QUALITY_COLUMNS}
            rows={quality}
            emptyState={{
              title: "目前沒有資料品質警告",
              description: "所有資料品質檢查皆通過，或尚未執行檢查。",
            }}
          />
        )}
      </div>

      {/* 快速入口 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">快速入口</h2>
        <div className="flex flex-wrap gap-space-3">
          <Link
            href="/compare"
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            ETF 比較
          </Link>
          <Link
            href="/portfolio"
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            組合建構
          </Link>
          <Link
            href="/backtest"
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            回測
          </Link>
          <Link
            href="/projection"
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            財務推算
          </Link>
          <Link
            href="/data-sources"
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            資料來源
          </Link>
        </div>
      </div>

      <SourceFooter
        sourceName="ETF Portfolio Lab 資料庫"
        dataDate={summary?.last_updated ?? null}
        disclaimer="本頁資料僅反映系統目前已匯入之資料狀態，回測結果不代表未來績效。"
      />
    </div>
  );
}
