"use client";

import dynamic from "next/dynamic";
import { formatPercent } from "@/lib/format";
import { chartColor, seriesPalette } from "@/lib/chartColors";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

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
  const palette = seriesPalette();
  const unclassifiedColor = chartColor("--series-unclassified");
  const textSecondary = chartColor("--text-secondary");
  const data = items.map((it, i) => ({
    name: it.name,
    value: it.value,
    itemStyle: { color: it.unclassified ? unclassifiedColor : palette[i % palette.length] },
  }));

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (p: { name: string; value: number }) =>
        `${p.name}<br/>占比：${formatPercent(p.value, { decimals: 2 })}`,
    },
    legend: { orient: "vertical", left: "left", textStyle: { color: textSecondary } },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: true,
        label: { color: textSecondary },
        data,
      },
    ],
  };

  return <ReactECharts option={option} style={{ width: "100%", height: `${height}px` }} />;
}
