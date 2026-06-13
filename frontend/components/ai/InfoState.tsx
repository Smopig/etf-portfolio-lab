export interface InfoStateProps {
  text: string;
}

export default function InfoState({ text }: InfoStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-space-2 rounded-md border border-status-info/30 bg-[rgba(56,189,248,0.06)] px-space-6 py-space-8 text-center">
      <p className="text-h3 text-status-info">資料不足</p>
      <p className="whitespace-pre-wrap text-body text-text-secondary">{text}</p>
      <a
        href="/data-sources"
        className="mt-space-2 inline-flex items-center rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary transition-colors hover:bg-bg-surface-raised"
      >
        前往資料來源頁確認
      </a>
    </div>
  );
}
