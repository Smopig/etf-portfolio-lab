"use client";

import Badge, { BadgeTone } from "@/components/common/Badge";
import type { EtfListItem, PortfolioItem, ValidationResult } from "@/lib/types";
import { formatPercent } from "@/lib/format";

export interface PortfolioTemplate {
  name: string;
  description: string;
  items: PortfolioItem[];
}

// 前端硬編碼的建議起點範本（後端尚無範本資料表，見 04_PAGE_SPECS §4 Backend gap #1）
export const STARTER_TEMPLATES: PortfolioTemplate[] = [
  {
    name: "市值核心 0050 / 006208",
    description: "0050 60% + 006208 40%（建議起點，請自行確認成分）",
    items: [
      { etf_symbol: "0050", target_weight: 60 },
      { etf_symbol: "006208", target_weight: 40 },
    ],
  },
  {
    name: "核心衛星：0050 + 00878",
    description: "0050 70% + 00878 30%（建議起點，請自行確認成分）",
    items: [
      { etf_symbol: "0050", target_weight: 70 },
      { etf_symbol: "00878", target_weight: 30 },
    ],
  },
  {
    name: "三檔均衡：0050 / 0056 / 00878",
    description: "0050 40% + 0056 30% + 00878 30%（建議起點，請自行確認成分）",
    items: [
      { etf_symbol: "0050", target_weight: 40 },
      { etf_symbol: "0056", target_weight: 30 },
      { etf_symbol: "00878", target_weight: 30 },
    ],
  },
];

function validationTone(status: ValidationResult["status"] | undefined): BadgeTone {
  if (status === "PASS") return "success";
  if (status === "WARN") return "warning";
  if (status === "FAIL") return "error";
  return "neutral";
}

export interface WeightAllocatorProps {
  items: PortfolioItem[];
  onChange: (items: PortfolioItem[]) => void;
  etfList: EtfListItem[];
  validation?: ValidationResult | null;
}

export default function WeightAllocator({ items, onChange, etfList, validation }: WeightAllocatorProps) {
  const weightSum = items.reduce((acc, it) => acc + (Number.isFinite(it.target_weight) ? it.target_weight : 0), 0);

  function updateItem(index: number, patch: Partial<PortfolioItem>) {
    const next = items.map((it, i) => (i === index ? { ...it, ...patch } : it));
    onChange(next);
  }

  function removeItem(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  function addItem() {
    const used = new Set(items.map((it) => it.etf_symbol));
    const firstAvailable = etfList.find((e) => !used.has(e.symbol));
    onChange([
      ...items,
      { etf_symbol: firstAvailable?.symbol ?? "", target_weight: 0 },
    ]);
  }

  function applyTemplate(template: PortfolioTemplate) {
    onChange(template.items.map((it) => ({ ...it })));
  }

  return (
    <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
      <div className="mb-space-4 flex flex-wrap items-center justify-between gap-space-2">
        <h2 className="text-h2 text-text-primary">權重配置</h2>
        <div className="flex items-center gap-space-2">
          <label className="text-small text-text-muted">套用範本：</label>
          <select
            defaultValue=""
            onChange={(e) => {
              const tpl = STARTER_TEMPLATES.find((t) => t.name === e.target.value);
              if (tpl) applyTemplate(tpl);
              e.target.value = "";
            }}
            className="rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value="">選擇範本（建議起點）...</option>
            {STARTER_TEMPLATES.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="mb-space-3 text-small text-text-muted">
        範本為前端建議起點，並非後端提供的標準配置，請自行確認成分股與權重是否符合需求。
      </p>

      <div className="flex flex-col gap-space-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-space-2">
            <select
              value={item.etf_symbol}
              onChange={(e) => updateItem(i, { etf_symbol: e.target.value })}
              className="flex-1 rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              <option value="">選擇 ETF...</option>
              {etfList.map((e) => (
                <option key={e.symbol} value={e.symbol}>
                  {e.symbol} {e.name}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={item.target_weight}
              onChange={(e) => updateItem(i, { target_weight: Number(e.target.value) })}
              className="w-28 rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-right font-mono-num text-body text-text-primary focus:border-accent-primary focus:outline-none"
            />
            <span className="text-body text-text-muted">%</span>
            <button
              onClick={() => removeItem(i)}
              aria-label="移除"
              className="rounded-sm border border-border-strong px-space-2 py-1 text-body text-text-muted hover:text-status-error hover:bg-bg-surface-raised"
            >
              ×
            </button>
          </div>
        ))}
        {items.length === 0 && <p className="text-body text-text-muted">尚未加入任何 ETF</p>}
      </div>

      <button
        onClick={addItem}
        className="mt-space-3 rounded-sm border border-border-strong px-space-3 py-1 text-body text-text-primary hover:bg-bg-surface-raised"
      >
        + 新增 ETF
      </button>

      <div className="mt-space-4 flex flex-wrap items-center gap-space-2 border-t border-border-subtle pt-space-3">
        <span className="text-body text-text-primary">權重加總：{formatPercent(weightSum, { decimals: 2 })}</span>
        {validation && <Badge label={validation.status} tone={validationTone(validation.status)} />}
        {validation && <span className="text-small text-text-secondary">{validation.message}</span>}
      </div>
    </div>
  );
}
