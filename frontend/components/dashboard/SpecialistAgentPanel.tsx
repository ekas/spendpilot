"use client";

import { ShieldCheck, Wallet, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentReport, AgentId } from "@/lib/types";

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
  const Icon = icons[report.agentId as AgentId] ?? ShieldCheck;
  const riskPercent = report.adverseRisk * 100;
  const riskColor =
    riskPercent >= 70
      ? "text-red-600 dark:text-red-400"
      : riskPercent >= 40
        ? "text-amber-600 dark:text-amber-400"
        : "text-emerald-600 dark:text-emerald-400";

  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm flex flex-col h-full">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-foreground">
            {report.agentName}
          </h3>
        </div>
        <RecBadge rec={report.recommendation} />
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className={cn("text-3xl font-bold tabular-nums", riskColor)}>
          {riskPercent.toFixed(1)}%
        </span>
        <span className="text-xs text-muted-foreground">adverse risk</span>
      </div>

      <div className="h-1.5 rounded-full bg-muted overflow-hidden mb-3">
        <div
          className={cn(
            "h-full rounded-full",
            riskPercent >= 70
              ? "bg-red-500"
              : riskPercent >= 40
                ? "bg-amber-500"
                : "bg-emerald-500"
          )}
          style={{ width: `${riskPercent}%` }}
        />
      </div>

      <p className="text-xs text-muted-foreground mb-3">{report.summary}</p>
      <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
        <Value label="Calibrated probability" value={formatProbability(report.calibratedProbability)} />
        <Value label="Model confidence" value={formatProbability(report.confidence)} />
      </div>

      <p className="text-xs font-semibold text-foreground mb-2">
        Signed model contributions
      </p>
      <ul className="space-y-1.5 mb-4 flex-1">
        {report.contributions.slice(0, 4).map((item) => (
          <li key={item.feature} className="flex items-center justify-between text-xs gap-3">
            <span className="text-muted-foreground truncate">
              {item.label}
            </span>
            <span
              className={cn(
                "font-mono shrink-0",
                item.impact > 0
                  ? "text-red-600 dark:text-red-400"
                  : item.impact < 0
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-muted-foreground"
              )}
            >
              {item.impact > 0 ? "+" : ""}
              {item.impact.toFixed(4)}
            </span>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap gap-1.5 pt-3 border-t border-border">
        {report.reasonCodes.map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
          >
            {tag.replaceAll("_", " ")}
          </span>
        ))}
      </div>
      <p className="mt-3 text-[10px] text-muted-foreground">
        {report.modelName} · {report.modelVersion}
      </p>
    </div>
  );
}

function formatProbability(value: number | null): string {
  return value === null ? "Not provided" : `${(value * 100).toFixed(1)}%`;
}

function Value({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 p-2">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-medium text-foreground">{value}</p>
    </div>
  );
}
