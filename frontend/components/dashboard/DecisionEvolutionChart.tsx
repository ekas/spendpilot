"use client";

import {
  Database,
  Users,
  GitMerge,
  Scale,
  UserCheck,
  CheckCircle2,
} from "lucide-react";
import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export function DecisionEvolutionChart({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const stages = [
    {
      label: "Immutable snapshot",
      detail: analysis.caseContext.snapshotId,
      icon: Database,
      state: "complete",
    },
    {
      label: "Three specialists",
      detail: `${analysis.agentReports.length} reports`,
      icon: Users,
      state: "complete",
    },
    {
      label: "Manager",
      detail: analysis.manager.disagreement ? "Disagreement" : "Aligned",
      icon: GitMerge,
      state: "complete",
    },
    {
      label: "Policy engine",
      detail: analysis.decision.label,
      icon: Scale,
      state: "complete",
    },
    {
      label: analysis.decision.requiresHumanReview
        ? "Human review"
        : "Finalized",
      detail: analysis.decision.requiresHumanReview
        ? analysis.decision.reviewId ?? "Review queued"
        : "No review required",
      icon: analysis.decision.requiresHumanReview ? UserCheck : CheckCircle2,
      state: analysis.decision.finalized ? "complete" : "current",
    },
  ] as const;

  return (
    <ChartSection
      title="Decision Flow"
      subtitle="Actual execution path for this immutable case snapshot"
    >
      <div className="space-y-2">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div
              key={stage.label}
              className="grid grid-cols-[32px_1fr_auto] items-center gap-3"
            >
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border",
                  stage.state === "complete"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-600"
                    : "border-amber-500/40 bg-amber-500/10 text-amber-600"
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-foreground">
                  {stage.label}
                </p>
                <p className="truncate text-[10px] text-muted-foreground">
                  {stage.detail}
                </p>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground">
                {String(index + 1).padStart(2, "0")}
              </span>
            </div>
          );
        })}
      </div>
    </ChartSection>
  );
}
