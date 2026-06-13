/**
 * Shared TypeScript types for ETF Portfolio Lab frontend.
 * Field names are derived from backend/app/services/*.py and backend/app/api/*.py
 * to stay accurate with the real API response shapes (unwrapped from {data, meta}).
 */

// ---------------------------------------------------------------------------
// Common / envelope
// ---------------------------------------------------------------------------

export interface ApiEnvelope<T> {
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export type ConfidenceLevel = "高" | "中" | "低" | null;

export interface DataProvenance {
  source_name: string | null;
  source_url: string | null;
  data_date: string | null;
  fetched_at: string | null;
  confidence_level: ConfidenceLevel;
}

// ---------------------------------------------------------------------------
// ETF list / card
// ---------------------------------------------------------------------------

export interface EtfListItem {
  symbol: string;
  name: string;
  issuer: string | null;
  asset_class: string | null;
  management_type: string | null;
  is_active: boolean;
  has_holdings: boolean;
  has_price_data: boolean;
}

export interface Concentration {
  etf_symbol?: string;
  holding_date: string | null;
  num_holdings: number;
  top1_fraction?: number | null;
  top1_pct: number | null;
  top3_fraction?: number | null;
  top3_pct: number | null;
  top5_fraction?: number | null;
  top5_pct: number | null;
  top10_fraction?: number | null;
  top10_pct: number | null;
  hhi: number | null;
  effective_holdings: number | null;
}

export interface EtfCard {
  symbol: string;
  name: string;
  issuer: string | null;
  management_type: string | null;
  asset_class: string | null;
  investment_style: string | null;
  strategy_type: string | null;
  tracking_index: string | null;
  index_provider: string | null;
  expense_ratio: number | null;
  management_fee: number | null;
  custody_fee: number | null;
  dividend_frequency: string | null;
  concentration: {
    holding_date: string | null;
    num_holdings: number;
    top1_pct: number | null;
    top3_pct: number | null;
    top5_pct: number | null;
    top10_pct: number | null;
    hhi: number | null;
    effective_holdings: number | null;
  };
  top3_industries: IndustryExposureItem[];
  data_provenance: DataProvenance;
}

// ---------------------------------------------------------------------------
// Holdings / Industry exposure
// ---------------------------------------------------------------------------

export interface Holding {
  asset_symbol: string;
  asset_name: string | null;
  weight_fraction: number;
  weight_pct: number;
}

export interface IndustryExposureItem {
  industry: string;
  weight_fraction: number;
  weight_pct: number;
}

export interface IndustryExposure {
  etf_symbol: string;
  holding_date: string | null;
  level: 1 | 2;
  industries: IndustryExposureItem[];
  max_industry: IndustryExposureItem | null;
  top3_industries: IndustryExposureItem[];
  unclassified: {
    industry: string;
    weight_fraction: number;
    weight_pct: number;
  };
}

// ---------------------------------------------------------------------------
// Price history
// ---------------------------------------------------------------------------

export interface EtfPricePoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  adjusted_close: number | null;
  volume: number | null;
}

export interface EtfPriceHistory {
  symbol: string;
  currency: string;
  source_name: string | null;
  data_start: string | null;
  data_end: string | null;
  points: EtfPricePoint[];
}

// ---------------------------------------------------------------------------
// Overlap
// ---------------------------------------------------------------------------

export interface OverlapRating {
  label: "極低重疊" | "低度重疊" | "中度重疊" | "高度重疊" | string;
  value: number;
}

export interface OverlapAsset {
  asset_symbol: string;
  asset_name: string | null;
  weight_a_pct: number;
  weight_b_pct: number;
  min_weight_pct: number;
}

export interface PairwiseOverlap {
  symbol_a: string;
  symbol_b: string;
  holding_date_a: string | null;
  holding_date_b: string | null;
  overlap_count: number;
  overlap_assets: OverlapAsset[];
  weighted_overlap_fraction: number;
  weighted_overlap_pct: number;
  overlap_rating: OverlapRating;
  jaccard: number;
  common_top10: OverlapAsset[];
}

export interface IndustrySimilarityBreakdownItem {
  industry: string;
  weight_a_pct: number;
  weight_b_pct: number;
  min_weight_pct: number;
}

export interface IndustrySimilarity {
  symbol_a: string;
  symbol_b: string;
  holding_date_a: string | null;
  holding_date_b: string | null;
  level: 1 | 2;
  industry_similarity_fraction: number;
  industry_similarity_pct: number;
  breakdown: IndustrySimilarityBreakdownItem[];
}

export interface OverlapResponse {
  overlap: PairwiseOverlap;
  industry_similarity: IndustrySimilarity;
}

export interface MultiOverlap {
  symbols: string[];
  matrix: number[][];
  pairs: PairwiseOverlap[];
}

export interface PortfolioOverlapRisk {
  symbols: string[];
  matrix: number[][];
  pairs: Array<{
    a?: string;
    b?: string;
    symbol_a?: string;
    symbol_b?: string;
    weighted_overlap_pct: number;
    overlap_rating: { label: string; value?: number };
    jaccard: number;
    [key: string]: unknown;
  }>;
  top_overlapping_pairs: unknown[];
  note: string;
}

// ---------------------------------------------------------------------------
// Dashboard / Ranking
// ---------------------------------------------------------------------------

export interface DashboardSummary {
  total_etfs: number;
  active_etfs: number;
  etfs_with_holdings: number;
  etfs_with_prices: number;
  last_updated: string | null;
  recent_quality_warnings: number;
}

