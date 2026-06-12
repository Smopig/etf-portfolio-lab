export type BadgeTone = "success" | "warning" | "error" | "info" | "neutral";

export interface BadgeProps {
  label: string;
  tone?: BadgeTone;
  tooltip?: string;
}

const toneClasses: Record<BadgeTone, string> = {
  success: "bg-[rgba(34,197,94,0.12)] text-status-success",
  warning: "bg-[rgba(245,158,11,0.12)] text-status-warning",
  error: "bg-[rgba(239,68,68,0.12)] text-status-error",
  info: "bg-[rgba(56,189,248,0.12)] text-status-info",
  neutral: "bg-[rgba(71,85,105,0.12)] text-text-secondary",
};

export default function Badge({ label, tone = "neutral", tooltip }: BadgeProps) {
  return (
    <span
      title={tooltip}
      className={`inline-flex items-center rounded-sm px-space-2 py-0.5 text-small font-medium leading-4 ${toneClasses[tone]}`}
    >
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Helpers for Badge taxonomy (02 §7)
// ---------------------------------------------------------------------------

export function confidenceLevelTone(level: string | null | undefined): BadgeTone {
  if (level === "高") return "success";
  if (level === "中") return "warning";
  if (level === "低") return "error";
  return "neutral";
}

export function overlapRatingTone(label: string | null | undefined): BadgeTone {
  switch (label) {
    case "極低重疊":
      return "success";
    case "低度重疊":
      return "info";
    case "中度重疊":
      return "warning";
    case "高度重疊":
      return "error";
    default:
      return "neutral";
  }
}
