"use client";

import { useEffect, useState } from "react";
import { getHealth, API_BASE_URL } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/States";

type Status = "loading" | "ok" | "error";

export default function HomePage() {
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((res) => {
        if (!mounted) return;
        setStatus("ok");
        setDetail(JSON.stringify(res));
      })
      .catch((err) => {
        if (!mounted) return;
        setStatus("error");
        setDetail(err instanceof Error ? err.message : String(err));
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div>
      <PageHeader title="研究入口" subtitle="ETF 研究分析工具：成分股、產業曝險、比較、投資組合與回測分析" />

      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <h2 className="mb-space-3 text-h3 text-text-secondary">後端連線狀態</h2>

        {status === "loading" && (
          <div className="flex items-center gap-space-2 text-text-muted">
            <span className="h-2 w-2 animate-pulse rounded-full bg-text-muted" />
            <span>檢查連線中...</span>
          </div>
        )}

        {status === "ok" && (
          <div className="flex items-start gap-space-2">
            <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-status-success" />
            <div>
              <p className="font-medium text-status-success">連線正常</p>
              <p className="mt-1 break-all text-small text-text-muted">{detail}</p>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex items-start gap-space-2">
            <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-status-error" />
            <div>
              <p className="font-medium text-status-error">無法連線後端</p>
              <p className="mt-1 break-all text-small text-text-muted">{detail}</p>
              <p className="mt-space-2 text-small text-text-muted">API 位址：{API_BASE_URL}</p>
            </div>
          </div>
        )}
      </div>

      <EmptyState
        title="Dashboard 建構中"
        description="本頁將顯示 ETF 總覽、排行卡與資料品質警告（Phase 11 後續批次）。"
      />
    </div>
  );
}
