"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PageHeader from "@/components/layout/PageHeader";
import Badge, { overlapRatingTone } from "@/components/common/Badge";
import MetricCard from "@/components/common/MetricCard";
import DataTable, { Column } from "@/components/tables/DataTable";
import { EmptyState, ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import SourceFooter from "@/components/common/SourceFooter";
import OverlapHeatmap from "@/components/charts/OverlapHeatmap";
import { compareEtfs, getOverlap, listEtfs } from "@/lib/api";
import type { EtfListItem, MultiOverlap, OverlapResponse } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/format";

type FetchState = "loading" | "ok" | "empty" | "error";

const PAIR_COLUMNS: Column[] = [
  { key: "a", label: "ETF A", sortable: true },
  { key: "b", label: "ETF B", sortable: true },
  { key: "weighted_overlap_pct", label: "加權重疊度", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "overlap_rating_label", label: "重疊程度", sortable: true },
  { key: "jaccard", label: "Jaccard", format: "number", align: "right", sortable: true, decimals: 3 },
  { key: "overlap_count", label: "共同持股數", format: "number", align: "right", sortable: true, decimals: 0 },
];

const COMMON_TOP10_COLUMNS: Column[] = [
  { key: "asset_symbol", label: "個股代號", sortable: true },
  { key: "asset_name", label: "個股名稱", sortable: true },
  { key: "weight_a_pct", label: "A 權重", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "weight_b_pct", label: "B 權重", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "min_weight_pct", label: "最小權重(重疊貢獻)", format: "percent", align: "right", sortable: true, decimals: 2 },
];

const INDUSTRY_BREAKDOWN_COLUMNS: Column[] = [
  { key: "industry", label: "產業", sortable: true },
  { key: "weight_a_pct", label: "A 占比", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "weight_b_pct", label: "B 占比", format: "percent", align: "right", sortable: true, decimals: 2 },
  { key: "min_weight_pct", label: "最小占比(相似貢獻)", format: "percent", align: "right", sortable: true, decimals: 2 },
];

function gradeOverlap(label: string | undefined) {
  if (!label) return undefined;
  return { label, tone: overlapRatingTone(label) };
}

function CompareContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [etfList, setEtfList] = useState<EtfListItem[]>([]);
  const [etfListState, setEtfListState] = useState<FetchState>("loading");

  const initialSymbols = useMemo(() => {
    const raw = searchParams.get("symbols");
    if (!raw) return [];
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }, [searchParams]);

  const [selected, setSelected] = useState<string[]>(initialSymbols);
  const [pickerValue, setPickerValue] = useState("");

  const [multi, setMulti] = useState<MultiOverlap | null>(null);
  const [multiState, setMultiState] = useState<FetchState>("loading");
  const [multiErr, setMultiErr] = useState<{ code: string; message: string } | null>(null);

  const [pairwise, setPairwise] = useState<OverlapResponse | null>(null);
  const [pairwiseState, setPairwiseState] = useState<FetchState>("loading");
  const [pairwiseErr, setPairwiseErr] = useState<{ code: string; message: string } | null>(null);

  // Load ETF list for the picker
  useEffect(() => {
    listEtfs()
      .then((data) => {
        setEtfList(data);
        setEtfListState(data.length === 0 ? "empty" : "ok");
      })
      .catch(() => {
        setEtfListState("error");
      });
  }, []);

  // Sync selected -> URL
  useEffect(() => {
    const url = selected.length > 0 ? `/compare?symbols=${encodeURIComponent(selected.join(","))}` : "/compare";
    router.replace(url, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  function loadMulti(symbols: string[]) {
    setMultiState("loading");
    compareEtfs(symbols)
      .then((data) => {
        setMulti(data);
        setMultiState("ok");
      })
      .catch((e: unknown) => {
        setMultiErr(errorToFriendlyMessage(e));
        setMultiState("error");
      });
  }

  function loadPairwise(a: string, b: string) {
    setPairwiseState("loading");
    getOverlap(a, b)
      .then((data) => {
        setPairwise(data);
        setPairwiseState("ok");
      })
      .catch((e: unknown) => {
        setPairwiseErr(errorToFriendlyMessage(e));
        setPairwiseState("error");
      });
  }

  useEffect(() => {
    if (selected.length >= 2) {
      loadMulti(selected);
    }
    if (selected.length === 2) {
      loadPairwise(selected[0], selected[1]);
    } else {
      setPairwise(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected.join(",")]);

  function addSymbol(symbol: string) {
    if (!symbol) return;
    if (selected.includes(symbol)) return;
    if (selected.length >= 5) return;
    setSelected((prev) => [...prev, symbol]);
    setPickerValue("");
  }

  function removeSymbol(symbol: string) {
    setSelected((prev) => prev.filter((s) => s !== symbol));
  }

  const selectedEtfRows = etfList.filter((e) => selected.includes(e.symbol));

  const basicInfoColumns: Column[] = [
    { key: "symbol", label: "代號" },
    { key: "name", label: "名稱" },
    { key: "issuer", label: "發行商" },
    { key: "management_type", label: "主動/被動" },
    { key: "asset_class", label: "資產類別" },
  ];

  const pairsRows = (multi?.pairs ?? []).map((p) => ({
    ...p,
    overlap_rating_label: p.overlap_rating.label,
  }));

  return (
    <div>
      <PageHeader title="ETF 比較" subtitle="選擇多檔 ETF（最多 5 檔），比較成分股重疊度與產業曝險。" />

      {/* ETF selector */}
      <div className="mb-space-6 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <div className="mb-space-3 flex flex-wrap items-center gap-space-2">
          {selected.map((sym) => (
            <span
              key={sym}
              className="inline-flex items-center gap-space-1 rounded-sm bg-bg-surface-raised px-space-2 py-1 text-body text-text-primary"
            >
              {sym}
              <button
                onClick={() => removeSymbol(sym)}
                aria-label={`移除 ${sym}`}
                className="ml-space-1 text-text-muted hover:text-status-error"
              >
                ×
              </button>
            </span>
          ))}
          {selected.length === 0 && <span className="text-body text-text-muted">尚未選擇任何 ETF</span>}
        </div>
        <div className="flex flex-wrap items-center gap-space-2">
          {etfListState === "loading" && <span className="text-small text-text-muted">載入 ETF 清單中...</span>}
          {etfListState === "ok" && (
            <select
              value={pickerValue}
              onChange={(e) => addSymbol(e.target.value)}
              disabled={selected.length >= 5}
              className="rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              <option value="">{selected.length >= 5 ? "已達上限（5 檔）" : "新增 ETF..."}</option>
              {etfList
                .filter((e) => !selected.includes(e.symbol))
                .map((e) => (
                  <option key={e.symbol} value={e.symbol}>
                    {e.symbol} {e.name}
                  </option>
                ))}
            </select>
          )}
          {etfListState === "error" && <span className="text-small text-status-error">ETF 清單載入失敗</span>}
          <span className="text-small text-text-muted">已選 {selected.length} / 5 檔</span>
        </div>
      </div>

      {selected.length < 2 && (
        <EmptyState
          title="請選擇至少 2 檔 ETF"
          description="選擇 2 檔以上的 ETF 後，將顯示重疊度熱力圖與逐對重疊摘要；剛好選擇 2 檔時，會額外顯示共同持股與產業相似度分析。"
        />
      )}

      {selected.length >= 2 && (
        <>
          {/* 基本資料比較表 */}
          <div className="mb-space-8">
            <h2 className="mb-space-4 text-h2 text-text-primary">基本資料比較</h2>
            <DataTable columns={basicInfoColumns} rows={selectedEtfRows} />
          </div>

          {/* OverlapHeatmap */}
          <div className="mb-space-8">
            <h2 className="mb-space-2 text-h2 text-text-primary">重疊度熱力圖</h2>
            <p className="mb-space-4 text-small text-text-secondary">
              顯示每兩檔 ETF 之間的加權重疊度（0~100%）。對角線為自身（100%）。數字越高代表兩檔 ETF
              持股越相似，分散效果越低。
            </p>
            {multiState === "loading" && <LoadingSkeleton variant="chart" />}
            {multiState === "error" && <ErrorState code={multiErr?.code} message={multiErr?.message} retry={() => loadMulti(selected)} />}
            {multiState === "ok" && multi && (
              <div className="rounded-md border border-border-subtle bg-bg-surface p-space-4">
                <OverlapHeatmap symbols={multi.symbols} matrix={multi.matrix} pairs={multi.pairs} />
              </div>
            )}
          </div>

          {/* 逐對重疊摘要 */}
          <div className="mb-space-8">
            <h2 className="mb-space-4 text-h2 text-text-primary">逐對重疊摘要</h2>
            {multiState === "loading" && <LoadingSkeleton variant="table" />}
            {multiState === "error" && <ErrorState code={multiErr?.code} message={multiErr?.message} retry={() => loadMulti(selected)} />}
            {multiState === "ok" && (
              <DataTable columns={PAIR_COLUMNS} rows={pairsRows} emptyState={{ title: "沒有重疊資料" }} />
            )}
          </div>

          {/* 2 檔模式：共同持股 + 產業相似度 */}
          {selected.length === 2 && (
            <>
              <div className="mb-space-8">
                <h2 className="mb-space-4 text-h2 text-text-primary">成分股重疊明細（2 檔模式）</h2>
                {pairwiseState === "loading" && <LoadingSkeleton variant="card" />}
                {pairwiseState === "error" && (
                  <ErrorState code={pairwiseErr?.code} message={pairwiseErr?.message} retry={() => loadPairwise(selected[0], selected[1])} />
                )}
                {pairwiseState === "ok" && pairwise && (
                  <div className="grid grid-cols-1 gap-space-4 lg:grid-cols-2">
                    <MetricCard
                      label="加權重疊分數"
                      value={formatPercent(pairwise.overlap.weighted_overlap_pct, { decimals: 2 })}
                      grade={gradeOverlap(pairwise.overlap.overlap_rating.label)}
                      explanation="兩檔 ETF 持股權重的加權重疊比例。重疊度越高，代表兩檔 ETF 持股越相似，分散效果越低。"
                      dataDate={pairwise.overlap.holding_date_a ?? pairwise.overlap.holding_date_b}
                    />
                    <MetricCard
                      label="Jaccard 相似度"
                      value={formatNumber(pairwise.overlap.jaccard, { decimals: 3 })}
                      explanation="兩檔 ETF 成分股集合的相似度（不考慮權重），0 為完全不同，1 為完全相同。"
                      dataDate={pairwise.overlap.holding_date_a ?? pairwise.overlap.holding_date_b}
                    />
                  </div>
                )}
              </div>

              <div className="mb-space-8">
                <h2 className="mb-space-4 text-h2 text-text-primary">共同前十大持股</h2>
                {pairwiseState === "ok" && pairwise && (
                  <DataTable
                    columns={COMMON_TOP10_COLUMNS}
                    rows={pairwise.overlap.common_top10}
                    emptyState={{ title: "無共同前十大持股" }}
                  />
                )}
              </div>

              <div className="mb-space-8">
                <h2 className="mb-space-2 text-h2 text-text-primary">產業相似度</h2>
                {pairwiseState === "ok" && pairwise && (
                  <>
                    <div className="mb-space-4 grid grid-cols-1 gap-space-4 lg:grid-cols-3">
                      <MetricCard
                        label="產業相似度"
                        value={formatPercent(pairwise.industry_similarity.industry_similarity_pct, { decimals: 2 })}
                        explanation="兩檔 ETF 在各產業曝險的最小重疊比例加總，數字越高代表兩者產業結構越相似。"
                        dataDate={pairwise.industry_similarity.holding_date_a ?? pairwise.industry_similarity.holding_date_b}
                      />
                    </div>
                    <DataTable
                      columns={INDUSTRY_BREAKDOWN_COLUMNS}
                      rows={pairwise.industry_similarity.breakdown}
                      emptyState={{ title: "無產業相似度資料" }}
                    />
                  </>
                )}
              </div>
            </>
          )}

          {selected.length > 2 && (
            <div className="mb-space-8">
              <EmptyState
                title="共同持股明細僅支援 2 檔比較"
                description="目前選擇超過 2 檔 ETF，僅顯示熱力圖與逐對重疊摘要。若要查看共同前十大持股與產業相似度，請縮小選擇至 2 檔。"
              />
            </div>
          )}

          {/* AI 比較結論 */}
          <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4">
            <div className="mb-space-3 flex items-center justify-between">
              <h2 className="text-h2 text-text-primary">AI 比較結論</h2>
              <Badge label="即將推出" tone="neutral" />
            </div>
            <EmptyState
              title="AI 比較結論即將推出"
              description="AI 分析功能將基於系統資料提供研究觀點，目前後端尚未開放此功能（呼叫會回傳 501）。"
            />
          </div>

          <SourceFooter
            sourceName="ETF Portfolio Lab 系統資料"
            dataDate={selected.length === 2 ? (pairwise?.overlap.holding_date_a ?? pairwise?.overlap.holding_date_b ?? null) : null}
            disclaimer="本頁分析僅供研究參考，依各 ETF 最新成分股資料計算，不代表未來績效，亦非投資買賣建議。"
          />
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<LoadingSkeleton variant="card" />}>
      <CompareContent />
    </Suspense>
  );
}
