import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function PortfolioPage() {
  return (
    <div>
      <PageHeader title="組合建構" subtitle="建立與管理投資組合，分析穿透曝險、集中度與重疊風險。" />
      <EmptyState title="建構中" description="投資組合建構功能將於後續批次提供。" />
    </div>
  );
}
