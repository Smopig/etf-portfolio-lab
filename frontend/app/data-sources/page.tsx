"use client";

import { useEffect, useRef, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import MetricCard from "@/components/common/MetricCard";
import Badge, { confidenceLevelTone, BadgeTone } from "@/components/common/Badge";
import DataTable, { Column } from "@/components/tables/DataTable";
import SourceFooter from "@/components/common/SourceFooter";
import { ErrorState, LoadingSkeleton, errorToFriendlyMessage } from "@/components/common/States";
import {
  listDataSources,
  listDataQuality,
  listFetchLogs,
  startDataRefresh,
  getDataRefreshStatus,
} from "@/lib/api";
import type { DataSource, DataQualityCheck, FetchLog, RefreshStatus } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

type FetchState = "loading" | "ok" | "empty" | "error";

const SOURCE_COLUMNS: Column[] = [
  { key: "source_name", label: "來源名稱", sortable: true },
  { key: "source_type", label: "類型", sortable: true },
  { key: "reliability_label", label: "資料可信度", sortable: true },
  { key: "update_frequency", label: "更新頻率", sortable: true },
  { key: "enabled_label", label: "啟用狀態", sortable: true },
  { key: "base_url", label: "連結" },
];

const QUALITY_COLUMNS: Column[] = [
  { key: "dataset_type", label: "資料類型", sortable: true },
  { key: "dataset_key", label: "資料識別", sortable: true },
  { key: "check_name", label: "檢查項目", sortable: true },
  { key: "status", label: "狀態", sortable: true },
  { key: "message", label: "說明" },
  { key: "checked_at", label: "檢查時間", format: "date", sortable: true },
];

const FETCH_LOG_COLUMNS: Column[] = [
  { key: "provider_name", label: "來源", sortable: true },
  { key: "dataset_type", label: "資料類型", sortable: true },
  { key: "status_label", label: "狀態", sortable: true },
  { key: "rows_fetched", label: "擷取筆數", format: "number", sortable: true },
  { key: "rows_inserted", label: "寫入筆數", format: "number", sortable: true },
  { key: "data_date", label: "資料日期", format: "date", sortable: true },
  { key: "started_at", label: "開始時間", format: "date", sortable: true },
  { key: "message", label: "訊息" },
];

const STATUS_OPTIONS = [
  { value: "all", label: "全部狀態" },
  { value: "FAIL", label: "FAIL" },
  { value: "WARN", label: "WARN" },
  { value: "PASS", label: "PASS" },
];

function statusTone(status: string): BadgeTone {
  if (status === "FAIL") return "error";
  if (status === "WARN") return "warning";
  if (status === "PASS") return "success";
  return "neutral";
}

function reliabilityTone(level: string | null): BadgeTone {
  return confidenceLevelTone(level ?? undefined);
}

function fetchLogStatusLabel(status: string): string {
  if (status === "success") return "成功";
  if (status === "error") return "失敗";
  if (status === "empty") return "無資料";
  return status;
}

export default function DataSourcesPage() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourcesState, setSourcesState] = useState<FetchState>("loading");
  const [sourcesErr, setSourcesErr] = useState<{ code: string; message: string } | null>(null);

  const [quality, setQuality] = useState<DataQualityCheck[]>([]);
  const [qualityState, setQualityState] = useState<FetchState>("loading");
  const [qualityErr, setQualityErr] = useState<{ code: string; message: string } | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

  const [fetchLogs, setFetchLogs] = useState<FetchLog[]>([]);
  const [fetchLogsState, setFetchLogsState] = useState<FetchState>("loading");
  const [fetchLogsErr, setFetchLogsErr] = useState<{ code: string; message: string } | null>(null);

  const [refreshStatus, setRefreshStatus] = useState<RefreshStatus | null>(null);
  const [refreshErr, setRefreshErr] = useState<{ code: string; message: string } | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function loadSources() {
    setSourcesState("loading");
    listDataSources()
      .then((data) => {
        setSources(data);
        setSourcesState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setSourcesErr(errorToFriendlyMessage(e));
        setSourcesState("error");
      });
  }

  function loadQuality(status: string) {
    setQualityState("loading");
    listDataQuality({ status: status === "all" ? undefined : status })
      .then((data) => {
        setQuality(data);
        setQualityState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setQualityErr(errorToFriendlyMessage(e));
        setQualityState("error");
      });
  }

  function loadFetchLogs() {
    setFetchLogsState("loading");
    listFetchLogs({ limit: 50 })
      .then((data) => {
        setFetchLogs(data);
        setFetchLogsState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setFetchLogsErr(errorToFriendlyMessage(e));
        setFetchLogsState("error");
      });
  }

  function isRefreshActive(status: RefreshStatus | null): boolean {
    if (!status) return false;
    return status.running === true || status.phase === "listing" || status.phase === "prices";
  }

  function stopPolling() {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }

  function pollRefreshStatus() {
    getDataRefreshStatus()
      .then((status) => {
        setRefreshStatus(status);
        if (!isRefreshActive(status)) {
          stopPolling();
          if (status.phase === "done" || status.phase === "error") {
            loadSources();
            loadQuality(statusFilter);
            loadFetchLogs();
          }
        }
      })
      .catch((e: unknown) => {
        setRefreshErr(errorToFriendlyMessage(e));
        stopPolling();
      });
  }

  function startPolling() {
    stopPolling();
    pollIntervalRef.current = setInterval(pollRefreshStatus, 3000);
  }

  function handleStartRefresh() {
    setRefreshErr(null);
    startDataRefresh()
      .then((res) => {
        setRefreshStatus(res);
        if (isRefreshActive(res)) {
          startPolling();
        }
      })
      .catch((e: unknown) => {
        setRefreshErr(errorToFriendlyMessage(e));
      });
  }

  useEffect(() => {
    loadSources();
    loadQuality("all");
    loadFetchLogs();
    // Check if a refresh is already running on mount
    getDataRefreshStatus()
      .then((status) => {
        setRefreshStatus(status);
        if (isRefreshActive(status)) {
          startPolling();
        }
      })
      .catch(() => {
        // ignore - refresh status is best-effort
      });
    return () => {
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadQuality(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const enabledCount = sources.filter((s) => s.enabled).length;
  const failCount = quality.filter((q) => q.status === "FAIL").length;
  const lastCheckedAt = quality
    .map((q) => q.checked_at)
    .filter((d): d is string => !!d)
    .sort()
    .reverse()[0];

  const sourceRows = sources.map((s) => ({
    ...s,
    reliability_label: s.reliability_level ?? "未標示",
    enabled_label: s.enabled ? "啟用中" : "已停用",
    base_url: s.base_url ? (
      <a href={s.base_url} target="_blank" rel="noreferrer" className="text-accent-primary hover:underline">
        前往
      </a>
    ) : (
      "—"
    ),
  }));

  const fetchLogRows = fetchLogs.map((f) => ({
    ...f,
    status_label: fetchLogStatusLabel(f.status),
    message: f.message ?? "—",
  }));

  const qualityRows = quality.map((q) => ({
    ...q,
    dataset_key: q.dataset_key ?? "—",
    message: q.message ?? "—",
    checked_at: q.checked_at ? formatDateTime(q.checked_at) : "—",
    status: <Badge label={q.status} tone={statusTone(q.status)} />,
  }));

  return (
    <div>
      <PageHeader title="資料來源管理" subtitle="檢視資料來源清單、資料品質檢查結果，以及匯入方式說明。" />

      {/* 一鍵更新資料 */}
      <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <div className="flex flex-wrap items-center justify-between gap-space-2">
          <div>
            <h2 className="text-h2 text-text-primary">一鍵更新資料</h2>
            <p className="mt-space-1 text-small text-text-muted">
              會從 TWSE／Yahoo 抓取 ETF 清單與價格，需數分鐘；成分股尚未包含。
            </p>
          </div>
          <button
            type="button"
            onClick={handleStartRefresh}
            disabled={isRefreshActive(refreshStatus)}
            className="rounded-sm border border-accent-primary bg-accent-primary px-space-4 py-2 text-body text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRefreshActive(refreshStatus) ? "更新中…" : "更新資料"}
          </button>
        </div>
        {isRefreshActive(refreshStatus) && refreshStatus && (
          <p className="mt-space-3 text-small text-text-secondary">
            {refreshStatus.phase === "listing" && "抓取 ETF 清單中…"}
            {refreshStatus.phase === "prices" &&
              `抓取價格中 ${refreshStatus.processed}/${refreshStatus.total}（成功 ${refreshStatus.succeeded}／失敗 ${refreshStatus.failed}）`}
          </p>
        )}
        {!isRefreshActive(refreshStatus) && refreshStatus && refreshStatus.phase === "done" && (
          <p className="mt-space-3 text-small text-text-secondary">{refreshStatus.message}</p>
        )}
        {!isRefreshActive(refreshStatus) && refreshStatus && refreshStatus.phase === "error" && (
          <ErrorState message={refreshStatus.message} />
        )}
        {refreshErr && (
          <p className="mt-space-3 text-small text-status-error">{refreshErr.message}</p>
        )}
      </div>

      {/* 上方指標卡 */}
      <div className="mb-space-8 grid grid-cols-1 gap-space-4 sm:grid-cols-3">
        <MetricCard
          label="啟用中資料來源數"
          value={sourcesState === "ok" ? enabledCount : sourcesState === "loading" ? null : 0}
          loading={sourcesState === "loading"}
          explanation="目前系統設定為「啟用」狀態的資料來源數量。"
        />
        <MetricCard
          label="資料品質 FAIL 數"
          value={qualityState === "loading" ? null : failCount}
          loading={qualityState === "loading"}
          grade={failCount > 0 ? { label: "需留意", tone: "error" } : { label: "正常", tone: "success" }}
          explanation="目前資料品質檢查中狀態為 FAIL 的項目數，建議優先處理。"
        />
        <MetricCard
          label="最近檢查時間"
          value={lastCheckedAt ? formatDateTime(lastCheckedAt) : "—"}
          loading={qualityState === "loading"}
          explanation="目前已知資料品質檢查紀錄中，最近一次的檢查時間。"
        />
      </div>

      {/* 資料來源清單 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">資料來源清單</h2>
        {sourcesState === "loading" && <LoadingSkeleton variant="table" />}
        {sourcesState === "error" && <ErrorState code={sourcesErr?.code} message={sourcesErr?.message} retry={loadSources} />}
        {(sourcesState === "ok" || sourcesState === "empty") && (
          <DataTable
            columns={SOURCE_COLUMNS}
            rows={sourceRows}
            emptyState={{ title: "尚無資料來源紀錄" }}
          />
        )}
      </div>

      {/* 資料品質檢查 */}
      <div className="mb-space-8">
        <div className="mb-space-4 flex flex-wrap items-center justify-between gap-space-2">
          <h2 className="text-h2 text-text-primary">資料品質檢查</h2>
          <div className="flex items-center gap-space-2">
            <label className="text-small text-text-secondary">狀態篩選</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        {qualityState === "loading" && <LoadingSkeleton variant="table" />}
        {qualityState === "error" && <ErrorState code={qualityErr?.code} message={qualityErr?.message} retry={() => loadQuality(statusFilter)} />}
        {(qualityState === "ok" || qualityState === "empty") && (
          <DataTable
            columns={QUALITY_COLUMNS}
            rows={qualityRows}
            searchable
            emptyState={{ title: "沒有符合篩選條件的資料品質檢查紀錄" }}
          />
        )}
      </div>

      {/* 手動匯入說明 */}
      <div className="mb-space-8 rounded-md border border-border-subtle bg-bg-surface p-space-4">
        <div className="mb-space-3 flex items-center justify-between">
          <h2 className="text-h2 text-text-primary">資料匯入</h2>
          <Badge label="僅支援 CLI" tone="neutral" />
        </div>
        <p className="mb-space-3 text-body text-text-secondary">
          目前資料透過 CLI 匯入工具更新，尚未提供網頁上傳功能。若需更新或補充資料，請在後端環境執行對應的匯入指令，例如：
        </p>
        <pre className="overflow-x-auto rounded-sm bg-bg-inset p-space-3 text-small text-text-primary">
{`python -m scripts.import_etfs
python -m scripts.import_holdings
python -m scripts.import_prices
python -m scripts.import_industry_mapping`}
        </pre>
        <p className="mt-space-3 text-small text-text-muted">
          以上為示意指令名稱，實際腳本請參考後端 scripts/ 目錄。匯入完成後，可在上方「資料品質檢查」表格中確認最新檢查結果。
        </p>
      </div>

      {/* 資料擷取紀錄 */}
      <div className="mb-space-8">
        <h2 className="mb-space-4 text-h2 text-text-primary">資料擷取紀錄</h2>
        {fetchLogsState === "loading" && <LoadingSkeleton variant="table" />}
        {fetchLogsState === "error" && (
          <ErrorState code={fetchLogsErr?.code} message={fetchLogsErr?.message} retry={loadFetchLogs} />
        )}
        {(fetchLogsState === "ok" || fetchLogsState === "empty") && (
          <DataTable
            columns={FETCH_LOG_COLUMNS}
            rows={fetchLogRows}
            searchable
            emptyState={{
              title: "尚無擷取紀錄",
              description: "執行 scripts/run_fetch.py 或各資料來源的擷取流程後，將於此顯示擷取紀錄。",
            }}
          />
        )}
      </div>

      <SourceFooter
        sourceName="ETF Portfolio Lab 系統設定"
        dataDate={lastCheckedAt ?? null}
        disclaimer="資料來源與品質檢查資訊僅反映系統目前設定與最近一次檢查結果，實際資料時效請以各來源網站公告為準。"
      />
    </div>
  );
}
