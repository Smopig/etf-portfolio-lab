import Badge from "@/components/common/Badge";

export interface ProviderBadgeProps {
  provider: string | null;
  model: string | null;
}

export default function ProviderBadge({ provider, model }: ProviderBadgeProps) {
  if (provider === "mock") {
    return (
      <Badge
        label="模擬模式（mock）"
        tone="neutral"
        tooltip="目前使用離線模擬回應，非即時 AI 模型"
      />
    );
  }
  if (provider === "claude") {
    return <Badge label={`AI 模型：${model ?? "claude"}`} tone="info" />;
  }
  return <Badge label="未呼叫 AI 模型" tone="neutral" />;
}
