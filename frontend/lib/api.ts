import type {
  AIAnalysisResponse,
  BacktestRequestPayload,
  BacktestResult,
  Concentration,
  DashboardSummary,
  DataQualityCheck,
  DataSource,
  DividendRankingRow,
  DividendRankingMeta,
  RefreshStartResponse,
  RefreshStatus,
  EtfCard,
  EtfPriceHistory,
  EtfPriceRange,
  FetchLog,
  EtfListItem,
  GoalSeekRequestPayload,
  GoalSeekResult,
  Holding,
  HoldingsMeta,
  IndustryExposure,
  IndustrySimilarity,
  MultiOverlap,
  OverlapResponse,
  PairwiseOverlap,
  Portfolio,
  PortfolioAnalyzeResponse,
  PortfolioConcentration,
  PortfolioItem,
  PortfolioOverlapRisk,
  PortfolioWarningsResponse,
  ProjectionRequestPayload,
  ProjectionResult,
  RankingItem,
  RankingMetric,
  ScenarioRequestPayload,
  ScenarioResponse,
  StockExposureResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/**
 * Typed application error mirroring the backend error envelope:
 * {"error": {"code", "message"}}.
 *
 * `status` is the HTTP status code (0 for network-level failures with no
 * response, e.g. backend not running).
 */
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/**
 * Fetch `path` against the API base URL, unwrap the `{data, meta}` success
 * envelope, and throw a typed `ApiError` for `{error: {code, message}}`
 * responses or network failures.
 */
export async function apiFetchWithMeta<T = unknown, M = Record<string, unknown>>(
  path: string,
  init?: RequestInit
): Promise<{ data: T; meta: M | undefined }> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
  } catch (err) {
    throw new ApiError(
      "NETWORK_ERROR",
      err instanceof Error ? err.message : "Network request failed",
      0
    );
  }

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    const errBody = body as { error?: { code?: string; message?: string } } | null;
    if (errBody?.error) {
      throw new ApiError(
        errBody.error.code || "INTERNAL_ERROR",
        errBody.error.message || res.statusText,
        res.status
      );
    }
    throw new ApiError("INTERNAL_ERROR", res.statusText || "Request failed", res.status);
  }

  const okBody = body as { data?: T; meta?: M } | null;
  return {
    data: (okBody?.data ?? (body as T)) as T,
    meta: okBody?.meta,
  };
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const { data } = await apiFetchWithMeta<T>(path, init);
  return data;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  [key: string]: unknown;
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>("/api/dashboard/summary");
}

// ---------------------------------------------------------------------------
// ETFs
// ---------------------------------------------------------------------------

export async function listEtfs(params?: { active?: boolean }): Promise<EtfListItem[]> {
  return apiFetch<EtfListItem[]>(`/api/etfs${qs({ active: params?.active })}`);
}

export async function getEtfCard(symbol: string): Promise<EtfCard> {
  return apiFetch<EtfCard>(`/api/etfs/${encodeURIComponent(symbol)}`);
}

export async function getHoldings(
  symbol: string,
  params?: { date?: string; n?: number }
): Promise<Holding[]> {
  return apiFetch<Holding[]>(
    `/api/etfs/${encodeURIComponent(symbol)}/holdings${qs({
      date: params?.date,
      n: params?.n,
    })}`
  );
}

export async function getHoldingsWithMeta(
  symbol: string,
  params?: { date?: string; n?: number }
): Promise<{ holdings: Holding[]; meta: HoldingsMeta | null }> {
  const { data, meta } = await apiFetchWithMeta<Holding[], HoldingsMeta>(
    `/api/etfs/${encodeURIComponent(symbol)}/holdings${qs({
      date: params?.date,
      n: params?.n,
    })}`
  );
  return { holdings: data, meta: meta ?? null };
}

export async function getConcentration(
  symbol: string,
  params?: { date?: string }
): Promise<Concentration> {
  return apiFetch<Concentration>(
    `/api/etfs/${encodeURIComponent(symbol)}/concentration${qs({ date: params?.date })}`
  );
}

