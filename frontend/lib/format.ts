/**
 * Number / percent / currency / date formatters shared by tables & cards.
 * All numeric output uses a monospace-friendly format (no surprise locale variance).
 */

const NBSP = "—"; // em dash for "no data"

export function formatNumber(
  value: number | null | undefined,
  options?: { decimals?: number }
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NBSP;
  const decimals = options?.decimals ?? 2;
  return new Intl.NumberFormat("zh-Hant-TW", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NBSP;
  return new Intl.NumberFormat("zh-Hant-TW", {
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a fraction-or-percent value as a percentage string with `%` suffix.
 * If `isFraction` is true, multiplies by 100 first (e.g. 0.184 -> "18.40%").
 */
export function formatPercent(
  value: number | null | undefined,
  options?: { decimals?: number; isFraction?: boolean }
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NBSP;
  const decimals = options?.decimals ?? 2;
  const pct = options?.isFraction ? value * 100 : value;
  return `${formatNumber(pct, { decimals })}%`;
}

export function formatCurrencyTWD(
  value: number | null | undefined,
  options?: { decimals?: number }
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NBSP;
  const decimals = options?.decimals ?? 0;
  return new Intl.NumberFormat("zh-Hant-TW", {
    style: "currency",
    currency: "TWD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format an ISO date string (YYYY-MM-DD or full ISO datetime) as YYYY-MM-DD.
 * Returns em dash for null/undefined/invalid input.
 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return NBSP;
  // Already a plain date string
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toISOString().slice(0, 10);
}

/**
 * Format an ISO datetime string as YYYY-MM-DD HH:mm.
 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return NBSP;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const date = d.toISOString().slice(0, 10);
  const time = d.toISOString().slice(11, 16);
  return `${date} ${time}`;
}

export { NBSP as EMPTY_VALUE };
