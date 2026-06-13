import { formatDate } from "@/lib/format";

export interface CitationListProps {
  dataSources: string[];
  dataDates: string[];
}

export default function CitationList({ dataSources, dataDates }: CitationListProps) {
  if (dataSources.length === 0) {
    return (
      <p className="mt-space-4 text-small text-text-muted">本次分析無外部資料來源</p>
    );
  }

  const sameLength = dataSources.length === dataDates.length;

  return (
    <div className="mt-space-4 border-t border-border-subtle pt-space-3 text-small text-text-secondary">
      <p className="mb-space-1 font-medium text-text-primary">資料來源</p>
      {sameLength ? (
        <ul className="space-y-space-1">
          {dataSources.map((src, i) => (
            <li key={i}>
              <span aria-hidden>📄 </span>
              {src}
              {dataDates[i] && <span className="text-text-muted">（資料日期：{formatDate(dataDates[i])}）</span>}
            </li>
          ))}
        </ul>
      ) : (
        <>
          <ul className="mb-space-2 space-y-space-1">
            {dataSources.map((src, i) => (
              <li key={i}>
                <span aria-hidden>📄 </span>
                {src}
              </li>
            ))}
          </ul>
          {dataDates.length > 0 && (
            <>
              <p className="mb-space-1 font-medium text-text-primary">資料日期</p>
              <ul className="space-y-space-1">
                {dataDates.map((d, i) => (
                  <li key={i}>{formatDate(d)}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
