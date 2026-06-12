import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function EtfDetailPage({ params }: { params: { symbol: string } }) {
  return (
    <div>
      <PageHeader
        title={`ETF 明細：${params.symbol}`}
        subtitle="查看策略、持股集中度、產業曝險與成分股重疊分析。"
      />
      <EmptyState title="建構中" description="ETF 詳情頁面將於後續批次提供。" />
    </div>
  );
}
