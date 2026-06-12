import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function EtfListPage() {
  return (
    <div>
      <PageHeader title="ETF 明細" subtitle="瀏覽所有已匯入的 ETF，點選代號可查看詳細研究頁面。" />
      <EmptyState title="建構中" description="ETF 列表與搜尋功能將於後續批次提供。" />
    </div>
  );
}
