/**
 * Resolve CSS custom properties (e.g. "var(--series-1)") to concrete color
 * strings for ECharts.
 *
 * ECharts renders to <canvas>, and canvas does NOT understand CSS `var(--…)`
 * references — passing one yields an invalid color that paints as black. We
 * therefore resolve the variable to its computed value at render time, with a
 * hardcoded fallback (kept in sync with app/globals.css) for SSR / first paint.
 */

const FALLBACKS: Record<string, string> = {
  "--series-1": "#3b82f6",
  "--series-2": "#22c55e",
  "--series-3": "#f59e0b",
  "--series-4": "#ef4444",
  "--series-5": "#8b5cf6",
  "--series-6": "#06b6d4",
  "--series-7": "#eab308",
  "--series-8": "#ec4899",
  "--series-9": "#84cc16",
  "--series-10": "#f97316",
  "--series-unclassified": "#475569",
  "--text-primary": "#e5e9f0",
  "--text-secondary": "#9aa5b8",
  "--text-muted": "#6b7484",
};

/**
 * Return a concrete color for a CSS variable name (with or without the
 * surrounding `var(...)`). Resolves via getComputedStyle in the browser and
 * falls back to the known hex value on the server or if unset.
 */
export function chartColor(nameOrVar: string): string {
  const name = nameOrVar.replace(/^var\(/, "").replace(/\)$/, "").trim();
  if (typeof window !== "undefined" && typeof getComputedStyle !== "undefined") {
    const v = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    if (v) return v;
  }
  return FALLBACKS[name] ?? "#888888";
}

/** Ordered categorical palette resolved to concrete colors. */
export function seriesPalette(): string[] {
  return [
    "--series-1",
    "--series-2",
    "--series-3",
    "--series-4",
    "--series-5",
    "--series-6",
    "--series-7",
    "--series-8",
    "--series-9",
    "--series-10",
  ].map(chartColor);
}
