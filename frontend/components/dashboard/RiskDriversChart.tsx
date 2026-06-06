"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";

export function RiskDriversChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = analysis.agentReports
    .flatMap((report) =>
      report.contributions.map((contribution) => ({
        name: contribution.label,
        impact: contribution.impact,
        agent: report.agentName,
        value: contribution.value,
      }))
    )
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 8);
  const extent = Math.max(
    ...data.map((entry) => Math.abs(entry.impact)),
    0.01
  );

  return (
    <ChartSection title="Top Risk Drivers (SHAP Impact)">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis
              type="number"
              domain={[-extent, extent]}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Signed contribution to modeled adverse risk",
                position: "insideBottom",
                offset: -2,
                fontSize: 10,
                fill: "var(--muted-foreground)",
              }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={120}
              tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v, _name, item) => {
                const n = Number(v);
                return [
                  n > 0 ? `+${n.toFixed(4)}` : n.toFixed(4),
                  `${item.payload.agent} · value ${String(item.payload.value ?? "Not provided")}`,
                ];
              }}
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <ReferenceLine x={0} stroke="var(--border)" />
            <Bar dataKey="impact" radius={[0, 4, 4, 0]} barSize={14}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.impact > 0 ? "#ef4444" : "#22c55e"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartSection>
  );
}
