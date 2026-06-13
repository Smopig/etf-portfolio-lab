"use client";

import { Suspense, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import MetricCard from "@/components/common/MetricCard";
import ChartCard from "@/components/common/ChartCard";
import SourceFooter from "@/components/common/SourceFooter";
import Badge, { BadgeTone } from "@/components/common/Badge";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState, ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import { runBacktest, listPortfolios } from "@/lib/api";
import type { BacktestRequestPayload, BacktestResult, Portfolio } from "@/lib/types";
import { formatCurrencyTWD, formatNumber, formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const REBALANCE_OPTIONS = [
  { value: "none", label: "不再平衡" },
  { value: "monthly", label: "每月" },
  { value: "quarterly", label: "每季" },
  { value: "semiannual", label: "每半年" },
  { value: "annual", label: "每年" },
];

const ANNUAL_RETURNS_COLUMNS: Column[] = [
  { key: "year", label: "年度", sortable: true },
  { key: "return_pct", label: "報酬率", format: "percent", align: "right", sortable: true, decimals: 2 },
];

function gradeDrawdown(value: number | null): { label: string; tone: BadgeTone } | undefined {
  if (value === null || value === undefined) return undefined;
  const abs = Math.abs(value) <= 1 ? Math.abs(value) * 100 : Math.abs(value);
  if (abs < 10) return { label: "輕微", tone: "success" };
  if (abs < 20) return { label: "中等", tone: "info" };
  if (abs < 35) return { label: "較大", tone: "warning" };
  return { label: "嚴重", tone: "error" };
}

function gradeSharpe(value: number | null): { label: string; tone: BadgeTone } | undefined {
  if (value === null || value === undefined) return undefined;
  if (value < 0) return { label: "不佳", tone: "error" };
  if (value < 0.5) return { label: "偏低", tone: "warning" };
  if (value < 1) return { label: "中等", tone: "info" };
  return { label: "良好", tone: "success" };
}

type FetchState = "idle" | "loading" | "ok" | "error";

function BacktestContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState<string>("");
  const [symbolsText, setSymbolsText] = useState("0050,0056");
  const [weightsText, setWeightsText] = useState("60,40");
  const [startDate, setStartDate] = useState("2015-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [initialAmount, setInitialAmount] = useState("100000");
  const [monthlyContribution, setMonthlyContribution] = useState("0");
  const [dividendReinvest, setDividendReinvest] = useState(true);
  const [rebalanceFrequency, setRebalanceFrequency] = useState("none");
  const [transactionCostRate, setTransactionCostRate] = useState("0.001425");

  const [state, setState] = useState<FetchState>("idle");
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  useEffect(() => {
    listPortfolios()
      .then(setPortfolios)
      .catch(() => setPortfolios([]));
    const pid = searchParams.get("portfolio_id");
    if (pid) setPortfolioId(pid);
  }, [searchParams]);

  function buildPayload(): BacktestRequestPayload | null {
    const payload: BacktestRequestPayload = {
      start_date: startDate,
      end_date: endDate,
      initial_amount: Number(initialAmount) || 0,
      monthly_contribution: Number(monthlyContribution) || 0,
      dividend_reinvest: dividendReinvest,
      rebalance_frequency: rebalanceFrequency,
      transaction_cost_rate: Number(transactionCostRate) || 0,
    };

    if (portfolioId) {
      payload.portfolio_id = Number(portfolioId);
    } else {
      const symbols = symbolsText.split(",").map((s) => s.trim()).filter(Boolean);
      const weights = weightsText
        .split(",")
        .map((w) => Number(w.trim()))
        .filter((w) => !Number.isNaN(w));
      if (symbols.length === 0 || symbols.length !== weights.length) {
        setError({ code: "VALIDATION_ERROR", message: "請確認 ETF 代號與權重數量一致" });
        return null;
      }
      payload.symbols = symbols;
      payload.weights = weights;
    }
    return payload;
  }

  function handleSubmit() {
    const payload = buildPayload();
    if (!payload) {
      setState("error");
      return;
    }
    setState("loading");
    setError(null);
    runBacktest(payload, { persist: false })
      .then((data) => {
        setResult(data);
        setState("ok");
      })
      .catch((e: unknown) => {
        setError(errorToFriendlyMessage(e));
        setState("error");
      });
  }

  const assetChartOption = result
    ? {
        backgroundColor: "transparent",
        grid: { left: 60, right: 24, top: 24, bottom: 40 },
        tooltip: { trigger: "axis" },
        xAxis: {
          type: "category",
          data: result.portfolio_value_series.map((p) => p.date),
          axisLabel: { color: "var(--text-secondary)" },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: "var(--text-secondary)" },
          splitLine: { lineStyle: { color: "var(--border-subtle)" } },
        },
        series: [
          {
            name: "資產價值",
            type: "line",
            showSymbol: false,
            data: result.portfolio_value_series.map((p) => p.value),
            lineStyle: { color: "var(--series-1)" },
            areaStyle: { color: "var(--series-1)", opacity: 0.1 },
          },
        ],
      }
    : null;

  const drawdownChartOption = result
    ? {
        backgroundColor: "transparent",
        grid: { left: 60, right: 24, top: 24, bottom: 40 },
        tooltip: { trigger: "axis" },
        xAxis: {
          type: "category",
          data: result.drawdown_series.map((p) => p.date),
          axisLabel: { color: "var(--text-secondary)" },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            color: "var(--text-secondary)",
            formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
          },
          splitLine: { lineStyle: { color: "var(--border-subtle)" } },
        },
        series: [
          {
            name: "回撤",
            type: "line",
            showSymbol: false,
            data: result.drawdown_series.map((p) => p.drawdown),
            lineStyle: { color: "var(--status-error)" },
            areaStyle: { color: "var(--status-error)", opacity: 0.15 },
          },
        ],
      }
    : null;

  const annualReturnsRows = result
    ? Object.entries(result.annual_returns).map(([year, value]) => ({
        year,
        return_pct: Math.abs(value) <= 1 ? value * 100 : value,
      }))
    : [];

  const isFraction = (v: number) => Math.abs(v) <= 1;

  return (
    <div>
      <PageHeader title="回測" subtitle="輸入投資組合與回測參數，驗證歷史資料中的表現。" />

      {/* Form */}
      <div className="mb-space-6 grid grid-cols-1 gap-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="lg:col-span-4">
          <label className="mb-space-1 block text-small text-text-secondary">選擇已存組合（可選）</label>
          <select
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value="">不使用已存組合（手動輸入 ETF 與權重）</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {!portfolioId && (
          <>
            <div className="lg:col-span-2">
              <label className="mb-space-1 block text-small text-text-secondary">ETF 代號（逗號分隔）</label>
              <input
                value={symbolsText}
                onChange={(e) => setSymbolsText(e.target.value)}
                className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
              />
            </div>
            <div className="lg:col-span-2">
              <label className="mb-space-1 block text-small text-text-secondary">權重（逗號分隔，加總為100）</label>
              <input
                value={weightsText}
                onChange={(e) => setWeightsText(e.target.value)}
                className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
              />
            </div>
          </>
        )}

        <div>
          <label className="mb-space-1 block text-small text-text-secondary">起始日期</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">結束日期</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">初始投入金額</label>
          <input
            type="number"
            value={initialAmount}
            onChange={(e) => setInitialAmount(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">每月投入金額</label>
          <input
            type="number"
            value={monthlyContribution}
            onChange={(e) => setMonthlyContribution(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-space-1 block text-small text-text-secondary">再平衡頻率</label>
          <select
            value={rebalanceFrequency}
            onChange={(e) => setRebalanceFrequency(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          >
            {REBALANCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">交易成本率</label>
          <input
            type="number"
            step="0.0001"
            value={transactionCostRate}
            onChange={(e) => setTransactionCostRate(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-space-2 text-body text-text-primary">
            <input
              type="checkbox"
              checked={dividendReinvest}
              onChange={(e) => setDividendReinvest(e.target.checked)}
            />
            配息再投入
          </label>
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSubmit}
            className="w-full rounded-sm bg-accent-primary px-space-4 py-2 text-body text-white transition-colors hover:bg-accent-primary-hover"
          >
            執行回測
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-3 text-small text-text-secondary">
        回測結果不代表未來績效，僅供研究分析。
      </div>

      {state === "loading" && <LoadingSkeleton variant="chart" />}
      {state === "error" && error && (
        <ErrorState code={error.code} message={error.message} retry={handleSubmit} />
      )}
      {state === "idle" && (
        <EmptyState title="尚未執行回測" description="請設定參數後點擊「執行回測」。" />
      )}

      {state === "ok" && result && (
        <>
          <div className="mb-space-4 flex justify-end">
            <button
              onClick={() => {
                try {
                  sessionStorage.setItem("ai:lastBacktest", JSON.stringify(result));
                } catch {
                  // ignore storage errors
                }
                router.push("/ai?context=backtest");
              }}
              className="rounded-sm border border-border-strong px-space-4 py-2 text-body text-text-primary transition-colors hover:bg-bg-surface-raised"
            >
              以 AI 解釋此結果
            </button>
          </div>

          <div className="mb-space-8 grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="最終資產價值"
              value={formatCurrencyTWD(result.final_value)}
              explanation="回測期間結束時，投資組合的總價值（含投入本金與累積收益）。"
            />
            <MetricCard
              label="累積投入金額"
              value={formatCurrencyTWD(result.total_contribution)}
              explanation="期間內投入的本金總額（初始投入加每月定期投入累計）。"
            />
            <MetricCard
              label="累積收益"
              value={formatCurrencyTWD(result.total_profit)}
              explanation="最終資產價值減去累積投入金額，代表此期間的總獲利（或虧損）。"
            />
            <MetricCard
              label="年化複合成長率 (CAGR)"
              value={formatPercent(result.cagr, { decimals: 2, isFraction: isFraction(result.cagr) })}
              explanation="衡量整段期間的年化報酬率，數字越高代表平均成長越快，但不代表未來會持續。"
            />
            {result.irr !== null && (
              <MetricCard
                label="內部報酬率 (IRR)"
                value={formatPercent(result.irr, { decimals: 2, isFraction: isFraction(result.irr) })}
                explanation="考慮每月投入時間點的內部報酬率，較能反映定期定額的實際報酬。"
              />
            )}
            <MetricCard
              label="最大回撤"
              value={formatPercent(result.max_drawdown, { decimals: 2, isFraction: isFraction(result.max_drawdown) })}
              grade={gradeDrawdown(result.max_drawdown)}
              explanation="歷史最大跌幅，數字越大代表曾經發生過的最大損失幅度越深（等級為前端粗略分類，非精確風險評估）。"
            />
            <MetricCard
              label="年化波動率"
              value={formatPercent(result.annualized_volatility, { decimals: 2, isFraction: isFraction(result.annualized_volatility) })}
              explanation="衡量資產價值波動的劇烈程度，數字越高代表價格起伏越大。"
            />
            <MetricCard
              label="夏普比率"
              value={formatNumber(result.sharpe_ratio, { decimals: 2 })}
              grade={gradeSharpe(result.sharpe_ratio)}
              explanation="每承擔一單位風險所獲得的超額報酬，數字越高代表風險調整後表現越好（等級為前端粗略分類）。"
            />
          </div>

          <div className="mb-space-8 grid grid-cols-1 gap-space-4 lg:grid-cols-2">
            <ChartCard
              title="資產曲線"
              explanation="顯示投資組合價值隨時間的變化。"
              dataDate={{ start: startDate, end: endDate }}
            >
              {assetChartOption && <ReactECharts option={assetChartOption} style={{ width: "100%", height: "320px" }} />}
            </ChartCard>
            <ChartCard
              title="回撤曲線"
              explanation="顯示投資組合相對於歷史高點的跌幅變化，數字越接近0代表越接近歷史新高。"
              dataDate={{ start: startDate, end: endDate }}
            >
              {drawdownChartOption && <ReactECharts option={drawdownChartOption} style={{ width: "100%", height: "320px" }} />}
            </ChartCard>
          </div>

          <div className="mb-space-8">
            <DataTable
              title="年度報酬"
              columns={ANNUAL_RETURNS_COLUMNS}
              rows={annualReturnsRows}
              emptyState={{ title: "無年度報酬資料" }}
            />
          </div>

          <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4 text-small text-text-secondary">
            <p className="mb-space-1 font-medium text-text-primary">風險提醒</p>
            <p>{result.disclaimer}</p>
          </div>

          <SourceFooter
            dataDate={endDate}
            disclaimer={result.disclaimer}
            confidenceLevel={null}
          />
        </>
      )}
    </div>
  );
}

export default function BacktestPage() {
  return (
    <Suspense fallback={<LoadingSkeleton variant="chart" />}>
      <BacktestContent />
    </Suspense>
  );
}
