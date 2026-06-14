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
import { getEtfCard, getConcentration, getHoldings, getHoldingsWithMeta, getIndustryExposure, getEtfPrices, getDividendRecoveryWithMeta } from "@/lib/api";
import type { Concentration, DividendRecoveryMeta, DividendRecoveryRow, EtfCard, EtfPriceHistory, Holding, HoldingsMeta, IndustryExposure } from "@/lib/types";
import { formatDate, formatInteger, formatNumber, formatPercent } from "@/lib/format";
import { chartColor, seriesPalette } from "@/lib/chartColors";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

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

// Backend holdings carry raw confidence text (HIGH / MEDIUM / LOW). Map to a
// localized label + semantic tone for the disclosure badge (CLAUDE.md §7).
function confidenceBadge(value: string | null | undefined): { label: string; tone: BadgeTone } | undefined {
  if (!value) return undefined;
  const v = value.toUpperCase();
  if (v === "HIGH" || value === "高") return { label: "高", tone: "success" };
  if (v === "MEDIUM" || value === "中") return { label: "中", tone: "warning" };
  if (v === "LOW" || value === "低") return { label: "低", tone: "error" };
  return { label: value, tone: "neutral" };
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

function movingAverage(points: { close: number | null }[], n: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i < n - 1) {
      result.push(null);
      continue;
    }
    let sum = 0;
    let valid = true;
    for (let j = i - n + 1; j <= i; j++) {
      const c = points[j].close;
      if (c === null || c === undefined) {
        valid = false;
        break;
      }
      sum += c;
    }
    result.push(valid ? sum / n : null);
  }
  return result;
}

function formatCompactVolume(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value >= 1e8) return `${formatNumber(value / 1e8, { decimals: 2 })}億`;
  if (value >= 1e4) return `${formatNumber(value / 1e4, { decimals: 2 })}萬`;
  return formatInteger(value);
}

// Compact NTD amount in 億/兆 (mirrors formatCompactVolume style) for AUM.
function formatCompactAum(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value >= 1e12) return `${formatNumber(value / 1e12, { decimals: 2 })} 兆`;
  if (value >= 1e8) return `${formatNumber(value / 1e8, { decimals: 0 })} 億`;
  if (value >= 1e4) return `${formatNumber(value / 1e4, { decimals: 2 })} 萬`;
  return formatInteger(value);
}

const MA_PERIODS = [5, 10, 20, 60] as const;
const MA_COLORS: Record<number, string> = {
  5: "#f5a623",
  10: "#4ec9b0",
  20: "#b07cff",
  60: "#ff6b9d",
};
const DEFAULT_MA_PERIODS: number[] = [5, 20];

type FetchState = "loading" | "ok" | "empty" | "error";

