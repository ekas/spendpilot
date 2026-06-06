"use client";

import { useState } from "react";
import {
  FileSearch,
  Wallet,
  ShieldAlert,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import {
  cn,
  formatDate,
  getAgentColor,
  getScoreColor,
} from "@/lib/utils";
import type { AgentId, AgentReport } from "@/lib/types";

const agentIcons: Record<AgentId, React.ComponentType<{ className?: string }>> = {
  evidence: FileSearch,
  affordability: Wallet,
  "credit-risk": ShieldAlert,
  manager: BrainCircuit,
};

interface AgentCardProps {
  report: AgentReport;
  defaultExpanded?: boolean;
}

export function AgentCard({ report, defaultExpanded = false }: AgentCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const Icon = agentIcons[report.agentId];

  return (
    <Card padding="none" className="overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 p-5 text-left hover:bg-muted/30 transition-colors"
      >
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg border",
            report.agentId === "evidence" && "bg-blue-500/10 border-blue-500/30",
            report.agentId === "affordability" && "bg-violet-500/10 border-violet-500/30",
            report.agentId === "credit-risk" && "bg-rose-500/10 border-rose-500/30",
            report.agentId === "manager" && "bg-cyan-500/10 border-cyan-500/30"
          )}
        >
          <Icon className={cn("h-5 w-5", getAgentColor(report.agentId))} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-semibold text-foreground">
              {report.agentName}
            </h3>
            <StatusIndicator status={report.status} />
          </div>
          <p className="text-xs text-muted-foreground truncate">{report.summary}</p>
        </div>

        <div className="text-right shrink-0">
          <p className={cn("text-2xl font-bold font-mono", getScoreColor(report.score))}>
            {report.score}
          </p>
          <p className="text-[10px] text-muted-foreground/80">
            {(report.confidence * 100).toFixed(0)}% conf.
          </p>
        </div>

        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground/80 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground/80 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border p-5 space-y-5">
          {report.completedAt && (
            <p className="text-xs text-muted-foreground/80">
              Completed {formatDate(report.completedAt)}
            </p>
          )}

          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
              Reasoning Chain
            </h4>
            <ol className="space-y-1.5">
              {report.reasoning.map((step, i) => (
                <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                  <span className="text-muted-foreground/80 font-mono shrink-0">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wider">
              Findings ({report.findings.length})
            </h4>
            <div className="space-y-3">
              {report.findings.map((finding) => (
                <div
                  key={finding.id}
                  className="rounded-lg border border-border bg-surface p-3"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <RiskBadge level={finding.severity} />
                    <Badge variant="muted">{finding.category}</Badge>
                    <span className="text-[10px] text-muted-foreground/80 ml-auto font-mono">
                      {(finding.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-sm font-medium text-foreground mb-1">
                    {finding.title}
                  </p>
                  <p className="text-xs text-muted-foreground mb-2">
                    {finding.description}
                  </p>
                  {finding.evidence.length > 0 && (
                    <ul className="space-y-0.5">
                      {finding.evidence.map((e, i) => (
                        <li
                          key={i}
                          className="text-[11px] text-muted-foreground/80 font-mono pl-2 border-l border-border"
                        >
                          {e}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wider">
              Metrics
            </h4>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(report.metrics).map(([key, value]) => (
                <div key={key} className="rounded-lg bg-muted/50 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground capitalize">
                    {key.replace(/([A-Z])/g, " $1").trim()}
                  </p>
                  <p className="text-sm font-mono text-foreground">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <Progress value={report.score} label="Agent Score" />
        </div>
      )}
    </Card>
  );
}
