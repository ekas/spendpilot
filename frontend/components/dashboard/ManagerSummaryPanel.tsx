"use client";

import { GitCompareArrows, UserCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

export function ManagerSummaryPanel({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = analysis.manager;

  const recStyle =
    data.recommendation === "APPROVE"
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400"
      : data.recommendation === "REFER"
        ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
        : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400";

  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <GitCompareArrows className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-foreground">
          Manager Agent Summary
        </h3>
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
          <span className="text-muted-foreground">Specialist agreement</span>
          <span className="text-xs font-semibold text-foreground">
            {data.disagreement ? "Disagreement found" : "Aligned"}
          </span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground mb-5 flex-1">{data.summary}</p>

      <div className="pt-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs">
          <UserCheck className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Review routing</span>
          <span className="ml-auto font-semibold text-foreground">
            {analysis.decision.requiresHumanReview
              ? "Human review required"
              : "No human review"}
          </span>
        </div>
        <p className="mt-3 text-[10px] text-muted-foreground">
          Final authority: {analysis.decision.finalAuthority}
        </p>
      </div>
    </div>
  );
}
