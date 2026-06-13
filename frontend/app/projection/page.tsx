"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import MetricCard from "@/components/common/MetricCard";
import ChartCard from "@/components/common/ChartCard";
import SourceFooter from "@/components/common/SourceFooter";
import Badge from "@/components/common/Badge";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState, ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import { runProjection, projectionScenarios, goalSeek } from "@/lib/api";
import type {
  ProjectionRequestPayload,
  ProjectionResult,
  ScenarioRequestPayload,
  ScenarioResponse,
  GoalSeekRequestPayload,
  GoalSeekResult,
} from "@/lib/types";
import { formatCurrencyTWD, formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

type FetchState = "idle" | "loading" | "ok" | "error";

const SCENARIO_COLUMNS: Column[] = [
  { key: "scenario_name", label: "情境", sortable: true },
  { key: "annual_return_rate_pct", label: "假設年化報酬率", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "final_value", label: "最終資產", format: "currency", align: "right", sortable: true },
  { key: "total_profit", label: "累積收益", format: "currency", align: "right", sortable: true },
  { key: "target_achieved_label", label: "達標狀態", sortable: true },
];

const SOLVE_FOR_OPTIONS: { value: GoalSeekRequestPayload["solve_for"]; label: string }[] = [
  { value: "years", label: "投資年限" },
  { value: "monthly_contribution", label: "每月投入金額" },
  { value: "annual_return", label: "年化報酬率" },
];

export default function ProjectionPage() {
  const router = useRouter();
  // --- 共用表單欄位 ---
  const [initialAmount, setInitialAmount] = useState("100000");
  const [monthlyContribution, setMonthlyContribution] = useState("5000");
  const [years, setYears] = useState("20");
  const [targetAmount, setTargetAmount] = useState("");

  // --- 單一情境 ---
  const [annualReturnRate, setAnnualReturnRate] = useState("6");
  const [singleState, setSingleState] = useState<FetchState>("idle");
  const [singleError, setSingleError] = useState<{ code: string; message: string } | null>(null);
  const [singleResult, setSingleResult] = useState<ProjectionResult | null>(null);

  // --- 情境比較 ---
  const [scenarioState, setScenarioState] = useState<FetchState>("idle");
  const [scenarioError, setScenarioError] = useState<{ code: string; message: string } | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResponse | null>(null);

  // --- 目標倒推 ---
  const [solveFor, setSolveFor] = useState<GoalSeekRequestPayload["solve_for"]>("years");
  const [goalTargetAmount, setGoalTargetAmount] = useState("3000000");
  const [goalState, setGoalState] = useState<FetchState>("idle");
  const [goalError, setGoalError] = useState<{ code: string; message: string } | null>(null);
  const [goalResult, setGoalResult] = useState<GoalSeekResult | null>(null);

  function handleSingleSubmit() {
    const payload: ProjectionRequestPayload = {
      initial_amount: Number(initialAmount) || 0,
      monthly_contribution: Number(monthlyContribution) || 0,
      annual_return_rate: (Number(annualReturnRate) || 0) / 100,
      years: Number(years) || 0,
      target_amount: targetAmount ? Number(targetAmount) : null,
    };
    setSingleState("loading");
    setSingleError(null);
    runProjection(payload)
      .then((data) => {
        setSingleResult(data);
        setSingleState("ok");
      })
      .catch((e: unknown) => {
        setSingleError(errorToFriendlyMessage(e));
        setSingleState("error");
      });
  }

  function handleScenarioSubmit() {
    const payload: ScenarioRequestPayload = {
      initial_amount: Number(initialAmount) || 0,
      monthly_contribution: Number(monthlyContribution) || 0,
      years: Number(years) || 0,
      target_amount: targetAmount ? Number(targetAmount) : null,
    };
    setScenarioState("loading");
    setScenarioError(null);
    projectionScenarios(payload)
      .then((data) => {
        setScenarioResult(data);
        setScenarioState("ok");
      })
      .catch((e: unknown) => {
        setScenarioError(errorToFriendlyMessage(e));
        setScenarioState("error");
      });
  }

  function handleGoalSubmit() {
    const payload: GoalSeekRequestPayload = {
      solve_for: solveFor,
      initial_amount: Number(initialAmount) || 0,
      monthly_contribution: Number(monthlyContribution) || 0,
      annual_return_rate: (Number(annualReturnRate) || 0) / 100,
      years: Number(years) || 0,
      target_amount: Number(goalTargetAmount) || 0,
    };
    setGoalState("loading");
    setGoalError(null);
    goalSeek(payload)
      .then((data) => {
        setGoalResult(data);
        setGoalState("ok");
      })
      .catch((e: unknown) => {
        setGoalError(errorToFriendlyMessage(e));
        setGoalState("error");
      });
  }

  const singleChartOption = useMemo(() => {
    if (!singleResult) return null;
    return {
      backgroundColor: "transparent",
      grid: { left: 70, right: 24, top: 24, bottom: 40 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "var(--text-secondary)" } },
      xAxis: {
        type: "category",
        data: singleResult.yearly_series.map((p) => `第${p.year}年`),
        axisLabel: { color: "var(--text-secondary)" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "var(--text-secondary)" },
        splitLine: { lineStyle: { color: "var(--border-subtle)" } },
      },
      series: [
        {
          name: "資產總值",
          type: "line",
          showSymbol: false,
          data: singleResult.yearly_series.map((p) => p.value),
          lineStyle: { color: "var(--series-1)" },
          areaStyle: { color: "var(--series-1)", opacity: 0.1 },
        },
        {
          name: "累積投入本金",
          type: "line",
          showSymbol: false,
          data: singleResult.yearly_series.map((p) => p.contributed),
          lineStyle: { color: "var(--series-2)", type: "dashed" },
        },
      ],
    };
  }, [singleResult]);

  const scenarioChartOption = useMemo(() => {
    if (!scenarioResult) return null;
    const entries = Object.entries(scenarioResult.scenarios);
    const colors = ["var(--series-3)", "var(--series-1)", "var(--series-4)"];
    const years_axis = entries[0]?.[1]?.yearly_series.map((p) => `第${p.year}年`) ?? [];
    return {
      backgroundColor: "transparent",
      grid: { left: 70, right: 24, top: 24, bottom: 40 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "var(--text-secondary)" } },
      xAxis: {
        type: "category",
        data: years_axis,
        axisLabel: { color: "var(--text-secondary)" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "var(--text-secondary)" },
        splitLine: { lineStyle: { color: "var(--border-subtle)" } },
      },
      series: entries.map(([key, scenario], i) => ({
        name: scenario.scenario_name ?? key,
        type: "line",
        showSymbol: false,
        data: scenario.yearly_series.map((p) => p.value),
        lineStyle: { color: colors[i % colors.length] },
      })),
    };
  }, [scenarioResult]);

  const scenarioRows = scenarioResult
    ? Object.entries(scenarioResult.scenarios).map(([key, s]) => ({
        scenario_name: s.scenario_name ?? key,
        annual_return_rate_pct: s.annual_return_rate,
        final_value: s.final_value,
        total_profit: s.total_profit,
        target_achieved_label: s.target_achieved === null ? "—" : s.target_achieved ? "已達標" : "未達標",
      }))
    : [];

  return (
    <div>
      <PageHeader title="資產推算" subtitle="估算未來資產成長與目標可行性，所有結果皆為假設報酬率下的模擬數字。" />

      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-3 text-small text-text-secondary">
        未來模擬基於假設報酬率，不代表保證收益，僅供研究分析。
      </div>

      {/* 共用表單 */}
      <div className="mb-space-6 grid grid-cols-1 gap-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-4 sm:grid-cols-2 lg:grid-cols-4">
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
          <label className="mb-space-1 block text-small text-text-secondary">投資年限（年）</label>
          <input
            type="number"
            value={years}
            onChange={(e) => setYears(e.target.value)}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">目標金額（可選）</label>
          <input
            type="number"
            value={targetAmount}
            onChange={(e) => setTargetAmount(e.target.value)}
            placeholder="不填則不檢查達標"
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          />
        </div>
      </div>

      {/* 單一情境推算 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">單一情境推算</h2>
        <div className="mb-space-4 flex flex-wrap items-end gap-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-4">
          <div>
            <label className="mb-space-1 block text-small text-text-secondary">自訂年化報酬率（%）</label>
            <input
              type="number"
              step="0.1"
              value={annualReturnRate}
              onChange={(e) => setAnnualReturnRate(e.target.value)}
              className="w-40 rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            />
          </div>
          <button
            onClick={handleSingleSubmit}
            className="rounded-sm bg-accent-primary px-space-4 py-2 text-body text-white transition-colors hover:bg-accent-primary-hover"
          >
            推算
          </button>
        </div>

        {singleState === "idle" && <EmptyState title="尚未推算" description="設定參數後點擊「推算」。" />}
        {singleState === "loading" && <LoadingSkeleton variant="chart" />}
        {singleState === "error" && singleError && (
          <ErrorState code={singleError.code} message={singleError.message} retry={handleSingleSubmit} />
        )}
        {singleState === "ok" && singleResult && (
          <>
            <div className="mb-space-4 flex justify-end">
              <button
                onClick={() => {
                  try {
                    sessionStorage.setItem("ai:lastProjection", JSON.stringify(singleResult));
                  } catch {
                    // ignore storage errors
                  }
                  router.push("/ai?context=projection");
                }}
                className="rounded-sm border border-border-strong px-space-4 py-2 text-body text-text-primary transition-colors hover:bg-bg-surface-raised"
              >
                以 AI 解釋此結果
              </button>
            </div>

            <div className="mb-space-4 grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="最終資產"
                value={formatCurrencyTWD(singleResult.final_value)}
                explanation="投資年限結束時的資產總值（假設報酬率下的模擬結果，非保證）。"
              />
              <MetricCard
                label="累積投入本金"
                value={formatCurrencyTWD(singleResult.total_contribution)}
                explanation="初始投入加每月定期投入的累計金額。"
              />
              <MetricCard
                label="累積收益"
                value={formatCurrencyTWD(singleResult.total_profit)}
                explanation="最終資產減去累積投入本金，代表模擬期間的總收益。"
              />
              <MetricCard
                label="達標狀態"
                value={singleResult.target_achieved === null ? "未設定目標" : singleResult.target_achieved ? "已達標" : "未達標"}
                grade={
                  singleResult.target_achieved === null
                    ? undefined
                    : singleResult.target_achieved
                    ? { label: "達標", tone: "success" }
                    : { label: "未達標", tone: "warning" }
                }
                explanation="是否在投資年限內，資產達到所設定的目標金額。"
              />
            </div>
            <ChartCard title="未來資產曲線" explanation="顯示資產總值（含收益）與累積投入本金隨時間的變化。">
              {singleChartOption && <ReactECharts option={singleChartOption} style={{ width: "100%", height: "320px" }} />}
            </ChartCard>
            <div className="mt-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-3 text-small text-text-secondary">
              {singleResult.disclaimer}
            </div>
          </>
        )}
      </div>

      {/* 情境比較 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">情境比較（保守 / 中性 / 樂觀）</h2>
        <div className="mb-space-4">
          <button
            onClick={handleScenarioSubmit}
            className="rounded-sm bg-accent-primary px-space-4 py-2 text-body text-white transition-colors hover:bg-accent-primary-hover"
          >
            比較三種情境
          </button>
        </div>

        {scenarioState === "idle" && <EmptyState title="尚未比較" description="點擊「比較三種情境」以查看保守／中性／樂觀三種假設報酬率下的結果。" />}
        {scenarioState === "loading" && <LoadingSkeleton variant="chart" />}
        {scenarioState === "error" && scenarioError && (
          <ErrorState code={scenarioError.code} message={scenarioError.message} retry={handleScenarioSubmit} />
        )}
        {scenarioState === "ok" && scenarioResult && (
          <>
            <ChartCard title="三情境資產曲線比較" explanation="分別以保守（4%）、中性（6%）、樂觀（8%）年化報酬率推算未來資產，僅為假設情境，非保證收益。">
              {scenarioChartOption && <ReactECharts option={scenarioChartOption} style={{ width: "100%", height: "320px" }} />}
            </ChartCard>
            <div className="mt-space-4">
              <DataTable columns={SCENARIO_COLUMNS} rows={scenarioRows} emptyState={{ title: "無情境資料" }} />
            </div>
            <div className="mt-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-3 text-small text-text-secondary">
              {scenarioResult.disclaimer}
            </div>
          </>
        )}
      </div>

      {/* 目標倒推 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">目標倒推</h2>
        <div className="mb-space-4 grid grid-cols-1 gap-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-space-1 block text-small text-text-secondary">倒推項目</label>
            <select
              value={solveFor}
              onChange={(e) => setSolveFor(e.target.value as GoalSeekRequestPayload["solve_for"])}
              className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              {SOLVE_FOR_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-space-1 block text-small text-text-secondary">目標金額</label>
            <input
              type="number"
              value={goalTargetAmount}
              onChange={(e) => setGoalTargetAmount(e.target.value)}
              className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleGoalSubmit}
              className="w-full rounded-sm bg-accent-primary px-space-4 py-2 text-body text-white transition-colors hover:bg-accent-primary-hover"
            >
              倒推計算
            </button>
          </div>
        </div>
        <p className="mb-space-4 text-small text-text-muted">
          其餘條件沿用上方共同表單（初始投入、每月投入、投資年限、年化報酬率）；選擇要倒推的項目後，系統會計算達成目標金額所需的數值。
        </p>

        {goalState === "idle" && <EmptyState title="尚未計算" description="選擇倒推項目與目標金額後，點擊「倒推計算」。" />}
        {goalState === "loading" && <LoadingSkeleton variant="card" />}
        {goalState === "error" && goalError && (
          <ErrorState code={goalError.code} message={goalError.message} retry={handleGoalSubmit} />
        )}
        {goalState === "ok" && goalResult && (
          <>
            {!goalResult.achievable ? (
              <EmptyState
                title="目標在目前條件下無法達成"
                description={
                  goalResult.achievable_with_zero === false
                    ? "即使提高投入或延長年限，在合理範圍內仍可能無法達成此目標，建議調整目標金額或投入條件。"
                    : "在目前的參數設定下無法求得合理解，請嘗試調整目標金額、投入金額或年限。"
                }
              />
            ) : (
              <div className="grid grid-cols-1 gap-space-4 sm:grid-cols-2 lg:grid-cols-3">
                {solveFor === "years" && (
                  <MetricCard
                    label="所需投資年限"
                    value={goalResult.years !== null && goalResult.years !== undefined ? String(goalResult.years) : "—"}
                    unit="年"
                    explanation="在目前投入金額與年化報酬率假設下，達成目標金額所需的投資年限。"
                  />
                )}
                {solveFor === "monthly_contribution" && (
                  <MetricCard
                    label="所需每月投入金額"
                    value={formatCurrencyTWD(goalResult.monthly_contribution ?? null)}
                    explanation="在目前投資年限與年化報酬率假設下，達成目標金額所需的每月投入金額。"
                  />
                )}
                {solveFor === "annual_return" && (
                  <MetricCard
                    label="所需年化報酬率"
                    value={formatPercent(goalResult.annual_return_rate ?? null, { decimals: 2, isFraction: true })}
                    explanation="在目前投入金額與投資年限下，達成目標金額所需的年化報酬率（僅為理論數字，不代表可實際取得）。"
                  />
                )}
                <MetricCard
                  label="達成狀態"
                  value="可達成"
                  grade={{ label: "可行", tone: "success" }}
                  explanation="表示在合理範圍內，系統找到了可達成此目標金額的解。"
                />
              </div>
            )}
            <div className="mt-space-4 rounded-md border border-border-subtle bg-bg-surface p-space-3 text-small text-text-secondary">
              {goalResult.disclaimer}
            </div>
          </>
        )}
      </div>

      <SourceFooter
        sourceName="模擬資料（無外部資料來源）"
        dataDate={null}
        disclaimer="所有推算結果均為基於假設報酬率的模擬數字，不代表保證收益，亦非投資建議，僅供研究分析。"
      />

      <div className="mt-space-2">
        <Badge label="模擬資料" tone="neutral" />
      </div>
    </div>
  );
}
