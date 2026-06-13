export default function SafetyNotice() {
  return (
    <div className="flex flex-col items-center justify-center gap-space-2 rounded-md border border-status-warning/30 bg-[rgba(245,158,11,0.08)] px-space-6 py-space-8 text-center">
      <p className="text-h3 text-status-warning">內容未顯示</p>
      <p className="text-body text-text-secondary">
        此次回應已被安全機制標記，內容未顯示。您可調整問題後重新嘗試。
      </p>
    </div>
  );
}
