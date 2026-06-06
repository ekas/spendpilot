"use client";

import { Check, X } from "lucide-react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

export function PolicyEnginePanel({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const decision = analysis.decision.label;

  const decisionStyle =
    decision === "APPROVE"
      ? "bg-emerald-500 text-white"
      : decision === "REFER"
        ? "bg-amber-500 text-white"
        : "bg-red-500 text-white";

  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm h-full flex flex-col">
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-sm font-semibold text-foreground">
          Policy Engine Evaluation
        </h3>
        <Info className="h-3.5 w-3.5 text-muted-foreground/50" />
      </div>

      <div className="flex-1 space-y-0">
        <div className="grid grid-cols-[1fr_auto] gap-2 text-xs font-medium text-muted-foreground border-b border-border pb-2 mb-2">
          <span>Rule</span>
          <span>Result</span>
        </div>
        {analysis.policyChecks.map((check) => (
          <div
            key={check.id}
            className="grid grid-cols-[1fr_auto] gap-2 py-2 border-b border-border-subtle last:border-0 items-center"
          >
            <span className="text-xs text-foreground">{check.rule}</span>
            <span
              className={cn(
                "inline-flex items-center gap-1 text-xs font-semibold",
                check.status === "pass"
                  ? "text-emerald-600 dark:text-emerald-400"
                  : check.status === "warning"
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-red-600 dark:text-red-400"
              )}
            >
              {check.status === "pass" ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <X className="h-3.5 w-3.5" />
              )}
              {check.status === "pass"
                ? "Pass"
                : check.status === "warning"
                  ? "Review"
                  : "Fail"}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-4 mt-2 border-t border-border">
        <span className="text-sm font-medium text-foreground">
          Policy Decision
        </span>
        <span
          className={cn(
            "rounded-lg px-4 py-1.5 text-sm font-bold tracking-wide",
            decisionStyle
          )}
        >
          {decision}
        </span>
      </div>
      <p className="mt-3 text-[10px] text-muted-foreground">
        {analysis.decision.finalized
          ? "Finalized by policy"
          : `Pending human review${analysis.decision.reviewId ? ` · ${analysis.decision.reviewId}` : ""}`}
      </p>
    </div>
  );
}
