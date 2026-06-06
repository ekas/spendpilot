"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ChartSection } from "./ChartSection";
import { formatCompactCurrency } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";
import { getSpendOverTime } from "@/lib/chart-data";

const LINE_COLORS = ["#8b5cf6", "#22c55e", "#3b82f6", "#f97316", "#9ca3af"];

export function SpendOverTimeChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = getSpendOverTime(analysis);
  const categories = [
    ...analysis.spendCategories.slice(0, 5).map((c) => c.name),
    ...(analysis.spendCategories.length > 5 ? ["Other"] : []),
  ];

  return (
    <ChartSection title="Spend by Category Over Time">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatCompactCurrency(v)}
            />
            <Tooltip
              formatter={(value) => formatCompactCurrency(Number(value))}
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
              iconType="circle"
              iconSize={8}
            />
            {categories.map((cat, i) => (
              <Line
                key={cat}
                type="monotone"
                dataKey={cat}
                stroke={LINE_COLORS[i % LINE_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 4, fill: LINE_COLORS[i % LINE_COLORS.length] }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartSection>
  );
}
