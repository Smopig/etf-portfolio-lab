import { EmptyState } from "@/components/common/States";
import type { BacktestResult, EtfListItem, Portfolio, ProjectionResult } from "@/lib/types";

export type ContextTab = "etf" | "portfolio" | "backtest" | "projection";

const TABS: { value: ContextTab; label: string }[] = [
  { value: "etf", label: "ETF" },
  { value: "portfolio", label: "Portfolio" },
  { value: "backtest", label: "回測結果" },
  { value: "projection", label: "推算結果" },
];

export interface ContextPickerProps {
  tab: ContextTab;
  onTabChange: (tab: ContextTab) => void;
  disabled?: boolean;

  etfs: EtfListItem[];
  etfSymbol: string;
  onEtfSymbolChange: (symbol: string) => void;

  portfolios: Portfolio[];
  portfolioId: string;
  onPortfolioIdChange: (id: string) => void;
  portfolioError?: string | null;

  backtestResult: BacktestResult | null;
  projectionResult: ProjectionResult | null;
}

export default function ContextPicker({
  tab,
  onTabChange,
  disabled,
  etfs,
  etfSymbol,
  onEtfSymbolChange,
  portfolios,
  portfolioId,
  onPortfolioIdChange,
  portfolioError,
  backtestResult,
  projectionResult,
}: ContextPickerProps) {
  return (
    <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
      {/* Tabs: horizontal on sm+, select on mobile */}
      <div className="mb-space-4 hidden gap-space-2 sm:flex">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => onTabChange(t.value)}
            disabled={disabled}
            className={`rounded-sm px-space-3 py-1 text-body transition-colors ${
              tab === t.value
                ? "bg-accent-primary text-white"
                : "border border-border-subtle text-text-secondary hover:bg-bg-surface-raised"
            } disabled:opacity-50`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="mb-space-4 sm:hidden">
        <label className="mb-space-1 block text-small text-text-secondary">分析情境</label>
        <select
          value={tab}
          onChange={(e) => onTabChange(e.target.value as ContextTab)}
          disabled={disabled}
          className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
        >
          {TABS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {tab === "etf" && (
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">選擇 ETF</label>
          <select
            value={etfSymbol}
            onChange={(e) => onEtfSymbolChange(e.target.value)}
            disabled={disabled}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value="">請選擇</option>
            {etfs.map((e) => (
              <option key={e.symbol} value={e.symbol}>
                {e.symbol} {e.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {tab === "portfolio" && (
        <div>
          <label className="mb-space-1 block text-small text-text-secondary">選擇投資組合</label>
          <select
            value={portfolioId}
            onChange={(e) => onPortfolioIdChange(e.target.value)}
            disabled={disabled}
            className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value="">請選擇</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {portfolioError && <p className="mt-space-1 text-small text-status-error">{portfolioError}</p>}
        </div>
      )}

      {tab === "backtest" && (
        <div>
          {backtestResult ? (
            <p className="text-body text-text-secondary">
              將使用本次 session 中最近一次的回測結果進行分析。
            </p>
          ) : (
            <EmptyState
              title="尚未有可分析的回測結果"
              description="請先至「回測」頁執行一次計算，並點擊「以 AI 解釋此結果」。"
              actionLabel="前往回測頁"
              actionHref="/backtest"
            />
          )}
        </div>
      )}

      {tab === "projection" && (
        <div>
          {projectionResult ? (
            <p className="text-body text-text-secondary">
              將使用本次 session 中最近一次的推算結果進行分析。
            </p>
          ) : (
            <EmptyState
              title="尚未有可分析的推算結果"
              description="請先至「資產推算」頁執行一次計算，並點擊「以 AI 解釋此結果」。"
              actionLabel="前往資產推算頁"
              actionHref="/projection"
            />
          )}
        </div>
      )}
    </div>
  );
}
