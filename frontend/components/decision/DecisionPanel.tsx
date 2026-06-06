import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Shield,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { cn, formatDate, getDecisionColor } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

const outcomeConfig = {
  approved: {
    icon: CheckCircle2,
    label: "Approved",
    variant: "success" as const,
    bg: "bg-emerald-500/5 border-emerald-500/20",
  },
  "approved-with-conditions": {
    icon: AlertCircle,
    label: "Approved with Conditions",
    variant: "warning" as const,
    bg: "bg-amber-500/5 border-amber-500/20",
  },
  "review-required": {
    icon: Clock,
    label: "Review Required",
    variant: "warning" as const,
    bg: "bg-orange-500/5 border-orange-500/20",
  },
  declined: {
    icon: XCircle,
    label: "Declined",
    variant: "danger" as const,
    bg: "bg-red-500/5 border-red-500/20",
  },
  pending: {
    icon: Clock,
    label: "Pending",
    variant: "muted" as const,
    bg: "bg-zinc-800/50 border-zinc-700",
  },
};

interface DecisionPanelProps {
  decision: AnalysisResult["decision"];
}

export function DecisionPanel({ decision }: DecisionPanelProps) {
  const config = outcomeConfig[decision.outcome];
  const Icon = config.icon;

  return (
    <Card>
      <CardHeader
        title="Final Decision"
        subtitle="Manager Agent recommendation"
        action={
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10">
            <Shield className="h-4 w-4 text-cyan-400" />
          </div>
        }
      />

      <div
        className={cn(
          "rounded-xl border p-5 mb-4",
          config.bg
        )}
      >
        <div className="flex items-center gap-3 mb-3">
          <Icon className={cn("h-6 w-6", getDecisionColor(decision.outcome))} />
          <div>
            <p className={cn("text-lg font-semibold", getDecisionColor(decision.outcome))}>
              {config.label}
            </p>
            {decision.decidedAt && (
              <p className="text-xs text-zinc-500">
                {decision.reviewedBy} · {formatDate(decision.decidedAt)}
              </p>
            )}
          </div>
          <Badge variant={config.variant} className="ml-auto">
            {decision.outcome}
          </Badge>
        </div>

        <div className="space-y-2">
          <h4 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
            Rationale
          </h4>
          <ul className="space-y-1.5">
            {decision.rationale.map((r, i) => (
              <li key={i} className="flex gap-2 text-sm text-zinc-300">
                <span className="text-zinc-600 font-mono text-xs mt-0.5">
                  {i + 1}.
                </span>
                {r}
              </li>
            ))}
          </ul>
        </div>

        {decision.conditions && decision.conditions.length > 0 && (
          <div className="mt-4 pt-4 border-t border-zinc-800/50">
            <h4 className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-2">
              Conditions
            </h4>
            <ul className="space-y-1">
              {decision.conditions.map((c, i) => (
                <li key={i} className="text-sm text-zinc-400 flex gap-2">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-400 mt-0.5 shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}
