"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import Badge from "@/components/common/Badge";
import { EmptyState } from "@/components/common/States";
import SourceFooter from "@/components/common/SourceFooter";
import { listEtfs, listPortfolios } from "@/lib/api";
import type { EtfListItem, Portfolio } from "@/lib/types";

export default function AiAssistantPage() {
  const [etfs, setEtfs] = useState<EtfListItem[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [contextType, setContextType] = useState<"etf" | "portfolio">("etf");
  const [contextValue, setContextValue] = useState("");

  useEffect(() => {
    listEtfs().then(setEtfs).catch(() => setEtfs([]));
    listPortfolios().then(setPortfolios).catch(() => setPortfolios([]));
  }, []);

  return (
    <div>
      <PageHeader
        title="AI 助手"
        subtitle="基於系統資料解釋分析結果，協助理解 ETF 與投資組合的研究資訊。"
        actions={<Badge label="即將推出" tone="neutral" />}
      />

      {/* 說明區 */}
      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-4 text-body text-text-secondary">
        <p className="mb-space-2">
          AI 助手功能規劃於 Phase 13 開放。開放後，AI 將僅根據本系統內的資料（成分股、產業曝險、集中度、回測與推算結果等）回答問題，
          每則回覆都會附上「資料來源」與「資料日期」。
        </p>
        <p className="mb-space-2">
          為避免誤導，AI 助手<strong className="text-text-primary">不會提供買賣建議或進出場時點建議</strong>，
          回測或模擬相關的回答也會附帶「不代表未來績效」的提醒。AI 助手不會憑空猜測 ETF 成分股或產業占比等未在系統中的資料。
        </p>
        <p>目前後端 <code className="rounded-sm bg-bg-inset px-1">/api/ai/analyze-etf</code> 與 <code className="rounded-sm bg-bg-inset px-1">/api/ai/analyze-portfolio</code> 端點皆回傳 501（尚未實作）。</p>
      </div>

      {/* AIChatPanel (disabled) */}
      <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <h2 className="mb-space-4 text-h2 text-text-primary">AI 對話面板（預覽）</h2>

        <div className="mb-space-4 grid grid-cols-1 gap-space-4 sm:grid-cols-2">
          <div>
            <label className="mb-space-1 block text-small text-text-secondary">分析對象類型</label>
            <select
              value={contextType}
              onChange={(e) => {
                setContextType(e.target.value as "etf" | "portfolio");
                setContextValue("");
              }}
              className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              <option value="etf">ETF</option>
              <option value="portfolio">投資組合</option>
            </select>
          </div>
          <div>
            <label className="mb-space-1 block text-small text-text-secondary">
              {contextType === "etf" ? "選擇 ETF" : "選擇投資組合"}
            </label>
            <select
              value={contextValue}
              onChange={(e) => setContextValue(e.target.value)}
              className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              <option value="">請選擇</option>
              {contextType === "etf"
                ? etfs.map((e) => (
                    <option key={e.symbol} value={e.symbol}>
                      {e.symbol} {e.name}
                    </option>
                  ))
                : portfolios.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
            </select>
          </div>
        </div>
        <p className="mb-space-4 text-small text-text-muted">
          以上選擇將於 Phase 13 開放後，直接帶入 AI 分析請求的上下文，目前僅供預先設定，不會送出任何請求。
        </p>

        {/* 對話區 */}
        <div className="mb-space-4 rounded-md border border-border-subtle bg-bg-inset p-space-4">
          <EmptyState
            title="此功能尚未開放"
            description="目前呼叫後端 AI 分析端點會回傳 501（NOT_IMPLEMENTED）。AI 助手規劃於 Phase 13 開放，開放後將基於系統資料回答問題，並標示資料來源與日期，不提供買賣建議。"
          />
        </div>

        {/* 輸入框 */}
        <div className="flex gap-space-2">
          <input
            type="text"
            disabled
            placeholder="AI 分析功能即將推出"
            title="AI 分析功能規劃中（Phase 13），目前後端回應 501"
            className="flex-1 cursor-not-allowed rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-2 text-body text-text-muted"
          />
          <button
            disabled
            title="AI 分析功能規劃中（Phase 13），目前後端回應 501"
            className="cursor-not-allowed rounded-sm border border-border-subtle bg-bg-surface-raised px-space-4 py-2 text-body text-text-muted"
          >
            送出
          </button>
        </div>
      </div>

      <SourceFooter
        sourceName="ETF Portfolio Lab 系統資料"
        dataDate={null}
        disclaimer="AI 助手功能規劃中（Phase 13），目前不提供任何分析結果。開放後將僅基於系統資料回答，附資料來源與日期，且不提供買賣建議。"
      />
    </div>
  );
}
