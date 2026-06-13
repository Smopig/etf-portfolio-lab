"use client";

import dynamic from "next/dynamic";
import { formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
  "var(--series-9)",
  "var(--series-10)",
];
const UNCLASSIFIED_COLOR = "var(--series-unclassified)";

export interface ExposureDoughnutItem {
  name: string;
  value: number;
  unclassified?: boolean;
}

export interface ExposureDoughnutProps {
  items: ExposureDoughnutItem[];
  height?: number;
}

export default function ExposureDoughnut({ items, height = 320 }: ExposureDoughnutProps) {
  const data = items.map((it, i) => ({
    name: it.name,
    value: it.value,
    itemStyle: { color: it.unclassified ? UNCLASSIFIED_COLOR : SERIES_COLORS[i % SERIES_COLORS.length] },
  }));

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (p: { name: string; value: number }) =>
        `${p.name}<br/>占比：${formatPercent(p.value, { decimals: 2 })}`,
    },
    legend: { orient: "vertical", left: "left", textStyle: { color: "var(--text-secondary)" } },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: true,
        label: { color: "var(--text-secondary)" },
        data,
      },
    ],
  };

  return <ReactECharts option={option} style={{ width: "100%", height: `${height}px` }} />;
}
