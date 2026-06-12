"use client";

import { useEffect, useState } from "react";
import { getHealth, API_BASE_URL } from "@/lib/api";

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
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-6 py-16">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          ETF Portfolio Lab
        </h1>
        <p className="mt-4 text-muted">
          ETF 研究分析工具：成分股、產業曝險、比較、投資組合與回測分析
        </p>
      </div>

      <div className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-lg">
        <h2 className="mb-3 text-sm font-medium text-muted">後端連線狀態</h2>

        {status === "loading" && (
          <div className="flex items-center gap-2 text-muted">
            <span className="h-2 w-2 animate-pulse rounded-full bg-muted" />
            <span>檢查連線中...</span>
          </div>
        )}

        {status === "ok" && (
          <div className="flex items-start gap-2">
            <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-green-500" />
            <div>
              <p className="font-medium text-green-400">連線正常</p>
              <p className="mt-1 break-all text-xs text-muted">{detail}</p>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex items-start gap-2">
            <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-red-500" />
            <div>
              <p className="font-medium text-red-400">無法連線後端</p>
              <p className="mt-1 break-all text-xs text-muted">{detail}</p>
              <p className="mt-2 text-xs text-muted">
                API 位址：{API_BASE_URL}
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
