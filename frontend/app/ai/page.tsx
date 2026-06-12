import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function AiAssistantPage() {
  return (
    <div>
      <PageHeader title="AI 助理" subtitle="基於系統資料提供研究說明與風險提醒，非投資建議。" />
      <EmptyState
        title="即將推出"
        description="AI 助理功能仰賴後端 /api/ai/analyze-etf、/api/ai/analyze-portfolio，目前回傳 501（尚未實作），敬請期待。"
      />
    </div>
  );
}
