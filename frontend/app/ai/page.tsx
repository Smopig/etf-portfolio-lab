"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import { LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import DisclaimerBanner from "@/components/ai/DisclaimerBanner";
import ContextPicker, { ContextTab } from "@/components/ai/ContextPicker";
import QuestionInput from "@/components/ai/QuestionInput";
import AnalysisResultPanel from "@/components/ai/AnalysisResultPanel";
import { analyzeEtf, analyzePortfolio, explainBacktest, explainProjection, listEtfs, listPortfolios } from "@/lib/api";
import type { AIAnalysisResponse, BacktestResult, EtfListItem, Portfolio, ProjectionResult } from "@/lib/types";

type FetchState = "idle" | "loading" | "ok" | "error";

function AiAssistantContent() {
  const searchParams = useSearchParams();

  const [etfs, setEtfs] = useState<EtfListItem[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);

  const [tab, setTab] = useState<ContextTab>("etf");
  const [etfSymbol, setEtfSymbol] = useState("");
  const [portfolioId, setPortfolioId] = useState("");
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");

  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [projectionResult, setProjectionResult] = useState<ProjectionResult | null>(null);

  const [state, setState] = useState<FetchState>("idle");
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [result, setResult] = useState<AIAnalysisResponse | null>(null);

  useEffect(() => {
    listEtfs().then(setEtfs).catch(() => setEtfs([]));
    listPortfolios().then(setPortfolios).catch(() => setPortfolios([]));

    try {
      const bt = sessionStorage.getItem("ai:lastBacktest");
      if (bt) setBacktestResult(JSON.parse(bt));
      const pj = sessionStorage.getItem("ai:lastProjection");
      if (pj) setProjectionResult(JSON.parse(pj));
    } catch {
      // ignore malformed sessionStorage content
    }

    const ctx = searchParams.get("context");
    if (ctx === "backtest" || ctx === "projection" || ctx === "portfolio" || ctx === "etf") {
      setTab(ctx);
    }
  }, [searchParams]);

  function handleSubmit() {
    if (tab === "portfolio" && !portfolioId) {
      setPortfolioError("請選擇一個投資組合");
      return;
    }
    setPortfolioError(null);

    let request: Promise<AIAnalysisResponse> | null = null;
    if (tab === "etf") {
      if (!etfSymbol) return;
      request = analyzeEtf(etfSymbol, question || undefined);
    } else if (tab === "portfolio") {
      request = analyzePortfolio({ portfolioId: Number(portfolioId) }, question || undefined);
    } else if (tab === "backtest") {
      if (!backtestResult) return;
      request = explainBacktest(backtestResult, question || undefined);
    } else if (tab === "projection") {
      if (!projectionResult) return;
      request = explainProjection(projectionResult, question || undefined);
    }
    if (!request) return;

    setState("loading");
    setError(null);
    request
      .then((data) => {
        setResult(data);
        setState("ok");
      })
      .catch((e: unknown) => {
        setError(errorToFriendlyMessage(e));
        setState("error");
      });
  }

  const canSubmit =
    state !== "loading" &&
    ((tab === "etf" && !!etfSymbol) ||
      (tab === "portfolio" && !!portfolioId) ||
      (tab === "backtest" && !!backtestResult) ||
      (tab === "projection" && !!projectionResult));

  return (
    <div>
      <PageHeader
        title="AI 助手"
        subtitle="針對 ETF、投資組合、回測或推算結果，取得基於系統資料的研究說明（非投資建議）"
      />

      <DisclaimerBanner />

      <div className="grid grid-cols-1 gap-space-6 lg:grid-cols-[35%_1fr]">
        {/* 左欄 */}
        <div className="flex flex-col gap-space-4">
          <ContextPicker
            tab={tab}
            onTabChange={(t) => {
              setTab(t);
              setPortfolioError(null);
            }}
            disabled={state === "loading"}
            etfs={etfs}
            etfSymbol={etfSymbol}
            onEtfSymbolChange={setEtfSymbol}
            portfolios={portfolios}
            portfolioId={portfolioId}
            onPortfolioIdChange={(id) => {
              setPortfolioId(id);
              setPortfolioError(null);
            }}
            portfolioError={portfolioError}
            backtestResult={backtestResult}
            projectionResult={projectionResult}
          />

          <QuestionInput value={question} onChange={setQuestion} disabled={state === "loading"} />

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="rounded-sm bg-accent-primary px-space-4 py-2 text-body text-white transition-colors hover:bg-accent-primary-hover disabled:opacity-50"
          >
            {state === "loading" ? "分析中..." : "開始分析"}
          </button>
        </div>

        {/* 右欄 */}
        <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
          <AnalysisResultPanel state={state} result={result} error={error} onRetry={handleSubmit} />
        </div>
      </div>
    </div>
  );
}

export default function AiAssistantPage() {
  return (
    <Suspense fallback={<LoadingSkeleton variant="card" />}>
      <AiAssistantContent />
    </Suspense>
  );
}
