"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import PageHeader from "@/components/layout/PageHeader";
import MetricCard from "@/components/common/MetricCard";
import ChartCard from "@/components/common/ChartCard";
import SourceFooter from "@/components/common/SourceFooter";
import Badge, { BadgeTone } from "@/components/common/Badge";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState, ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import { getEtfCard, getConcentration, getHoldings, getIndustryExposure, getEtfPrices } from "@/lib/api";
import type { Concentration, EtfCard, EtfPriceHistory, Holding, IndustryExposure } from "@/lib/types";
import { formatInteger, formatNumber, formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
  "var(--series-9)",
  "var(--series-10)",
];
const UNCLASSIFIED_COLOR = "var(--series-unclassified)";

// ---------------------------------------------------------------------------
// Presentation-only grading heuristics (not backend-defined thresholds).
// HHI: <0.10 低/分散, 0.10–0.18 中, 0.18–0.25 中高, >0.25 高/集中
// top10_pct (as a percentage 0-100): <30 低, 30-50 中, 50-70 中高, >70 高
// ---------------------------------------------------------------------------
function gradeHhi(hhi: number | null): { label: string; tone: BadgeTone } | undefined {
  if (hhi === null || hhi === undefined) return undefined;
  if (hhi < 0.1) return { label: "低／分散", tone: "success" };
  if (hhi < 0.18) return { label: "中", tone: "info" };
  if (hhi < 0.25) return { label: "中高", tone: "warning" };
  return { label: "高／集中", tone: "error" };
}

function gradeTop10(top10Pct: number | null): { label: string; tone: BadgeTone } | undefined {
  if (top10Pct === null || top10Pct === undefined) return undefined;
  if (top10Pct < 30) return { label: "低", tone: "success" };
  if (top10Pct < 50) return { label: "中", tone: "info" };
  if (top10Pct < 70) return { label: "中高", tone: "warning" };
  return { label: "高", tone: "error" };
}

function managementTypeBadge(value: string | null): { label: string; tone: BadgeTone } {
  if (value === "主動" || value === "active" || value === "Active") {
    return { label: "主動", tone: "warning" };
  }
  if (value === "被動" || value === "passive" || value === "Passive") {
    return { label: "被動", tone: "info" };
  }
  return { label: value ?? "—", tone: "neutral" };
}

type FetchState = "loading" | "ok" | "empty" | "error";

const HOLDINGS_COLUMNS: Column[] = [
  { key: "asset_symbol", label: "個股代號", sortable: true },
  { key: "asset_name", label: "個股名稱", sortable: true },
  { key: "weight_pct", label: "權重", format: "percent", align: "right", sortable: true, decimals: 2 },
];

