import Badge, { confidenceLevelTone } from "./Badge";
import { formatDate } from "@/lib/format";

export interface SourceFooterProps {
  sourceName?: string | null;
  sourceUrl?: string | null;
  dataDate?: string | null;
  confidenceLevel?: "高" | "中" | "低" | null;
  disclaimer?: string;
}

export default function SourceFooter({
  sourceName,
  sourceUrl,
  dataDate,
  confidenceLevel,
  disclaimer,
}: SourceFooterProps) {
  return (
    <div className="mt-space-6 flex flex-col gap-space-2 border-t border-border-subtle pt-space-4 text-small text-text-muted">
      <div className="flex flex-wrap items-center gap-space-3">
        <span>
          資料來源：
          {sourceUrl ? (
            <a href={sourceUrl} target="_blank" rel="noreferrer" className="text-accent-primary hover:underline">
              {sourceName ?? "未提供"}
            </a>
          ) : (
            sourceName ?? "未提供"
          )}
        </span>
        <span>資料日期：{formatDate(dataDate)}</span>
        {confidenceLevel && (
          <span className="flex items-center gap-space-1">
            資料可信度：
            <Badge label={confidenceLevel} tone={confidenceLevelTone(confidenceLevel)} />
          </span>
        )}
      </div>
      {disclaimer && <p className="text-text-secondary">{disclaimer}</p>}
    </div>
  );
}
