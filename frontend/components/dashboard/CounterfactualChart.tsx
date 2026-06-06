"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";

export function CounterfactualChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = analysis.counterfactuals.map((scenario) => ({
    scenario: scenario.label,
    reduction: scenario.riskReduction * 100,
    before: scenario.originalAverageRisk * 100,
    after: scenario.hypotheticalAverageRisk * 100,
    policy: `${scenario.originalPolicyOutcome} → ${scenario.hypotheticalPolicyOutcome}`,
  }));

  return (
    <ChartSection
      title="Measured Counterfactuals"
      subtitle="Hypothetical full-workflow reruns; never persisted or treated as decisions"
    >
      {data.length ? (
        <>
          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 12, bottom: 4 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tickFormatter={(value) => `${Number(value).toFixed(1)} pp`}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="scenario"
                  width={150}
                  tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value, _name, item) => [
                    `${Number(value).toFixed(2)} percentage points`,
                    `Risk reduction · ${item.payload.before.toFixed(1)}% to ${item.payload.after.toFixed(1)}% · ${item.payload.policy}`,
                  ]}
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="reduction" fill="#22c55e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 space-y-2">
            {analysis.counterfactuals.map((scenario) => (
              <p
                key={scenario.scenarioId}
                className="text-[10px] text-muted-foreground"
              >
                <span className="font-semibold text-foreground">
                  {scenario.label}:
                </span>{" "}
                {scenario.assumption}
              </p>
            ))}
          </div>
        </>
      ) : (
        <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
          No applicable bounded scenario reduced modeled risk.
        </div>
      )}
    </ChartSection>
  );
}
