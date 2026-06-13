"use client";

import dynamic from "next/dynamic";
import { formatPercent } from "@/lib/format";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

export interface ExposureBarItem {
  name: string;
  value: number;
}

export interface ExposureBarProps {
  items: ExposureBarItem[];
  height?: number;
}

export default function ExposureBar({ items, height = 320 }: ExposureBarProps) {
  const sorted = [...items].sort((a, b) => a.value - b.value);
  const option = {
    grid: { left: 120, right: 40, top: 20, bottom: 20 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>權重：${formatPercent(p.value, { decimals: 2 })}`;
      },
    },
    xAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
    yAxis: {
      type: "category",
      data: sorted.map((it) => it.name),
    },
    series: [
      {
        type: "bar",
        data: sorted.map((it) => it.value),
        itemStyle: { color: "var(--series-1)" },
      },
    ],
  };

  return <ReactECharts option={option} style={{ width: "100%", height: `${height}px` }} />;
}