export default function EtfDetailPage({ params }: { params: { symbol: string } }) {
  const symbol = decodeURIComponent(params.symbol);

  // Card (策略卡 + Badge群 + SourceFooter)
  const [card, setCard] = useState<EtfCard | null>(null);
  const [cardState, setCardState] = useState<FetchState>("loading");
  const [cardErr, setCardErr] = useState<{ code: string; message: string } | null>(null);

  // Price history (chart)
  const [prices, setPrices] = useState<EtfPriceHistory | null>(null);
  const [pricesState, setPricesState] = useState<FetchState>("loading");
  const [pricesErr, setPricesErr] = useState<{ code: string; message: string } | null>(null);

  // Concentration
  const [concentration, setConcentration] = useState<Concentration | null>(null);
  const [concState, setConcState] = useState<FetchState>("loading");
  const [concErr, setConcErr] = useState<{ code: string; message: string } | null>(null);

  // Top 10 holdings (chart)
  const [top10, setTop10] = useState<Holding[]>([]);
  const [top10State, setTop10State] = useState<FetchState>("loading");
  const [top10Err, setTop10Err] = useState<{ code: string; message: string } | null>(null);

  // Full holdings (table)
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [holdingsState, setHoldingsState] = useState<FetchState>("loading");
  const [holdingsErr, setHoldingsErr] = useState<{ code: string; message: string } | null>(null);

  // Price chart type toggle (線圖 / K線)
  const [priceChartType, setPriceChartType] = useState<"line" | "candlestick">("candlestick");

  // Industry exposure (chart, with level toggle)
  const [level, setLevel] = useState<1 | 2>(1);
  const [exposure, setExposure] = useState<IndustryExposure | null>(null);
  const [exposureState, setExposureState] = useState<FetchState>("loading");
  const [exposureErr, setExposureErr] = useState<{ code: string; message: string } | null>(null);

  function loadCard() {
    setCardState("loading");
    getEtfCard(symbol)
      .then((data) => {
        setCard(data);
        setCardState("ok");
      })
      .catch((e: unknown) => {
        setCardErr(errorToFriendlyMessage(e));
        setCardState("error");
      });
  }

  function loadPrices() {
    setPricesState("loading");
    getEtfPrices(symbol, { limit: 1000 })
      .then((data) => {
        setPrices(data);
        setPricesState(data.points.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setPricesErr(errorToFriendlyMessage(e));
        setPricesState("error");
      });
  }

  function loadConcentration() {
    setConcState("loading");
    getConcentration(symbol)
      .then((data) => {
        setConcentration(data);
        setConcState("ok");
      })
      .catch((e: unknown) => {
        setConcErr(errorToFriendlyMessage(e));
        setConcState("error");
      });
  }

  function loadTop10() {
    setTop10State("loading");
    getHoldings(symbol, { n: 10 })
      .then((data) => {
        setTop10(data);
        setTop10State(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setTop10Err(errorToFriendlyMessage(e));
        setTop10State("error");
      });
  }

  function loadHoldings() {
    setHoldingsState("loading");
    getHoldings(symbol, { n: 200 })
      .then((data) => {
        setHoldings(data);
        setHoldingsState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setHoldingsErr(errorToFriendlyMessage(e));
        setHoldingsState("error");
      });
  }

  function loadExposure(lvl: 1 | 2) {
    setExposureState("loading");
    getIndustryExposure(symbol, { level: lvl })
      .then((data) => {
        setExposure(data);
        setExposureState(data.industries.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setExposureErr(errorToFriendlyMessage(e));
        setExposureState("error");
      });
  }

  useEffect(() => {
    loadCard();
    loadPrices();
    loadConcentration();
    loadTop10();
    loadHoldings();
    loadExposure(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const priceChartOption = useMemo(() => {
    if (!prices) return null;
    const dates = prices.points.map((p) => p.date);

    if (priceChartType === "candlestick") {
      return {
        grid: { left: 60, right: 20, top: 30, bottom: 40 },
        tooltip: {
          trigger: "axis",
          formatter: (params: { axisValue: string; data: number[] }[]) => {
            const p = params[0];
            const [open, close, low, high] = p.data;
            return `${p.axisValue}<br/>開：${formatNumber(open, { decimals: 2 })}<br/>高：${formatNumber(high, { decimals: 2 })}<br/>低：${formatNumber(low, { decimals: 2 })}<br/>收：${formatNumber(close, { decimals: 2 })}`;
          },
        },
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { color: "var(--text-secondary)" },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          scale: true,
          axisLabel: { color: "var(--text-secondary)" },
          splitLine: { lineStyle: { color: "var(--border-subtle)" } },
        },
        series: [
          {
            type: "candlestick",
            name: "K線",
            data: prices.points.map((p) => [p.open, p.close, p.low, p.high]),
            itemStyle: {
              color: "#e23b3b",
              color0: "#18a058",
              borderColor: "#e23b3b",
              borderColor0: "#18a058",
            },
          },
        ],
      };
    }

    return {
      grid: { left: 60, right: 20, top: 30, bottom: 40 },
      tooltip: {
        trigger: "axis",
        formatter: (params: { axisValue: string; value: number }[]) => {
          const p = params[0];
          return `${p.axisValue}<br/>收盤價：${formatNumber(p.value, { decimals: 2 })}`;
        },
      },
      xAxis: {
        type: "category",
        data: dates,
        axisLabel: { color: "var(--text-secondary)" },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: { color: "var(--text-secondary)" },
        splitLine: { lineStyle: { color: "var(--border-subtle)" } },
      },
      series: [
        {
          type: "line",
          name: "收盤價",
          data: prices.points.map((p) => p.close),
          showSymbol: false,
          smooth: true,
          itemStyle: { color: "var(--accent-primary)" },
          lineStyle: { color: "var(--accent-primary)" },
          areaStyle: { color: "var(--accent-primary)", opacity: 0.08 },
        },
      ],
    };
  }, [prices, priceChartType]);

  const top10ChartOption = useMemo(() => {
    const sorted = [...top10].sort((a, b) => a.weight_pct - b.weight_pct);
    return {
      grid: { left: 120, right: 40, top: 20, bottom: 20 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params: { name: string; value: number }[]) => {
          const p = params[0];
          return `${p.name}<br/>權重：${formatPercent(p.value, { decimals: 2 })}`;
        },
      },
      xAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
      yAxis: {
        type: "category",
        data: sorted.map((h) => h.asset_name ?? h.asset_symbol),
      },
      series: [
        {
          type: "bar",
          data: sorted.map((h) => h.weight_pct),
          itemStyle: { color: "var(--series-1)" },
        },
      ],
    };
  }, [top10]);

  const exposureChartOption = useMemo(() => {
    if (!exposure) return null;
    const data = exposure.industries.map((it, i) => ({
      name: it.industry,
      value: it.weight_pct,
      itemStyle: { color: SERIES_COLORS[i % SERIES_COLORS.length] },
    }));
    if (exposure.unclassified && exposure.unclassified.weight_pct > 0) {
      data.push({
        name: exposure.unclassified.industry || "未分類",
        value: exposure.unclassified.weight_pct,
        itemStyle: { color: UNCLASSIFIED_COLOR },
      });
    }
    return {
      tooltip: {
        trigger: "item",
        formatter: (p: { name: string; value: number }) =>
          `${p.name}<br/>占比：${formatPercent(p.value, { decimals: 2 })}`,
      },
      legend: { orient: "vertical", left: "left", textStyle: { color: "var(--text-secondary)" } },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          avoidLabelOverlap: true,
          label: { color: "var(--text-secondary)" },
          data,
        },
      ],
    };
  }, [exposure]);

  if (cardState === "loading") {
    return (
      <div>
        <PageHeader title={`ETF 明細：${symbol}`} subtitle="查看策略、持股集中度、產業曝險與成分股重疊分析。" />
        <LoadingSkeleton variant="card" />
      </div>
    );
  }

  if (cardState === "error") {
    return (
      <div>
        <PageHeader title={`ETF 明細：${symbol}`} subtitle="查看策略、持股集中度、產業曝險與成分股重疊分析。" />
        <ErrorState code={cardErr?.code} message={cardErr?.message} retry={loadCard} />
      </div>
    );
  }

  if (!card) {
    return (
      <div>
        <PageHeader title={`ETF 明細：${symbol}`} subtitle="查看策略、持股集中度、產業曝險與成分股重疊分析。" />
        <EmptyState title="找不到此 ETF" description="請確認代號是否正確，或回到 ETF 明細列表。" actionLabel="回到 ETF 明細" actionHref="/etf" />
      </div>
    );
  }

  const mgmt = managementTypeBadge(card.management_type);
  const conc = concentration ?? card.concentration;

  return (
    <div>
      <PageHeader
        title={`${card.symbol} ${card.name}`}
        subtitle="查看策略、持股集中度、產業曝險與成分股重疊分析。"
        actions={
          <a
            href={`/compare?symbols=${encodeURIComponent(card.symbol)}`}
            className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised"
          >
            加入比較
          </a>
        }
      />

      {/* Badge 群 */}
      <div className="mb-space-6 flex flex-wrap gap-space-2">
        <Badge label={mgmt.label} tone={mgmt.tone} />
        {card.asset_class && <Badge label={card.asset_class} tone="neutral" />}
        {card.investment_style && <Badge label={card.investment_style} tone="neutral" />}
      </div>

      {/* 策略卡 */}
      <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <h2 className="mb-space-3 text-h2 text-text-primary">策略資訊</h2>
        <div className="grid grid-cols-1 gap-space-3 sm:grid-cols-2 lg:grid-cols-3">
          <StrategyField label="追蹤指數" value={card.tracking_index} />
          <StrategyField label="指數編製公司" value={card.index_provider} />
          <StrategyField label="選股邏輯" value={card.strategy_type} />
          <StrategyField label="加權方式 / 風格" value={card.investment_style} />
          <StrategyField label="配息頻率" value={card.dividend_frequency} />
          <StrategyField
            label="總管理費用率"
            value={card.expense_ratio !== null ? formatPercent(card.expense_ratio, { decimals: 2, isFraction: card.expense_ratio <= 1 }) : null}
          />
          <StrategyField
            label="經理費"
            value={card.management_fee !== null ? formatPercent(card.management_fee, { decimals: 2, isFraction: card.management_fee <= 1 }) : null}
          />
          <StrategyField
            label="保管費"
            value={card.custody_fee !== null ? formatPercent(card.custody_fee, { decimals: 2, isFraction: card.custody_fee <= 1 }) : null}
          />
          <StrategyField label="發行商" value={card.issuer} />
        </div>
      </div>

      {/* ConcentrationPanel */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">持股集中度</h2>
        {concState === "loading" && (
          <div className="grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <LoadingSkeleton key={i} variant="card" />
            ))}
          </div>
        )}
        {concState === "error" && <ErrorState code={concErr?.code} message={concErr?.message} retry={loadConcentration} />}
        {concState === "ok" && conc && (
          <div className="grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="HHI（持股集中度指標）"
              value={formatNumber(conc.hhi, { decimals: 4 })}
              grade={gradeHhi(conc.hhi)}
              explanation="HHI 為各持股權重平方和，數值越高代表持股越集中於少數標的，越低代表越分散。"
              dataDate={conc.holding_date}
            />
            <MetricCard
              label="有效持股數"
              value={formatNumber(conc.effective_holdings, { decimals: 1 })}
              unit="檔"
              explanation={`有效持股數約為 ${formatNumber(conc.effective_holdings, { decimals: 1 })} 檔——數字越接近實際持股數（${formatInteger(conc.num_holdings)} 檔），代表權重分布越平均。`}
              dataDate={conc.holding_date}
            />
            <MetricCard
              label="實際持股數"
              value={formatInteger(conc.num_holdings)}
              unit="檔"
              explanation="此 ETF 目前持有的成分股總數。"
              dataDate={conc.holding_date}
            />
            <MetricCard
              label="前 1 大持股占比"
              value={formatPercent(conc.top1_pct, { decimals: 2 })}
              explanation="最大持股占整體權重的比例，數字越高代表單一標的對 ETF 績效影響越大。"
              dataDate={conc.holding_date}
            />
            <MetricCard
              label="前 5 大持股占比"
              value={formatPercent(conc.top5_pct, { decimals: 2 })}
              explanation="前五大持股合計占比，數字越高代表組合越集中於少數標的。"
              dataDate={conc.holding_date}
            />
            <MetricCard
              label="前 10 大持股占比"
              value={formatPercent(conc.top10_pct, { decimals: 2 })}
              grade={gradeTop10(conc.top10_pct)}
              explanation="前十大持股合計占比，數字越高代表組合越集中於少數標的。"
              dataDate={conc.holding_date}
            />
          </div>
        )}
      </div>

      {/* Price chart */}
      <div className="mb-space-8">
        <ChartCard
          title="價格走勢（收盤價）"
          unit="TWD"
          dataDate={prices?.data_end ?? null}
          explanation={
            prices?.source_name
              ? `資料來源：${prices.source_name}${prices.data_start ? `，資料區間：${prices.data_start} ~ ${prices.data_end}` : ""}。歷史價格不代表未來績效。`
              : "歷史價格不代表未來績效。"
          }
          loading={pricesState === "loading"}
          error={pricesState === "error" ? pricesErr : null}
          retry={loadPrices}
        >
          {pricesState === "empty" && (
            <EmptyState
              title="尚無價格資料"
              description="請執行 scripts.fetch_all 抓取 ETF 歷史價格資料。"
            />
          )}
          {pricesState === "ok" && priceChartOption && (
            <div>
              <div className="mb-space-2 flex justify-end gap-space-2">
                <button
                  onClick={() => setPriceChartType("line")}
                  className={`rounded-sm border px-space-3 py-1 text-small ${
                    priceChartType === "line"
                      ? "border-accent-primary text-accent-primary"
                      : "border-border-strong text-text-secondary hover:bg-bg-surface-raised"
                  }`}
                >
                  線圖
                </button>
                <button
                  onClick={() => setPriceChartType("candlestick")}
                  className={`rounded-sm border px-space-3 py-1 text-small ${
                    priceChartType === "candlestick"
                      ? "border-accent-primary text-accent-primary"
                      : "border-border-strong text-text-secondary hover:bg-bg-surface-raised"
                  }`}
                >
                  K線
                </button>
              </div>
              <ReactECharts option={priceChartOption} style={{ width: "100%", height: "320px" }} />
            </div>
          )}
        </ChartCard>
      </div>

      {/* Charts */}
      <div className="mb-space-8 grid grid-cols-1 gap-space-4 lg:grid-cols-2">
        <ChartCard
          title="前十大成分股權重"
          unit="%"
          dataDate={concentration?.holding_date ?? null}
          explanation="顯示此 ETF 權重最高的十檔成分股，數字越高代表該個股對 ETF 績效影響越大。"
          loading={top10State === "loading"}
          empty={top10State === "empty"}
          error={top10State === "error" ? top10Err : null}
          retry={loadTop10}
        >
          {top10State === "ok" && (
            <ReactECharts option={top10ChartOption} style={{ width: "100%", height: "320px" }} />
          )}
        </ChartCard>

        <ChartCard
          title="產業占比"
          unit="%"
          dataDate={exposure?.holding_date ?? null}
          explanation="依產業分類顯示持股權重占比，「未分類」代表系統暫無法判斷其產業歸屬之持股。"
          loading={exposureState === "loading"}
          empty={exposureState === "empty"}
          error={exposureState === "error" ? exposureErr : null}
          retry={() => loadExposure(level)}
        >
          {exposureState === "ok" && exposureChartOption && (
            <div>
              <div className="mb-space-2 flex justify-end gap-space-2">
                <button
                  onClick={() => {
                    setLevel(1);
                    loadExposure(1);
                  }}
                  className={`rounded-sm border px-space-3 py-1 text-small ${
                    level === 1
                      ? "border-accent-primary text-accent-primary"
                      : "border-border-strong text-text-secondary hover:bg-bg-surface-raised"
                  }`}
                >
                  一級產業
                </button>
                <button
                  onClick={() => {
                    setLevel(2);
                    loadExposure(2);
                  }}
                  className={`rounded-sm border px-space-3 py-1 text-small ${
                    level === 2
                      ? "border-accent-primary text-accent-primary"
                      : "border-border-strong text-text-secondary hover:bg-bg-surface-raised"
                  }`}
                >
                  二級產業
                </button>
              </div>
              <ReactECharts option={exposureChartOption} style={{ width: "100%", height: "320px" }} />
            </div>
          )}
        </ChartCard>
      </div>

      {/* 全部成分股表格 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">全部成分股</h2>
        {holdingsState === "loading" && <LoadingSkeleton variant="table" />}
        {holdingsState === "error" && <ErrorState code={holdingsErr?.code} message={holdingsErr?.message} retry={loadHoldings} />}
        {(holdingsState === "ok" || holdingsState === "empty") && (
          <DataTable
            columns={HOLDINGS_COLUMNS}
            rows={[...holdings].sort((a, b) => b.weight_pct - a.weight_pct)}
            searchable
            exportCsv
            dataDate={concentration?.holding_date ?? null}
            emptyState={{
              title: "尚無成分股資料",
              description: "此 ETF 目前尚未匯入成分股持股資料。",
            }}
          />
        )}
      </div>

      {/* 持股變化 Timeline + AI 摘要 */}
      <div className="mb-space-8 grid grid-cols-1 gap-space-4 lg:grid-cols-2">
        <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
          <div className="mb-space-3 flex items-center justify-between">
            <h2 className="text-h2 text-text-primary">持股變化 Timeline</h2>
            <Badge label="即將推出" tone="neutral" />
          </div>
          <EmptyState
            title="持股變化 Timeline 即將推出"
            description="此功能需要新增資料表與 API（Phase 13 規劃），目前尚未提供，不會顯示虛構資料。"
          />
        </div>
        <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
          <div className="mb-space-3 flex items-center justify-between">
            <h2 className="text-h2 text-text-primary">AI 摘要</h2>
            <Badge label="即將推出" tone="neutral" />
          </div>
          <EmptyState
            title="AI 摘要功能即將推出"
            description="AI 分析功能將基於系統資料提供研究觀點，目前後端尚未開放此功能。"
          />
        </div>
      </div>

      <SourceFooter
        sourceName={card.data_provenance.source_name}
        sourceUrl={card.data_provenance.source_url}
        dataDate={card.data_provenance.data_date}
        confidenceLevel={card.data_provenance.confidence_level}
        disclaimer="本頁資料僅供研究分析參考，回測與歷史數據不代表未來績效。"
      />
    </div>
  );
}

function StrategyField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-small text-text-muted">{label}</p>
      <p className="text-body text-text-primary">{value ?? "—"}</p>
    </div>
  );
}
