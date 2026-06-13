"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export interface TopBarProps {
  lastUpdated?: string | null;
}

export default function TopBar({ lastUpdated }: TopBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const symbol = query.trim().toUpperCase();
    if (!symbol) return;
    router.push(`/etf/${encodeURIComponent(symbol)}`);
    setQuery("");
  }

  return (
    <header className="flex h-14 items-center justify-between gap-space-4 border-b border-border-subtle bg-bg-surface px-space-4">
      <div className="flex items-center gap-space-2">
        <span className="text-h3 font-semibold text-text-primary">ETF Portfolio Lab</span>
        <span className="hidden text-small text-text-muted sm:inline">研究與分析輔助工具</span>
      </div>

      <form onSubmit={handleSearch} className="flex-1 max-w-sm">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="輸入 ETF 代號，例如 0050"
          className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-3 py-1.5 text-body text-text-primary placeholder:text-text-muted focus:border-accent-primary focus:outline-none"
        />
      </form>

      <div className="text-small text-text-muted whitespace-nowrap">
        {lastUpdated ? `資料快照：${lastUpdated}` : "資料快照：—"}
      </div>
    </header>
  );
}
