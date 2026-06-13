import { ApiError } from "@/lib/api";

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
}

export function EmptyState({ icon, title, description, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-space-2 rounded-md border border-border-subtle bg-bg-surface px-space-6 py-space-8 text-center">
      {icon && <div className="text-3xl text-text-muted">{icon}</div>}
      <p className="text-h3 text-text-primary">{title}</p>
      {description && <p className="text-body text-text-secondary">{description}</p>}
      {actionLabel && actionHref && (
        <a
          href={actionHref}
          className="mt-space-2 inline-flex items-center rounded-sm bg-accent-primary px-space-4 py-space-2 text-body text-white transition-colors hover:bg-accent-primary-hover"
        >
          {actionLabel}
        </a>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// LoadingSkeleton
// ---------------------------------------------------------------------------

export interface LoadingSkeletonProps {
  variant: "table" | "chart" | "card" | "text";
  rows?: number;
}

export function LoadingSkeleton({ variant, rows = 5 }: LoadingSkeletonProps) {
  if (variant === "card") {
    return (
      <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <div className="mb-space-3 h-3 w-1/2 animate-pulse-subtle rounded-sm bg-bg-surface-raised" />
        <div className="h-6 w-3/4 animate-pulse-subtle rounded-sm bg-bg-surface-raised" />
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className="flex h-64 w-full items-center justify-center rounded-md border border-border-subtle bg-bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border-strong border-t-accent-primary" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="overflow-hidden rounded-md border border-border-subtle bg-bg-surface">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="border-b border-border-subtle p-space-3 last:border-b-0">
            <div className="h-3 w-full animate-pulse-subtle rounded-sm bg-bg-surface-raised" />
          </div>
        ))}
      </div>
    );
  }

  // text
  return (
    <div className="space-y-space-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-3 w-full animate-pulse-subtle rounded-sm bg-bg-surface-raised" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ErrorState — maps ApiError.code -> friendly zh-Hant message (05 §1)
// ---------------------------------------------------------------------------

export interface ErrorStateProps {
  code?: string;
  message?: string;
  retry?: () => void;
}

const ERROR_MESSAGES: Record<string, string> = {
  NOT_FOUND: "找不到資料，可能尚未匯入或代號輸入錯誤。",
  VALIDATION_ERROR: "輸入內容有誤，請檢查欄位後重試。",
  NOT_IMPLEMENTED: "此功能即將推出，敬請期待。",
  INTERNAL_ERROR: "系統發生錯誤，請稍後再試。",
  NETWORK_ERROR: "無法連線到伺服器，請確認後端服務是否啟動。",
};

export function errorToFriendlyMessage(err: unknown): { code: string; message: string } {
  if (err instanceof ApiError) {
    const friendly = ERROR_MESSAGES[err.code] ?? ERROR_MESSAGES.INTERNAL_ERROR;
    if (err.code === "VALIDATION_ERROR" && err.message) {
      if (/No price data for symbols|No common trading dates/i.test(err.message)) {
        return {
          code: err.code,
          message: "此組合的標的尚無價格資料，請先執行 scripts.fetch_all 抓取，或改選有價格的 ETF。",
        };
      }
      return { code: err.code, message: `${friendly}（${err.message}）` };
    }
    return { code: err.code, message: friendly };
  }
  return { code: "INTERNAL_ERROR", message: ERROR_MESSAGES.INTERNAL_ERROR };
}

export function ErrorState({ code, message, retry }: ErrorStateProps) {
  const friendly = code ? ERROR_MESSAGES[code] ?? ERROR_MESSAGES.INTERNAL_ERROR : message ?? ERROR_MESSAGES.INTERNAL_ERROR;
  const showRetry = code !== "NOT_IMPLEMENTED" && code !== "NOT_FOUND" && !!retry;

  return (
    <div className="flex flex-col items-center justify-center gap-space-2 rounded-md border border-status-error/30 bg-bg-surface px-space-6 py-space-8 text-center">
      <p className="text-h3 text-status-error">發生錯誤</p>
      <p className="text-body text-text-secondary">{friendly}</p>
      {showRetry && (
        <button
          onClick={retry}
          className="mt-space-2 inline-flex items-center rounded-sm border border-border-strong px-space-4 py-space-2 text-body text-text-primary transition-colors hover:bg-bg-surface-raised"
        >
          重試
        </button>
      )}
    </div>
  );
}
