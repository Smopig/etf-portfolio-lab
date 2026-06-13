"use client";

import MetricCard from "@/components/common/MetricCard";
import ChartCard from "@/components/common/ChartCard";
import Badge, { BadgeTone } from "@/components/common/Badge";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState } from "@/components/common/States";
import ExposureBar from "@/components/charts/ExposureBar";
import ExposureDoughnut from "@/components/charts/ExposureDoughnut";
import OverlapHeatmap from "@/components/charts/OverlapHeatmap";
import { formatNumber, formatPercent } from "@/lib/format";
import type {
  IndustryExposure,
  MultiOverlap,
  PortfolioConcentration,
  PortfolioWarning,
  StockExposureResponse,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Presentation-only grading heuristics (consistent with ETF detail page)
// ---------------------------------------------------------------------------
function gradeHhi(hhi: number | null | undefined): { label: string; tone: BadgeTone } | undefined {
  if (hhi === null || hhi === undefined) return undefined;
  if (hhi < 0.1) return { label: "低／分散", tone: "success" };
  if (hhi < 0.18) return { label: "中", tone: "info" };
  if (hhi < 0.25) return { label: "中高", tone: "warning" };
  return { label: "高／集中", tone: "error" };
}

function gradeTop10(top10Pct: number | null | undefined): { label: string; tone: BadgeTone } | undefined {
  if (top10Pct === null || top10Pct === undefined) return undefined;
  if (top10Pct < 30) return { label: "低", tone: "success" };
  if (top10Pct < 50) return { label: "中", tone: "info" };
  if (top10Pct < 70) return { label: "中高", tone: "warning" };
  return { label: "高", tone: "error" };
}

function severityTone(severity: string): BadgeTone {
  if (severity === "ERROR") return "error";
  if (severity === "WARN") return "warning";
  if (severity === "INFO") return "info";
  return "neutral";
}

const STOCK_EXPOSURE_COLUMNS: Column[] = [
  { key: "asset_symbol", label: "個股代號", sortable: true },
  { key: "asset_name", label: "個股名稱", sortable: true },
  { key: "weight_pct", label: "穿透後權重", format: "percent", align: "right", sortable: true, decimals: 2 },
];

export interface PortfolioAnalysisProps {
  stockExposure: StockExposureResponse | null;
  industryExposure: IndustryExposure | Record<string, unknown> | null;
  concentration: PortfolioConcentration | null;
  warnings: PortfolioWarning[];
  disclaimer?: string | null;
  overlapRisk?: MultiOverlap | null;
  loading?: boolean;
}

function isIndustryExposure(v: unknown): v is IndustryExposure {
  return !!v && typeof v === "object" && Array.isArray((v as IndustryExposure).industries);
}

export default function PortfolioAnalysis({
  stockExposure,
  industryExposure,
  concentration,
  warnings,
  disclaimer,
  overlapRisk,
  loading,
}: PortfolioAnalysisProps) {
  const stocks = stockExposure?.stocks ?? [];
  const top10Stocks = [...stocks].sort((a, b) => b.weight_pct - a.weight_pct).slice(0, 10);

  const industryData = isIndustryExposure(industryExposure) ? industryExposure : null;
  const doughnutItems = industryData
    ? [
        ...industryData.industries.map((it) => ({ name: it.industry, value: it.weight_pct })),
        ...(industryData.unclassified && industryData.unclassified.weight_pct > 0
          ? [{ name: industryData.unclassified.industry || "未分類", value: industryData.unclassified.weight_pct, unclassified: true }]
          : []),
      ]
    : [];

  return (
    <div>
      {/* 穿透後股票曝險 */}
      <div className="mb-space-8 grid grid-cols-1 gap-space-4 lg:grid-cols-2">
        <ChartCard
          title="穿透後 Top 10 股票曝險"
          unit="%"
          explanation="顯示組合穿透 ETF 後，權重最高的十檔個股。數字越高代表該個股對整體組合績效影響越大。"
          loading={loading}
          empty={!loading && top10Stocks.length === 0}
        >
          {top10Stocks.length > 0 && (
            <ExposureBar items={top10Stocks.map((s) => ({ name: s.asset_name ?? s.asset_symbol, value: s.weight_pct }))} />
          )}
        </ChartCard>

        <ChartCard
          title="穿透後產業曝險"
          unit="%"
          dataDate={industryData?.holding_date ?? null}
          explanation="依產業分類顯示組合穿透後的權重占比，「未分類」代表系統暫無法判斷其產業歸屬之持股。"
          loading={loading}
          empty={!loading && doughnutItems.length === 0}
        >
          {doughnutItems.length > 0 && <ExposureDoughnut items={doughnutItems} />}
        </ChartCard>
      </div>

      {/* 組合集中度 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">組合集中度</h2>
        {loading && <p className="text-body text-text-muted">載入中...</p>}
        {!loading && concentration && (
          <div className="grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="HHI（持股集中度指標）"
              value={formatNumber(concentration.hhi, { decimals: 4 })}
              grade={gradeHhi(concentration.hhi)}
              explanation="HHI 為穿透後各持股權重平方和，數值越高代表持股越集中於少數標的，越低代表越分散。"
            />
            <MetricCard
              label="有效持股數"
              value={formatNumber(concentration.effective_holdings, { decimals: 1 })}
              unit="檔"
              explanation={`有效持股數約為 ${formatNumber(concentration.effective_holdings, { decimals: 1 })} 檔——數字越接近實際持股數（${concentration.num_stocks} 檔），代表權重分布越平均。`}
            />
            <MetricCard
              label="前 1 大持股占比"
              value={formatPercent(concentration.top1_pct, { decimals: 2 })}
              explanation="穿透後最大持股占整體權重的比例，數字越高代表單一標的對組合績效影響越大。"
            />
            <MetricCard
              label="前 10 大持股占比"
              value={formatPercent(concentration.top10_pct, { decimals: 2 })}
              grade={gradeTop10(concentration.top10_pct)}
              explanation="穿透後前十大持股合計占比，數字越高代表組合越集中於少數標的。"
            />
          </div>
        )}
      </div>

      {/* 穿透後股票曝險明細表 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">穿透後股票曝險明細</h2>
        <DataTable
          columns={STOCK_EXPOSURE_COLUMNS}
          rows={[...stocks].sort((a, b) => b.weight_pct - a.weight_pct)}
          searchable
          exportCsv
          loading={loading}
          emptyState={{ title: "尚無穿透曝險資料", description: "請先加入 ETF 並設定權重。" }}
        />
        {stockExposure?.missing_holdings && stockExposure.missing_holdings.length > 0 && (
          <p className="mt-space-2 text-small text-status-warning">
            以下 ETF 缺少成分股資料，未納入穿透分析：{stockExposure.missing_holdings.join("、")}
          </p>
        )}
      </div>

      {/* 重疊風險 */}
      {overlapRisk && overlapRisk.symbols.length >= 2 && (
        <div className="mb-space-8">
          <h2 className="mb-space-2 text-h2 text-text-primary">重疊風險</h2>
          <p className="mb-space-4 text-small text-text-secondary">
            顯示組合內各 ETF 之間的加權重疊度。數字越高代表兩檔 ETF 持股越相似，分散效果越低。
          </p>
          <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
            <OverlapHeatmap symbols={overlapRisk.symbols} matrix={overlapRisk.matrix} pairs={overlapRisk.pairs} />
          </div>
        </div>
      )}

      {/* 警告清單 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">警告清單</h2>
        {warnings.length === 0 ? (
          <EmptyState title="目前沒有警告" description="此配置未觸發任何分散度或資料品質警告。" />
        ) : (
          <ul className="flex flex-col gap-space-2">
            {warnings.map((w, i) => (
              <li
                key={i}
                className="flex items-start gap-space-2 rounded-md border border-border-subtle bg-bg-surface p-space-3"
              >
                <Badge label={w.severity} tone={severityTone(w.severity)} />
                <span className="text-body text-text-primary">{w.message}</span>
              </li>
            ))}
          </ul>
        )}
        {disclaimer && <p className="mt-space-3 text-small text-text-secondary">{disclaimer}</p>}
      </div>
    </div>
  );
}
