"use client";

import { Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";
import { getManagerSummary } from "@/lib/chart-data";

export function ManagerSummaryPanel({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = getManagerSummary(analysis);

  const recStyle =
    data.recommendation === "APPROVE"
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400"
      : data.recommendation === "REFER"
        ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
        : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400";

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm h-full flex flex-col">
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-sm font-semibold text-foreground">
          Manager Agent Summary
        </h3>
        <Info className="h-3.5 w-3.5 text-muted-foreground/50" />
      </div>

      <div className="space-y-3 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Recommendation</span>
          <span
            className={cn(
              "rounded-md px-2.5 py-0.5 text-xs font-bold",
              recStyle
            )}
          >
            {data.recommendation}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Confidence</span>
          <span className="rounded-md bg-amber-100 dark:bg-amber-500/15 px-2.5 py-0.5 text-xs font-bold text-amber-700 dark:text-amber-400">
            {data.confidence}%
          </span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground mb-5 flex-1">{data.summary}</p>

      <div className="pt-4 border-t border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">
            Disagreement Score
          </span>
          <span className="text-2xl font-bold text-red-600 dark:text-red-400">
            {data.disagreementScore}
            <span className="text-sm font-normal text-muted-foreground">
              /100
            </span>
          </span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-red-500"
            style={{ width: `${data.disagreementScore}%` }}
          />
        </div>
      </div>
    </div>
  );
}