export async function getIndustryExposure(
  symbol: string,
  params?: { level?: 1 | 2; date?: string }
): Promise<IndustryExposure> {
  return apiFetch<IndustryExposure>(
    `/api/etfs/${encodeURIComponent(symbol)}/industry-exposure${qs({
      level: params?.level,
      date: params?.date,
    })}`
  );
}

export async function getEtfPrices(
  symbol: string,
  params?: { start?: string; end?: string; limit?: number }
): Promise<EtfPriceHistory> {
  return apiFetch<EtfPriceHistory>(
    `/api/etfs/${encodeURIComponent(symbol)}/prices${qs({
      start: params?.start,
      end: params?.end,
      limit: params?.limit,
    })}`
  );
}

export async function getEtfPriceRange(symbols: string[]): Promise<EtfPriceRange> {
  return apiFetch<EtfPriceRange>(`/api/etfs/price-range${qs({ symbols: symbols.join(",") })}`);
}

export async function compareEtfs(symbols: string[]): Promise<MultiOverlap> {
  return apiFetch<MultiOverlap>(`/api/etfs/compare${qs({ symbols: symbols.join(",") })}`);
}

export async function getOverlap(
  symbolA: string,
  symbolB: string
): Promise<OverlapResponse> {
  return apiFetch<OverlapResponse>(
    `/api/etfs/overlap${qs({ symbols: `${symbolA},${symbolB}` })}`
  );
}

export async function rankEtfs(params: {
  metric: RankingMetric;
  order?: "asc" | "desc";
  limit?: number;
  industry?: string;
  level?: 1 | 2;
}): Promise<RankingItem[]> {
  return apiFetch<RankingItem[]>(
    `/api/etfs/ranking${qs({
      metric: params.metric,
      order: params.order,
      limit: params.limit,
      industry: params.industry,
      level: params.level,
    })}`
  );
}

export async function getDividendRankingWithMeta(params?: {
  order?: "asc" | "desc";
  frequency?: string;
  limit?: number;
}): Promise<{ rows: DividendRankingRow[]; meta: DividendRankingMeta }> {
  const { data, meta } = await apiFetchWithMeta<DividendRankingRow[], DividendRankingMeta>(
    `/api/etfs/dividends/ranking${qs({
      order: params?.order,
      frequency: params?.frequency,
      limit: params?.limit,
    })}`
  );
  return {
    rows: data ?? [],
    meta: meta ?? {
      order: params?.order ?? "desc",
      frequency: params?.frequency ?? null,
      limit: params?.limit ?? null,
      count: data?.length ?? 0,
      disclosure: "",
    },
  };
}

// ---------------------------------------------------------------------------
// Portfolios
// ---------------------------------------------------------------------------

export async function listPortfolios(): Promise<Portfolio[]> {
  return apiFetch<Portfolio[]>("/api/portfolios");
}

export async function getPortfolio(id: number): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/portfolios/${id}`);
}

export async function createPortfolio(payload: {
  name: string;
  description?: string | null;
  base_currency?: string;
  items: PortfolioItem[];
}): Promise<Portfolio> {
  return apiFetch<Portfolio>("/api/portfolios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updatePortfolio(
  id: number,
  payload: {
    name?: string;
    description?: string | null;
    base_currency?: string;
    items?: PortfolioItem[];
  }
): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/portfolios/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deletePortfolio(id: number): Promise<{ deleted: boolean; id: number }> {
  return apiFetch<{ deleted: boolean; id: number }>(`/api/portfolios/${id}`, {
    method: "DELETE",
  });
}

export async function analyzePortfolioDraft(
  items: PortfolioItem[]
): Promise<PortfolioAnalyzeResponse> {
  return apiFetch<PortfolioAnalyzeResponse>("/api/portfolios/analyze", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}

export async function getPortfolioExposure(
  id: number,
  params?: { level?: 1 | 2 }
): Promise<{ stock_exposure: StockExposureResponse; industry_exposure: IndustryExposure }> {
  return apiFetch(`/api/portfolios/${id}/exposure${qs({ level: params?.level })}`);
}

export async function getPortfolioConcentration(id: number): Promise<PortfolioConcentration> {
  return apiFetch<PortfolioConcentration>(`/api/portfolios/${id}/concentration`);
}

export async function getPortfolioOverlapRisk(id: number): Promise<PortfolioOverlapRisk> {
  return apiFetch(`/api/portfolios/${id}/overlap-risk`);
}

export async function getPortfolioWarnings(id: number): Promise<PortfolioWarningsResponse> {
  return apiFetch<PortfolioWarningsResponse>(`/api/portfolios/${id}/warnings`);
}

// ---------------------------------------------------------------------------
// Backtests
// ---------------------------------------------------------------------------

export async function runBacktest(
  payload: BacktestRequestPayload,
  params?: { persist?: boolean }
): Promise<BacktestResult> {
  return apiFetch<BacktestResult>(`/api/backtests${qs({ persist: params?.persist })}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Projections
