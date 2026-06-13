"use client";

import dynamic from "next/dynamic";
import { formatNumber, formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

export interface OverlapPair {
  a?: string;
  b?: string;
  symbol_a?: string;
  symbol_b?: string;
  weighted_overlap_pct: number;
  overlap_rating: { label: string; value?: number };
  jaccard: number;
  overlap_count?: number;
}

export interface OverlapHeatmapProps {
  symbols: string[];
  matrix: number[][];
  pairs: OverlapPair[];
  height?: number;
}

function findPair(pairs: OverlapPair[], a: string, b: string): OverlapPair | null {
  if (a === b) return null;
  return (
    pairs.find((p) => {
      const pa = p.symbol_a ?? p.a;
      const pb = p.symbol_b ?? p.b;
      return (pa === a && pb === b) || (pa === b && pb === a);
    }) ?? null
  );
}

export default function OverlapHeatmap({ symbols, matrix, pairs, height = 360 }: OverlapHeatmapProps) {
  const data: [number, number, number][] = [];
  for (let i = 0; i < symbols.length; i++) {
    for (let j = 0; j < symbols.length; j++) {
      const value = matrix?.[i]?.[j] ?? (i === j ? 100 : 0);
      data.push([j, i, value]);
    }
  }

  const option = {
    tooltip: {
      position: "top",
      formatter: (params: { data: [number, number, number] }) => {
        const [x, y, value] = params.data;
        const a = symbols[y];
        const b = symbols[x];
        if (a === b) {
          return `${a}<br/>自身重疊：100%`;
        }
        const pair = findPair(pairs, a, b);
        if (!pair) {
          return `${a} vs ${b}<br/>加權重疊度：${formatPercent(value, { decimals: 2 })}`;
        }
        return (
          `${a} vs ${b}` +
          `<br/>加權重疊度：${formatPercent(pair.weighted_overlap_pct, { decimals: 2 })}` +
          `<br/>重疊程度：${pair.overlap_rating.label}` +
          `<br/>Jaccard：${formatNumber(pair.jaccard, { decimals: 3 })}`
        );
      },
    },
    grid: { left: 80, right: 20, top: 20, bottom: 60 },
    xAxis: {
      type: "category",
      data: symbols,
      splitArea: { show: true },
      axisLabel: { color: "var(--text-secondary)" },
    },
    yAxis: {
      type: "category",
      data: symbols,
      splitArea: { show: true },
      axisLabel: { color: "var(--text-secondary)" },
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: {
        color: ["#0f2742", "#1d4ed8", "#3b82f6", "#93c5fd"],
      },
      textStyle: { color: "var(--text-secondary)" },
    },
    series: [
      {
        type: "heatmap",
        data,
        label: {
          show: true,
          color: "#fff",
          formatter: (p: { data: [number, number, number] }) => formatNumber(p.data[2], { decimals: 1 }),
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ width: "100%", height: `${height}px` }} />;
}
