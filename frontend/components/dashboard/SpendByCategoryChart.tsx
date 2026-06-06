"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChartSection } from "./ChartSection";
import { formatCompactCurrency } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";
import { getSpendByCategory } from "@/lib/chart-data";

export function SpendByCategoryChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = getSpendByCategory(analysis);
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <ChartSection title="Spend by Category">
      <div className="flex flex-col md:flex-row items-center gap-6">
        <div className="relative h-52 w-52 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-lg font-bold text-foreground">
              {formatCompactCurrency(total)}
            </span>
            <span className="text-xs text-muted-foreground">Total</span>
          </div>
        </div>

        <div className="flex-1 w-full space-y-2.5">
          {data.map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between gap-3 text-sm"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-foreground truncate">{item.name}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="font-semibold text-foreground">
                  {formatCompactCurrency(item.value)}
                </span>
                <span className="text-muted-foreground w-8 text-right">
                  {Math.round(item.percentage)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </ChartSection>
  );
}