export type RankingMetric =
  | "hhi"
  | "effective_holdings"
  | "top1"
  | "top10"
  | "num_holdings"
  | "industry_concentration"
  | "industry_diversification"
  | "industry_exposure";

export interface RankingItem {
  symbol: string;
  name?: string;
  value: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Portfolio
// ---------------------------------------------------------------------------

export interface PortfolioItem {
  id?: number;
  etf_symbol: string;
  target_weight: number;
}

export interface Portfolio {
  id: number;
  name: string;
  description: string | null;
  base_currency: string;
  items: PortfolioItem[];
}

export interface ValidationResult {
  status: "PASS" | "WARN" | "FAIL";
  weight_sum_pct: number;
  message: string;
  duplicate_symbols: string[];
  unknown_symbols: string[];
}

export interface StockExposureItem {
  asset_symbol: string;
  asset_name: string | null;
  weight_fraction: number;
  weight_pct: number;
}

export interface StockExposureResponse {
  stocks: StockExposureItem[];
  missing_holdings?: string[];
  [key: string]: unknown;
}

export interface PortfolioConcentration {
  hhi: number | null;
  effective_holdings: number | null;
  num_stocks: number;
  top1_pct: number;
  top3_pct: number;
  top5_pct: number;
  top10_pct: number;
}

export interface PortfolioWarning {
  code: string;
  severity: "INFO" | "WARN" | "ERROR" | string;
  message: string;
}

export interface PortfolioWarningsResponse {
  warnings: PortfolioWarning[];
  disclaimer?: string;
  [key: string]: unknown;
}

export interface PortfolioAnalyzeResponse {
  validation: ValidationResult;
  stock_exposure: StockExposureResponse;
  industry_exposure: IndustryExposure | Record<string, unknown>;
  concentration: PortfolioConcentration;
  warnings: PortfolioWarningsResponse | PortfolioWarning[];
}

// ---------------------------------------------------------------------------
// Backtest
// ---------------------------------------------------------------------------

export interface BacktestRequestPayload {
  portfolio_id?: number | null;
  symbols?: string[];
  weights?: number[];
  start_date: string;
  end_date: string;
  initial_amount: number;
  monthly_contribution?: number;
  dividend_reinvest?: boolean;
  rebalance_frequency?: "none" | "monthly" | "quarterly" | "annually" | string;
  transaction_cost_rate?: number;
  risk_free_rate?: number;
  name?: string | null;
}

export interface BacktestSeriesPoint {
  date: string;
  value: number;
}

export interface DrawdownSeriesPoint {
  date: string;
  drawdown: number;
}

export interface BacktestResult {
  final_value: number;
  total_contribution: number;
  total_profit: number;
  cagr: number;
  irr: number | null;
  max_drawdown: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  annual_returns: Record<string, number>;
  portfolio_value_series: BacktestSeriesPoint[];
  drawdown_series: DrawdownSeriesPoint[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Projection
// ---------------------------------------------------------------------------

export interface ProjectionRequestPayload {
  initial_amount: number;
  monthly_contribution?: number;
  annual_return_rate?: number;
  years?: number;
  target_amount?: number | null;
  name?: string | null;
  persist?: boolean;
}

export interface YearlyProjectionPoint {
  year: number;
  value: number;
  contributed: number;
  profit: number;
}

export interface ProjectionResult {
  final_value: number;
  total_contribution: number;
  total_profit: number;
  target_achieved: boolean | null;
  yearly_series: YearlyProjectionPoint[];
  disclaimer: string;
}

export interface ScenarioRequestPayload {
  initial_amount: number;
  monthly_contribution?: number;
  years?: number;
  scenarios?: Record<string, number>;
  target_amount?: number | null;
}

export interface ScenarioResult extends ProjectionResult {
  scenario_name: string;
  annual_return_rate: number;
}

export interface ScenarioResponse {
  scenarios: Record<string, ScenarioResult>;
  rates_used: Record<string, number>;
  disclaimer: string;
}

export interface GoalSeekRequestPayload {
  solve_for: "years" | "monthly_contribution" | "annual_return";
  initial_amount: number;
  monthly_contribution?: number;
  annual_return_rate?: number;
  years?: number;
  target_amount: number;
}

export interface GoalSeekResult {
  achievable: boolean;
  years?: number | null;
  months?: number | null;
  monthly_contribution?: number;
  annual_return_rate?: number | null;
  achievable_with_zero?: boolean;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Data sources / quality
// ---------------------------------------------------------------------------

export interface DataSource {
  id: number;
  source_name: string;
  source_type: string | null;
  base_url: string | null;
  description: string | null;
  update_frequency: string | null;
  reliability_level: string | null;
  license_note: string | null;
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// AI Assistant
// ---------------------------------------------------------------------------

export interface AIAnalysisResponse {
  analysis_text: string;
  provider: string | null;
  model: string | null;
  refused: boolean;
  data_sources: string[];
  data_dates: string[];
  disclaimer: string;
}

export interface FetchLog {
  id: number;
  provider_name: string;
  dataset_type: string;
  status: "success" | "error" | "empty" | string;
  rows_fetched: number | null;
  rows_inserted: number | null;
  source_url: string | null;
  data_date: string | null;
  message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DataQualityCheck {
  id: number;
  dataset_type: string;
  dataset_key: string | null;
  check_name: string;
  status: "PASS" | "WARN" | "FAIL" | string;
  severity: string | null;
  message: string | null;
  checked_at: string | null;
}