// ---------------------------------------------------------------------------

export async function runProjection(payload: ProjectionRequestPayload): Promise<ProjectionResult> {
  return apiFetch<ProjectionResult>("/api/projections", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function projectionScenarios(
  payload: ScenarioRequestPayload
): Promise<ScenarioResponse> {
  return apiFetch<ScenarioResponse>("/api/projections/scenarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function goalSeek(payload: GoalSeekRequestPayload): Promise<GoalSeekResult> {
  return apiFetch<GoalSeekResult>("/api/projections/goal-seek", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Data sources / quality
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// AI Assistant
// ---------------------------------------------------------------------------

export async function analyzeEtf(symbol: string, question?: string): Promise<AIAnalysisResponse> {
  return apiFetch<AIAnalysisResponse>("/api/ai/analyze-etf", {
    method: "POST",
    body: JSON.stringify({ symbol, ...(question ? { question } : {}) }),
  });
}

export async function analyzePortfolio(
  target: { portfolioId?: number; items?: PortfolioItem[] },
  question?: string
): Promise<AIAnalysisResponse> {
  const body: Record<string, unknown> = {};
  if (target.portfolioId !== undefined) {
    body.portfolio_id = target.portfolioId;
  } else if (target.items !== undefined) {
    body.items = target.items;
  }
  if (question) body.question = question;
  return apiFetch<AIAnalysisResponse>("/api/ai/analyze-portfolio", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function explainBacktest(
  result: BacktestResult,
  question?: string
): Promise<AIAnalysisResponse> {
  return apiFetch<AIAnalysisResponse>("/api/ai/explain-backtest", {
    method: "POST",
    body: JSON.stringify({ result, ...(question ? { question } : {}) }),
  });
}

export async function explainProjection(
  result: ProjectionResult,
  question?: string
): Promise<AIAnalysisResponse> {
  return apiFetch<AIAnalysisResponse>("/api/ai/explain-projection", {
    method: "POST",
    body: JSON.stringify({ result, ...(question ? { question } : {}) }),
  });
}

export async function listDataSources(): Promise<DataSource[]> {
  return apiFetch<DataSource[]>("/api/data-sources");
}

export async function listFetchLogs(params?: {
  datasetType?: string;
  providerName?: string;
  limit?: number;
}): Promise<FetchLog[]> {
  return apiFetch<FetchLog[]>(
    `/api/data-sources/fetch-logs${qs({
      dataset_type: params?.datasetType,
      provider_name: params?.providerName,
      limit: params?.limit,
    })}`
  );
}

export async function startDataRefresh(opts?: {
  listing?: boolean;
  prices?: boolean;
  range?: string;
  limit?: number;
  market?: string;
  holdings?: boolean;
  dividends?: boolean;
}): Promise<RefreshStartResponse> {
  return apiFetch<RefreshStartResponse>("/api/data/refresh", {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  });
}

export async function getDataRefreshStatus(): Promise<RefreshStatus> {
  return apiFetch<RefreshStatus>("/api/data/refresh/status");
}

export async function listDataQuality(params?: {
  dataset_type?: string;
  status?: string;
  limit?: number;
}): Promise<DataQualityCheck[]> {
  return apiFetch<DataQualityCheck[]>(
    `/api/data-quality${qs({
      dataset_type: params?.dataset_type,
      status: params?.status,
      limit: params?.limit,
    })}`
  );
}
