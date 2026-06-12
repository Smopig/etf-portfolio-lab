import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function DataSourcesPage() {
  return (
    <div>
      <PageHeader title="資料來源" subtitle="檢視資料來源清單與資料品質檢查紀錄。" />
      <EmptyState title="建構中" description="資料來源頁面將於後續批次提供。" />
    </div>
  );
}
