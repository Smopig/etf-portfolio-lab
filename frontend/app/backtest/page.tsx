import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function BacktestPage() {
  return (
    <div>
      <PageHeader title="回測" subtitle="輸入投資組合與回測參數，驗證歷史表現。" />
      <EmptyState title="建構中" description="回測功能將於後續批次提供。" />
    </div>
  );
}
