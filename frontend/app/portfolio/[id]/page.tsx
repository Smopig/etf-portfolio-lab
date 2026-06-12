import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function PortfolioDetailPage({ params }: { params: { id: string } }) {
  return (
    <div>
      <PageHeader
        title={`投資組合詳情：#${params.id}`}
        subtitle="查看穿透曝險、集中度與警示。"
      />
      <EmptyState title="建構中" description="投資組合詳情頁面將於後續批次提供。" />
    </div>
  );
}