function buildHoldingsColumns(hasShares: boolean): Column[] {
  const cols: Column[] = [
    { key: "asset_symbol", label: "個股代號", sortable: true },
    { key: "asset_name", label: "個股名稱", sortable: true },
    { key: "weight_pct", label: "權重", format: "percent", align: "right", sortable: true, decimals: 2 },
  ];
  if (hasShares) {
    cols.push({
      key: "shares",
      label: "持股股數",
      format: "number",
      align: "right",
      sortable: true,
      decimals: 0,
    });
  }
  return cols;
}

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
  const [holdingsMeta, setHoldingsMeta] = useState<HoldingsMeta | null>(null);
  const [holdingsState, setHoldingsState] = useState<FetchState>("loading");
  const [holdingsErr, setHoldingsErr] = useState<{ code: string; message: string } | null>(null);

  // Price chart type toggle (線圖 / K線)
  const [priceChartType, setPriceChartType] = useState<"line" | "candlestick">("candlestick");

  // Moving average periods toggle
  const [maPeriods, setMaPeriods] = useState<number[]>(DEFAULT_MA_PERIODS);

  function toggleMaPeriod(period: number) {
    setMaPeriods((prev) =>
      prev.includes(period) ? prev.filter((p) => p !== period) : [...prev, period].sort((a, b) => a - b)
    );
  }

  // Dividend recovery (填息天數)
  const [recovery, setRecovery] = useState<DividendRecoveryRow[]>([]);
  const [recoveryMeta, setRecoveryMeta] = useState<DividendRecoveryMeta | null>(null);
  const [recoveryState, setRecoveryState] = useState<FetchState>("loading");
  const [recoveryErr, setRecoveryErr] = useState<{ code: string; message: string } | null>(null);

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
    getHoldingsWithMeta(symbol, { n: 200 })
      .then(({ holdings: data, meta }) => {
        setHoldings(data);
        setHoldingsMeta(meta);
        setHoldingsState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setHoldingsErr(errorToFriendlyMessage(e));
        setHoldingsState("error");
      });
  }

  function loadRecovery() {
    setRecoveryState("loading");
    getDividendRecoveryWithMeta(symbol)
      .then(({ rows, meta }) => {
        setRecovery(rows);
        setRecoveryMeta(meta);
        setRecoveryState(rows.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setRecoveryErr(errorToFriendlyMessage(e));
        setRecoveryState("error");
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
    loadRecovery();
    loadExposure(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const priceChartOption = useMemo(() => {
    if (!prices) return null;
    const dates = prices.points.map((p) => p.date);
    const volumes = prices.points.map((p) => p.volume ?? 0);

    const AXIS_LABEL_COLOR = "#c2cad6";
    const AXIS_LINE_COLOR = "#3a4250";
    const SPLIT_LINE_COLOR = "#272d38";

    const sharedGrid = [
      { left: 60, right: 20, top: 30, height: "50%" },
      { left: 60, right: 20, top: "64%", height: "20%" },
    ];

    const sharedXAxis = [
      {
        type: "category",
        data: dates,
        gridIndex: 0,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: AXIS_LINE_COLOR } },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: dates,
        gridIndex: 1,
        axisLabel: { color: AXIS_LABEL_COLOR },
        axisLine: { onZero: false, lineStyle: { color: AXIS_LINE_COLOR } },
        axisTick: { lineStyle: { color: AXIS_LINE_COLOR } },
        splitLine: { show: false },
      },
    ];

    const sharedYAxis = [
      {
        type: "value",
        scale: true,
        gridIndex: 0,
        axisLabel: { color: AXIS_LABEL_COLOR },
        axisLine: { lineStyle: { color: AXIS_LINE_COLOR } },
        axisTick: { lineStyle: { color: AXIS_LINE_COLOR } },
        splitLine: { lineStyle: { color: SPLIT_LINE_COLOR } },
      },
      {
        type: "value",
        gridIndex: 1,
        axisLabel: {
          color: AXIS_LABEL_COLOR,
          formatter: (value: number) => formatCompactVolume(value),
        },
        axisLine: { lineStyle: { color: AXIS_LINE_COLOR } },
        axisTick: { lineStyle: { color: AXIS_LINE_COLOR } },
        splitLine: { show: false },
      },
    ];

    const maNames = maPeriods.map((n) => `MA${n}`);

    const maSeries = maPeriods.map((n) => ({
      type: "line",
      name: `MA${n}`,
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: movingAverage(prices.points, n),
      showSymbol: false,
      smooth: true,
      lineStyle: { color: MA_COLORS[n], width: 1.5 },
      itemStyle: { color: MA_COLORS[n] },
    }));

    const sharedLegend = {
      data: maNames,
      top: 4,
      right: 20,
      textStyle: { color: "#c2cad6" },
      itemWidth: 16,
      itemHeight: 8,
    };

    const axisPointerLink = { link: [{ xAxisIndex: "all" }] };

    const sharedDataZoom = [
      { type: "inside", xAxisIndex: [0, 1], zoomOnMouseWheel: true, moveOnMouseMove: true, throttle: 50 },
      {
        type: "slider",
        xAxisIndex: [0, 1],
        height: 18,
        bottom: 4,
        borderColor: AXIS_LINE_COLOR,
        backgroundColor: "#1c2129",
        fillerColor: "rgba(90, 169, 255, 0.2)",
        handleStyle: { color: "#5aa9ff", borderColor: "#5aa9ff" },
        moveHandleStyle: { color: "#5aa9ff" },
        textStyle: { color: AXIS_LABEL_COLOR },
        dataBackground: {
          lineStyle: { color: AXIS_LINE_COLOR },
          areaStyle: { color: AXIS_LINE_COLOR },
        },
      },
    ];

    if (priceChartType === "candlestick") {
      const volumeData = prices.points.map((p) => ({
        value: p.volume ?? 0,
        itemStyle: { color: (p.close ?? 0) >= (p.open ?? 0) ? "#e23b3b" : "#18a058" },
      }));
      return {
        grid: sharedGrid,
        legend: sharedLegend,
        axisPointer: axisPointerLink,
        dataZoom: sharedDataZoom,
        tooltip: {
          trigger: "axis",
          formatter: (params: { axisValue: string; seriesName: string; data: number[] | { value: number; itemStyle?: unknown } | number }[]) => {
            const pricePoint = params.find((p) => p.seriesName === "K線");
            const volumePoint = params.find((p) => p.seriesName === "成交量");
            const axisValue = params[0]?.axisValue ?? "";
            let lines = `${axisValue}`;
            if (pricePoint && Array.isArray(pricePoint.data)) {
              const [open, close, low, high] = pricePoint.data;
              lines += `<br/>開：${formatNumber(open, { decimals: 2 })}<br/>高：${formatNumber(high, { decimals: 2 })}<br/>低：${formatNumber(low, { decimals: 2 })}<br/>收：${formatNumber(close, { decimals: 2 })}`;
            }
            for (const n of maPeriods) {
              const maPoint = params.find((p) => p.seriesName === `MA${n}`);
              if (maPoint && typeof maPoint.data === "number") {
                lines += `<br/>MA${n}：${formatNumber(maPoint.data, { decimals: 2 })}`;
              }
            }
            if (volumePoint) {
              const vol = Array.isArray(volumePoint.data) || typeof volumePoint.data === "number" ? 0 : volumePoint.data.value;
              lines += `<br/>成交量：${formatCompactVolume(vol)}`;
            }
            return lines;
          },
        },
        xAxis: sharedXAxis,
        yAxis: sharedYAxis,
        series: [
          {
            type: "candlestick",
            name: "K線",
            xAxisIndex: 0,
            yAxisIndex: 0,
            data: prices.points.map((p) => [p.open, p.close, p.low, p.high]),
            itemStyle: {
              color: "#e23b3b",
              color0: "#18a058",
              borderColor: "#e23b3b",
              borderColor0: "#18a058",
            },
          },
          ...maSeries,
          {
            type: "bar",
            name: "成交量",
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: volumeData,
          },
        ],
      };
    }

    return {
      grid: sharedGrid,
      legend: sharedLegend,
      axisPointer: axisPointerLink,
      dataZoom: sharedDataZoom,
      tooltip: {
        trigger: "axis",
        formatter: (params: { axisValue: string; seriesName: string; value: number }[]) => {
          const pricePoint = params.find((p) => p.seriesName === "收盤價");
          const volumePoint = params.find((p) => p.seriesName === "成交量");
          const axisValue = params[0]?.axisValue ?? "";
          let lines = `${axisValue}`;
          if (pricePoint) {
            lines += `<br/>收盤價：${formatNumber(pricePoint.value, { decimals: 2 })}`;
          }
          for (const n of maPeriods) {
            const maPoint = params.find((p) => p.seriesName === `MA${n}`);
            if (maPoint && maPoint.value !== null && maPoint.value !== undefined) {
              lines += `<br/>MA${n}：${formatNumber(maPoint.value, { decimals: 2 })}`;
            }
          }
          if (volumePoint) {
            lines += `<br/>成交量：${formatCompactVolume(volumePoint.value)}`;
          }
          return lines;
        },
      },
      xAxis: sharedXAxis,
      yAxis: sharedYAxis,
      series: [
        {
          type: "line",
          name: "收盤價",
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: prices.points.map((p) => p.close),
          showSymbol: false,
          smooth: true,
          itemStyle: { color: "#5aa9ff" },
          lineStyle: { color: "#5aa9ff", width: 2 },
          areaStyle: { color: "#5aa9ff", opacity: 0.08 },
        },
        ...maSeries,
        {
          type: "bar",
          name: "成交量",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: { color: chartColor("--accent-primary"), opacity: 0.35 },
        },
      ],
    };
  }, [prices, priceChartType, maPeriods]);

  const priceHeader = useMemo(() => {
    if (!prices || prices.points.length === 0) return null;
    const withClose = prices.points.filter((p) => p.close !== null && p.close !== undefined);
    if (withClose.length === 0) return null;
    const latest = withClose[withClose.length - 1];
    const prev = withClose.length > 1 ? withClose[withClose.length - 2] : null;
    const latestClose = latest.close as number;
    if (!prev) {
      return { latestClose, change: null, changePct: null, date: latest.date };
    }
    const prevClose = prev.close as number;
    const change = latestClose - prevClose;
    const changePct = prevClose !== 0 ? (change / prevClose) * 100 : null;
    return { latestClose, change, changePct, date: latest.date };
  }, [prices]);

  const top10ChartOption = useMemo(() => {
    const sorted = [...top10].sort((a, b) => a.weight_pct - b.weight_pct);
    const textSecondary = chartColor("--text-secondary");
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
      xAxis: { type: "value", axisLabel: { formatter: "{value}%", color: textSecondary } },
      yAxis: {
        type: "category",
        data: sorted.map((h) => h.asset_name ?? h.asset_symbol),
        axisLabel: { color: textSecondary },
      },
      series: [
        {
          type: "bar",
          data: sorted.map((h) => h.weight_pct),
          itemStyle: { color: chartColor("--series-1") },
        },
      ],
    };
  }, [top10]);

  const exposureChartOption = useMemo(() => {
    if (!exposure) return null;
    const palette = seriesPalette();
    const textSecondary = chartColor("--text-secondary");
    const data = exposure.industries.map((it, i) => ({
      name: it.industry,
      value: it.weight_pct,
      itemStyle: { color: palette[i % palette.length] },
    }));
    if (exposure.unclassified && exposure.unclassified.weight_pct > 0) {
      data.push({
        name: exposure.unclassified.industry || "未分類",
        value: exposure.unclassified.weight_pct,
        itemStyle: { color: chartColor("--series-unclassified") },
      });
    }
    return {
      tooltip: {
        trigger: "item",
        formatter: (p: { name: string; value: number }) =>
          `${p.name}<br/>占比：${formatPercent(p.value, { decimals: 2 })}`,
      },
      legend: { orient: "vertical", left: "left", textStyle: { color: textSecondary } },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          avoidLabelOverlap: true,
          label: { color: textSecondary },
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

      {/* 現價 + 漲跌 */}
      {priceHeader && (
        <div className="mb-space-6 flex items-baseline gap-space-3">
          <span className="text-h1 text-text-primary">
            {formatNumber(priceHeader.latestClose, { decimals: 2 })}
          </span>
          <span className="text-body text-text-muted">TWD</span>
          {priceHeader.change !== null && priceHeader.changePct !== null && (
            <span
              className="text-body font-medium"
              style={{
                color:
                  priceHeader.change > 0
                    ? "#e23b3b"
                    : priceHeader.change < 0
                      ? "#18a058"
                      : "var(--text-muted)",
              }}
            >
              {priceHeader.change > 0 ? "+" : ""}
              {formatNumber(priceHeader.change, { decimals: 2 })} (
              {priceHeader.change > 0 ? "+" : ""}
              {formatNumber(priceHeader.changePct, { decimals: 2 })}%)
            </span>
          )}
          <span className="text-small text-text-muted">收盤 {priceHeader.date}</span>
        </div>
      )}

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
            label="基金規模（AUM）"
            value={card.aum !== null && card.aum !== undefined ? formatCompactAum(card.aum) : null}
          />
          <StrategyField
            label="每股淨值（NAV）"
            value={
              card.nav !== null && card.nav !== undefined
                ? `${formatNumber(card.nav, { decimals: 2 })} 元${card.nav_date ? `（${formatDate(card.nav_date)}）` : ""}`
                : null
            }
          />
          <StrategyField
            label="總管理費用率"
            value={card.expense_ratio !== null ? `${formatNumber(card.expense_ratio, { decimals: 2 })}%` : null}
          />
          <StrategyField
            label="經理費"
            value={card.management_fee !== null ? `${formatNumber(card.management_fee, { decimals: 4 })}%` : null}
          />
          <StrategyField
            label="保管費"
            value={card.custody_fee !== null ? `${formatNumber(card.custody_fee, { decimals: 2 })}%` : null}
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
              <div className="mb-space-2 flex flex-wrap items-center justify-end gap-space-2">
                <span className="text-small text-text-muted">MA：</span>
                {MA_PERIODS.map((n) => (
                  <button
                    key={n}
                    onClick={() => toggleMaPeriod(n)}
                    className={`rounded-sm border px-space-3 py-1 text-small ${
                      maPeriods.includes(n)
                        ? "border-accent-primary text-accent-primary"
                        : "border-border-strong text-text-secondary hover:bg-bg-surface-raised"
                    }`}
                  >
                    MA{n}
                  </button>
                ))}
                <span className="mx-space-2 h-4 w-px bg-border-strong" />
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
              <ReactECharts option={priceChartOption} style={{ width: "100%", height: "460px" }} />
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
        {(() => {
          const meta = holdingsMeta;
          const hasShares = holdings.some(
            (h) => h.shares !== null && h.shares !== undefined
          );
          const isFullList = hasShares || holdings.length > 10;
          const heading =
            holdingsState === "ok" && isFullList
              ? `完整成分股（共 ${formatInteger(holdings.length)} 檔）`
              : "前 10 大持股";
          const confidence = confidenceBadge(meta?.confidence_level);
          return (
            <>
              <div className="mb-space-2 flex flex-wrap items-baseline gap-x-space-3 gap-y-space-1">
                <h2 className="text-h2 text-text-primary">{heading}</h2>
              </div>

              {/* 資料來源揭露（CLAUDE.md §7）：資料來源 / 資料日期 / 可信度 / 過舊警示 */}
              {meta && (meta.source_name || meta.holding_date || confidence) && (
                <div className="mb-space-3 flex flex-wrap items-center gap-x-space-4 gap-y-space-1 text-small text-text-muted">
                  {meta.source_name && (
                    <span>
                      資料來源：
                      {meta.source_url ? (
                        <a
                          href={meta.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent-primary hover:underline"
                        >
                          {meta.source_name}
                        </a>
                      ) : (
                        <span className="text-text-secondary">{meta.source_name}</span>
                      )}
                    </span>
                  )}
                  {meta.holding_date && <span>資料日期：{formatDate(meta.holding_date)}</span>}
                  {confidence && (
                    <span className="inline-flex items-center gap-space-1">
                      可信度：
                      <Badge label={confidence.label} tone={confidence.tone} />
                    </span>
                  )}
                </div>
              )}
              {meta?.is_stale && (
                <div className="mb-space-3">
                  <Badge
                    label={`資料可能過舊（最後更新：${formatDate(meta.holding_date)}）`}
                    tone="warning"
                  />
                </div>
              )}

              {holdingsState === "loading" && <LoadingSkeleton variant="table" />}
              {holdingsState === "error" && (
                <ErrorState code={holdingsErr?.code} message={holdingsErr?.message} retry={loadHoldings} />
              )}
              {(holdingsState === "ok" || holdingsState === "empty") && (
                <DataTable
                  columns={buildHoldingsColumns(hasShares)}
                  rows={[...holdings].sort((a, b) => b.weight_pct - a.weight_pct)}
                  searchable
                  exportCsv
                  dataDate={meta?.holding_date ?? concentration?.holding_date ?? null}
                  emptyState={{
                    title: "尚無成分股資料",
                    description: "此 ETF 目前尚未匯入成分股持股資料。",
                  }}
                />
              )}
            </>
          );
        })()}
      </div>

      {/* 填息天數 */}
      <div className="mb-space-8">
        <h2 className="mb-space-2 text-h2 text-text-primary">填息天數</h2>
        <p className="mb-space-3 text-small text-text-muted">
          填息天數＝除息後股價回到除息前收盤價所經過的交易日數。
          {recoveryMeta?.source_name ? `資料來源：${recoveryMeta.source_name}。` : ""}
          過去填息表現不代表未來，僅供研究分析參考。
        </p>

        {recoveryState === "loading" && <LoadingSkeleton variant="table" />}
        {recoveryState === "error" && (
          <ErrorState code={recoveryErr?.code} message={recoveryErr?.message} retry={loadRecovery} />
        )}
        {recoveryState === "empty" && (
          <EmptyState
            title="此 ETF 無配息紀錄"
            description="目前尚未匯入此 ETF 的除息與填息資料，不會顯示虛構資料。"
          />
        )}
        {recoveryState === "ok" && (
          <div className="overflow-x-auto rounded-md border border-border-subtle bg-bg-surface">
            <table className="w-full min-w-[640px] text-body">
              <thead>
                <tr className="border-b border-border-subtle text-small text-text-muted">
                  <th className="px-space-3 py-space-2 text-left font-medium">除息日</th>
                  <th className="px-space-3 py-space-2 text-right font-medium">配息金額</th>
                  <th className="px-space-3 py-space-2 text-right font-medium">除息前收盤</th>
                  <th className="px-space-3 py-space-2 text-right font-medium">填息天數</th>
                  <th className="px-space-3 py-space-2 text-left font-medium">填息日</th>
                </tr>
              </thead>
              <tbody>
                {[...recovery]
                  .sort((a, b) => (a.ex_date < b.ex_date ? 1 : -1))
                  .map((r) => (
                    <tr key={r.ex_date} className="border-b border-border-subtle last:border-0">
                      <td className="px-space-3 py-space-2 text-left text-text-primary">
                        {formatDate(r.ex_date)}
                      </td>
                      <td className="px-space-3 py-space-2 text-right text-text-primary">
                        {r.dividend_amount !== null ? `${formatNumber(r.dividend_amount, { decimals: 2 })} 元` : "—"}
                      </td>
                      <td className="px-space-3 py-space-2 text-right text-text-primary">
                        {r.pre_ex_close !== null ? formatNumber(r.pre_ex_close, { decimals: 2 }) : "—"}
                      </td>
                      <td className="px-space-3 py-space-2 text-right">
                        {r.recovered ? (
                          <span className="text-text-primary">
                            {r.days_to_recover !== null ? `${formatInteger(r.days_to_recover)} 天` : "—"}
                          </span>
                        ) : (
                          <Badge label="尚未填息" tone="warning" />
                        )}
                      </td>
                      <td className="px-space-3 py-space-2 text-left text-text-secondary">
                        {r.recovered ? formatDate(r.recovered_date) : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
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
