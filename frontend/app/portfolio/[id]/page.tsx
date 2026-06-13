"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import PortfolioAnalysis from "@/components/portfolio/PortfolioAnalysis";
import SourceFooter from "@/components/common/SourceFooter";
import { ErrorState, errorToFriendlyMessage } from "@/components/common/States";
import {
  deletePortfolio,
  getPortfolio,
  getPortfolioConcentration,
  getPortfolioExposure,
  getPortfolioOverlapRisk,
  getPortfolioWarnings,
} from "@/lib/api";
import type {
  IndustryExposure,
  Portfolio,
  PortfolioConcentration,
  PortfolioOverlapRisk,
  PortfolioWarningsResponse,
  StockExposureResponse,
} from "@/lib/types";

type FetchState = "loading" | "ok" | "error";

export default function PortfolioDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const id = parseInt(params.id, 10);

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [stockExposure, setStockExposure] = useState<StockExposureResponse | null>(null);
  const [industryExposure, setIndustryExposure] = useState<IndustryExposure | null>(null);
  const [concentration, setConcentration] = useState<PortfolioConcentration | null>(null);
  const [warnings, setWarnings] = useState<PortfolioWarningsResponse | null>(null);
  const [overlapRisk, setOverlapRisk] = useState<PortfolioOverlapRisk | null>(null);

  const [state, setState] = useState<FetchState>("loading");
  const [err, setErr] = useState<{ code: string; message: string } | null>(null);

  function load() {
    setState("loading");
    Promise.all([
      getPortfolio(id),
      getPortfolioExposure(id),
      getPortfolioConcentration(id),
      getPortfolioWarnings(id),
      getPortfolioOverlapRisk(id),
    ])
      .then(([p, exposure, conc, warn, overlap]) => {
        setPortfolio(p);
        setStockExposure(exposure.stock_exposure);
        setIndustryExposure(exposure.industry_exposure);
        setConcentration(conc);
        setWarnings(warn);
        setOverlapRisk(overlap);
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
  }, [id]);

  async function handleDelete() {
    try {
      await deletePortfolio(id);
      router.push("/portfolio");
    } catch {
      // ignore
    }
  }

  if (state === "error") {
    return (
      <div>
        <PageHeader title="投資組合詳情" subtitle="查看穿透曝險、集中度與警示。" />
        <ErrorState code={err?.code} message={err?.message} retry={load} />
        <div className="mt-space-4">
          <Link href="/portfolio" className="text-body text-accent-primary hover:underline">
            返回投資組合列表
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={`投資組合：${portfolio?.name ?? "..."}`}
        subtitle="查看穿透曝險、集中度與重疊風險警示。"
        actions={
          <>
            <Link
              href={`/backtest?portfolio_id=${id}`}
              className="rounded-sm border border-border-strong px-space-3 py-1 text-body text-text-primary hover:bg-bg-surface-raised"
            >
              執行回測
            </Link>
            <Link
              href="/projection"
              className="rounded-sm border border-border-strong px-space-3 py-1 text-body text-text-primary hover:bg-bg-surface-raised"
            >
              推算
            </Link>
            <button
              onClick={handleDelete}
              className="rounded-sm border border-border-strong px-space-3 py-1 text-body text-text-muted hover:text-status-error hover:bg-bg-surface-raised"
            >
              刪除
            </button>
          </>
        }
      />

      <PortfolioAnalysis
        stockExposure={stockExposure}
        industryExposure={industryExposure}
        concentration={concentration}
        warnings={warnings?.warnings ?? []}
        disclaimer={warnings?.disclaimer}
        overlapRisk={overlapRisk as any}
        loading={state === "loading"}
      />

      <SourceFooter
        sourceName="ETF Portfolio Lab 系統資料"
        dataDate={industryExposure?.holding_date ?? null}
        disclaimer={warnings?.disclaimer ?? "本頁分析僅供研究參考，依各 ETF 最新成分股資料計算，不代表未來績效，亦非投資買賣建議。"}
      />
    </div>
  );
}
