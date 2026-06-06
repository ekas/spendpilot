"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";
import { getReasonCodes, CATEGORY_COLORS } from "@/lib/chart-data";

export function ReasonCodeChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = getReasonCodes(analysis);
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <ChartSection title="Reason Code Breakdown">
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="relative h-44 w-44 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={72}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold text-foreground">{total}</span>
            <span className="text-[10px] text-muted-foreground">Total Reasons</span>
          </div>
        </div>

        <div className="flex-1 w-full space-y-1.5 max-h-44 overflow-y-auto">
          {data.map((item, i) => (
            <div
              key={item.name}
              className="flex items-center justify-between text-[10px] gap-2"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
                  }}
                />
                <span className="text-muted-foreground truncate">{item.name}</span>
              </div>
              <span className="text-foreground font-medium shrink-0">
                {item.value} ({Math.round((item.value / total) * 100)}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </ChartSection>
  );
}
