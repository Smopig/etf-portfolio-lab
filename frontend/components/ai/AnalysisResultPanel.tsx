import { EmptyState, LoadingSkeleton, ErrorState } from "@/components/common/States";
import ProviderBadge from "./ProviderBadge";
import CitationList from "./CitationList";
import DisclaimerBanner from "./DisclaimerBanner";
import SafetyNotice from "./SafetyNotice";
import InfoState from "./InfoState";
import type { AIAnalysisResponse } from "@/lib/types";

export interface AnalysisResultPanelProps {
  state: "idle" | "loading" | "ok" | "error";
  result: AIAnalysisResponse | null;
  error: { code: string; message: string } | null;
  onRetry?: () => void;
}

export default function AnalysisResultPanel({ state, result, error, onRetry }: AnalysisResultPanelProps) {
  if (state === "idle") {
    return (
      <EmptyState
        title="尚未開始分析"
        description="請於上方選擇分析對象（ETF / 投資組合 / 回測結果 / 推算結果），可選填問題後點擊「開始分析」"
      />
    );
  }

  if (state === "loading") {
    return (
      <div>
        <div className="mb-space-3 h-5 w-32 animate-pulse-subtle rounded-sm bg-bg-surface-raised" />
        <LoadingSkeleton variant="text" />
      </div>
    );
  }

  if (state === "error") {
    return <ErrorState code={error?.code} message={error?.message} retry={onRetry} />;
  }

  if (!result) return null;

  const isDataInsufficient = result.provider === null && result.analysis_text.startsWith("資料不足");

  return (
    <div>
      <div className="mb-space-3">
        <ProviderBadge provider={result.provider} model={result.model} />
      </div>

      {result.refused ? (
        <SafetyNotice />
      ) : isDataInsufficient ? (
        <InfoState text={result.analysis_text} />
      ) : (
        <div
          className="whitespace-pre-wrap text-body text-text-primary"
          style={{ lineHeight: 1.7 }}
        >
          {result.analysis_text.split(/\n{2,}/).map((para, i) => (
            <p key={i} className="mb-[1em] last:mb-0">
              {para}
            </p>
          ))}
        </div>
      )}

      {!result.refused && <CitationList dataSources={result.data_sources} dataDates={result.data_dates} />}

      <div className="mt-space-4">
        <DisclaimerBanner text={result.disclaimer} />
      </div>
    </div>
  );
}
