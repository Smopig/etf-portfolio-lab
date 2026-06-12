import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function ComparePage() {
  return (
    <div>
      <PageHeader title="ETF 比較" subtitle="選擇多檔 ETF，比較成分股重疊度與產業曝險。" />
      <EmptyState title="建構中" description="ETF 比較功能將於後續批次提供。" />
    </div>
  );
}
