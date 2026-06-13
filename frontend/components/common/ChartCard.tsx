import { ErrorState, LoadingSkeleton, EmptyState } from "./States";

export interface ChartCardProps {
  title: string;
  unit?: string;
  dataDate?: string | { start: string; end: string } | null;
  explanation: string;
  children?: React.ReactNode;
  loading?: boolean;
  empty?: boolean;
  error?: { code?: string; message?: string } | null;
  retry?: () => void;
}

function formatDataDate(dataDate: ChartCardProps["dataDate"]): string | null {
  if (!dataDate) return null;
  if (typeof dataDate === "string") return dataDate;
  return `${dataDate.start} ~ ${dataDate.end}`;
}

export default function ChartCard({
  title,
  unit,
  dataDate,
  explanation,
  children,
  loading,
  empty,
  error,
  retry,
}: ChartCardProps) {
  const dateLabel = formatDataDate(dataDate);

  return (
    <div className="flex flex-col gap-space-3 rounded-md border border-border-subtle bg-bg-surface p-space-4">
      <div className="flex items-start justify-between gap-space-2">
        <div>
          <h2 className="text-h2 text-text-primary">{title}</h2>
          {unit && <p className="text-small text-text-muted">單位：{unit}</p>}
        </div>
        {dateLabel && <span className="text-small text-text-muted">資料日期：{dateLabel}</span>}
      </div>

      <div className="min-h-[200px]">
        {loading ? (
          <LoadingSkeleton variant="chart" />
        ) : error ? (
          <ErrorState code={error.code} message={error.message} retry={retry} />
        ) : empty ? (
          <EmptyState title="尚無資料可顯示" />
        ) : (
          children
        )}
      </div>

      {!loading && !error && !empty && (
        <p className="text-small text-text-secondary">{explanation}</p>
      )}
    </div>
  );
}
