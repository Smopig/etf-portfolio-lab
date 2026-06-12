import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

export default function ProjectionPage() {
  return (
    <div>
      <PageHeader title="財務推算" subtitle="依不同情境推算未來資產成長，並可進行目標倒推。" />
      <EmptyState title="建構中" description="財務推算功能將於後續批次提供。" />
    </div>
  );
}
