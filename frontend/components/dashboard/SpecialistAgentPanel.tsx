"use client";

import { Info, ShieldCheck, Wallet, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentReport, AgentId } from "@/lib/types";
import { mapAgentDisplay } from "@/lib/chart-data";

const icons: Record<string, React.ComponentType<{ className?: string }>> = {
  evidence: ShieldCheck,
  affordability: Wallet,
  "credit-risk": AlertTriangle,
};

function RecBadge({ rec }: { rec: "APPROVE" | "REFER" | "REJECT" }) {
  const styles = {
    APPROVE: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400",
    REFER: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400",
    REJECT: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
  };
  return (
    <span
      className={cn(
        "rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wide",
        styles[rec]
      )}
    >
      {rec}
    </span>
  );
}

export function SpecialistAgentPanel({ report }: { report: AgentReport }) {
  const data = mapAgentDisplay(report);
  const Icon = icons[report.agentId as AgentId] ?? ShieldCheck;

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col h-full">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icon className={cn("h-4 w-4", data.color)} />
          <h3 className="text-sm font-semibold text-foreground">{data.title}</h3>
          <Info className="h-3.5 w-3.5 text-muted-foreground/50" />
        </div>
        <RecBadge rec={data.recommendation} />
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className={cn("text-4xl font-bold", data.color)}>{data.score}</span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>

      <div className="h-1.5 rounded-full bg-muted overflow-hidden mb-3">
        <div
          className={cn("h-full rounded-full", data.barColor)}
          style={{ width: `${data.score}%` }}
        />
      </div>

      <p className="text-xs text-muted-foreground mb-4">{data.description}</p>

      <p className="text-xs font-semibold text-foreground mb-2">Top Issues</p>
      <ul className="space-y-1.5 mb-4 flex-1">
        {data.issues.map((issue, i) => (
          <li key={i} className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground truncate pr-2">
              {issue.label}
            </span>
            <span className="text-red-600 dark:text-red-400 font-mono shrink-0">
              + {issue.impact.toFixed(2)}
            </span>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap gap-1.5 pt-3 border-t border-border">
        {data.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-violet-100 dark:bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
