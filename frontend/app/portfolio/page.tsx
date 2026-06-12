"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import WeightAllocator, { STARTER_TEMPLATES } from "@/components/portfolio/WeightAllocator";
import PortfolioAnalysis from "@/components/portfolio/PortfolioAnalysis";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState, ErrorState, errorToFriendlyMessage } from "@/components/common/States";
import {
  analyzePortfolioDraft,
  createPortfolio,
  deletePortfolio,
  listEtfs,
  listPortfolios,
} from "@/lib/api";
import type {
  EtfListItem,
  Portfolio,
  PortfolioAnalyzeResponse,
  PortfolioItem,
} from "@/lib/types";

type FetchState = "loading" | "ok" | "empty" | "error";

const PORTFOLIO_COLUMNS: Column[] = [
  { key: "name", label: "名稱", sortable: true },
  { key: "base_currency", label: "計價幣別", sortable: true },
  { key: "item_count", label: "持有 ETF 數", format: "number", align: "right", sortable: true, decimals: 0 },
];

export default function PortfolioPage() {
  const router = useRouter();

  const [etfList, setEtfList] = useState<EtfListItem[]>([]);
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [name, setName] = useState("");

  const [analysis, setAnalysis] = useState<PortfolioAnalyzeResponse | null>(null);
  const [analysisState, setAnalysisState] = useState<FetchState>("empty");
  const [analysisErr, setAnalysisErr] = useState<{ code: string; message: string } | null>(null);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfoliosState, setPortfoliosState] = useState<FetchState>("loading");

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    listEtfs().then(setEtfList).catch(() => setEtfList([]));
    loadPortfolios();
  }, []);

  function loadPortfolios() {
    setPortfoliosState("loading");
    listPortfolios()
      .then((data) => {
        setPortfolios(data);
        setPortfoliosState(data.length === 0 ? "empty" : "ok");
      })
      .catch(() => setPortfoliosState("error"));
  }

  function analyzeDraft() {
    if (items.length === 0) {
      setAnalysis(null);
      setAnalysisState("empty");
      return;
    }
    setAnalysisState("loading");
    analyzePortfolioDraft(items)
      .then((data) => {
        setAnalysis(data);
        setAnalysisState("ok");
      })
      .catch((e: unknown) => {
        setAnalysisErr(errorToFriendlyMessage(e));
        setAnalysisState("error");
      });
  }

  // Debounced auto-analyze on items change
  useEffect(() => {
    if (items.length === 0) {
      setAnalysis(null);
      setAnalysisState("empty");
      return;
    }
    const timer = setTimeout(() => {
      analyzeDraft();
    }, 500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(items)]);

  async function handleSave() {
    if (!name.trim()) {
      setSaveError("請輸入投資組合名稱");
      return;
    }
    if (items.length === 0) {
      setSaveError("請先加入至少一檔 ETF");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const portfolio = await createPortfolio({ name: name.trim(), items });
      router.push(`/portfolio/${portfolio.id}`);
    } catch (e: unknown) {
      setSaveError(errorToFriendlyMessage(e).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deletePortfolio(id);
      loadPortfolios();
    } catch {
      // ignore; list stays as-is
    }
  }

  const warningsList = Array.isArray(analysis?.warnings)
    ? analysis?.warnings ?? []
    : analysis?.warnings?.warnings ?? [];
  const disclaimer = Array.isArray(analysis?.warnings)
    ? undefined
    : analysis?.warnings?.disclaimer;

  const portfolioRows = portfolios.map((p) => ({
    ...p,
    item_count: p.items?.length ?? 0,
  }));

  return (
    <div>
      <PageHeader title="組合建構" subtitle="建立與管理投資組合，分析穿透曝險、集中度與重疊風險。" />

      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <label className="mb-space-2 block text-body text-text-primary">投資組合名稱</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：我的核心衛星組合"
          className="w-full max-w-md rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
        />
      </div>

      <div className="mb-space-6">
        <WeightAllocator items={items} onChange={setItems} etfList={etfList} validation={analysis?.validation ?? null} />
      </div>

      <div className="mb-space-8 flex flex-wrap items-center gap-space-2">
        <button
          onClick={analyzeDraft}
          disabled={items.length === 0}
          className="rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary hover:bg-bg-surface-raised disabled:opacity-50"
        >
          分析草稿
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-sm bg-accent-primary px-space-4 py-space-2 text-body text-white hover:bg-accent-primary-hover disabled:opacity-50"
        >
          {saving ? "儲存中..." : "儲存"}
        </button>
        {saveError && <span className="text-small text-status-error">{saveError}</span>}
      </div>

      {items.length === 0 && (
        <div className="mb-space-8">
          <EmptyState title="尚未加入任何 ETF" description="請先在上方權重配置中加入 ETF 並設定權重，即可分析穿透曝險。" />
        </div>
      )}

      {items.length > 0 && analysisState === "loading" && (
        <PortfolioAnalysis stockExposure={null} industryExposure={null} concentration={null} warnings={[]} loading />
      )}

      {items.length > 0 && analysisState === "error" && (
        <ErrorState code={analysisErr?.code} message={analysisErr?.message} retry={analyzeDraft} />
      )}

      {items.length > 0 && analysisState === "ok" && analysis && (
        <>
          {analysis.validation.status === "FAIL" && (
            <div className="mb-space-4 rounded-md border border-status-error/30 bg-bg-surface p-space-4">
              <p className="text-body text-status-error">驗證失敗：{analysis.validation.message}</p>
            </div>
          )}
          <PortfolioAnalysis
            stockExposure={analysis.stock_exposure}
            industryExposure={analysis.industry_exposure}
            concentration={analysis.concentration}
            warnings={warningsList}
            disclaimer={disclaimer}
          />
        </>
      )}

      <div className="mt-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">已儲存組合</h2>
        {portfoliosState === "loading" && <p className="text-body text-text-muted">載入中...</p>}
        {portfoliosState === "error" && <ErrorState retry={loadPortfolios} />}
        {portfoliosState === "empty" && <EmptyState title="尚未建立任何投資組合" />}
        {portfoliosState === "ok" && (
          <>
            <DataTable
              columns={PORTFOLIO_COLUMNS}
              rows={portfolioRows}
              onRowClick={(row: any) => router.push(`/portfolio/${row.id}`)}
            />
            <div className="mt-space-2 flex flex-wrap gap-space-2">
              {portfolios.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleDelete(p.id)}
                  className="rounded-sm border border-border-strong px-space-2 py-1 text-small text-text-muted hover:text-status-error hover:bg-bg-surface-raised"
                >
                  刪除「{p.name}」
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
