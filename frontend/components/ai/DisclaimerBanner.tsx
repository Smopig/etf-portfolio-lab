export const STATIC_DISCLAIMER =
  "AI 分析僅基於系統現有資料，不提供買賣建議，回測與推算結果不代表未來績效。";

export interface DisclaimerBannerProps {
  text?: string;
}

export default function DisclaimerBanner({ text }: DisclaimerBannerProps) {
  return (
    <div className="mb-space-6 flex gap-space-3 rounded-md border-l-4 border-status-info bg-bg-surface-raised p-space-4 text-body text-text-secondary">
      <span aria-hidden className="text-status-info">
        ℹ
      </span>
      <p>{text ?? STATIC_DISCLAIMER}</p>
    </div>
  );
}
