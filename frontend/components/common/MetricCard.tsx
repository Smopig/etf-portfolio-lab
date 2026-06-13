import Badge, { BadgeTone } from "./Badge";
import { LoadingSkeleton } from "./States";

export interface MetricCardProps {
  label: string;
  value: string | number | null;
  unit?: string;
  grade?: { label: string; tone: BadgeTone };
  explanation: string;
  dataDate?: string | null;
  loading?: boolean;
}

export default function MetricCard({
  label,
  value,
  unit,
  grade,
  explanation,
  dataDate,
  loading,
}: MetricCardProps) {
  if (loading) {
    return <LoadingSkeleton variant="card" />;
  }

  const displayValue = value === null || value === undefined ? "—" : value;

  return (
    <div className="flex flex-col gap-space-2 rounded-md border border-border-subtle bg-bg-surface p-space-4">
      <div className="flex items-center justify-between gap-space-2">
        <span className="text-h3 text-text-primary">{label}</span>
        {grade && <Badge label={grade.label} tone={grade.tone} />}
      </div>
      <div className="font-mono-num text-display text-text-primary">
        {displayValue}
        {unit && value !== null && value !== undefined ? (
          <span className="ml-1 text-h3 text-text-secondary">{unit}</span>
        ) : null}
      </div>
      <p className="text-small text-text-secondary">{explanation}</p>
      {dataDate && <p className="text-small text-text-muted">資料日期：{dataDate}</p>}
    </div>
  );
}
