"use client";

import { useState } from "react";
import {
  UserCheck,
  Clock,
  AlertTriangle,
  CheckCircle2,
  RotateCcw,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn, formatDate } from "@/lib/utils";
import { submitReviewDecision } from "@/lib/api";
import type { HumanReviewItem } from "@/lib/types";

const priorityConfig = {
  low: { variant: "muted" as const, label: "Low" },
  medium: { variant: "info" as const, label: "Medium" },
  high: { variant: "warning" as const, label: "High" },
  urgent: { variant: "danger" as const, label: "Urgent" },
};

const statusConfig = {
  pending: { icon: Clock, color: "text-amber-400" },
  "in-review": { icon: UserCheck, color: "text-cyan-400" },
  resolved: { icon: CheckCircle2, color: "text-emerald-400" },
};

interface HumanReviewQueueProps {
  items: HumanReviewItem[];
  onUpdate?: () => void;
}

export function HumanReviewQueue({ items, onUpdate }: HumanReviewQueueProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleDecision = async (
    id: string,
    decision: "approve" | "challenge" | "override"
  ) => {
    setLoadingId(id);
    try {
      await submitReviewDecision(id, decision);
      onUpdate?.();
    } finally {
      setLoadingId(null);
    }
  };

  const pending = items.filter((i) => i.status !== "resolved").length;

  return (
    <Card>
      <CardHeader
        title="Human Review Queue"
        subtitle={`${pending} cases awaiting review`}
        action={
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500/10">
            <UserCheck className="h-4 w-4 text-orange-400" />
          </div>
        }
      />

      <div className="space-y-3">
        {items.map((item) => {
          const priority = priorityConfig[item.priority];
          const status = statusConfig[item.status];
          const StatusIcon = status.icon;
          const isSelected = selectedId === item.id;

          return (
            <div
              key={item.id}
              className={cn(
                "rounded-lg border transition-colors cursor-pointer",
                isSelected
                  ? "border-cyan-500/40 bg-cyan-500/5"
                  : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700"
              )}
              onClick={() =>
                setSelectedId(isSelected ? null : item.id)
              }
            >
              <div className="p-4">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <StatusIcon className={cn("h-4 w-4", status.color)} />
                  <span className="text-sm font-medium text-zinc-200">
                    {item.applicantName}
                  </span>
                  <span className="text-xs text-zinc-600 font-mono">
                    {item.caseId}
                  </span>
                  <Badge variant={priority.variant} className="ml-auto">
                    {priority.label}
                  </Badge>
                  <RiskBadge level={item.riskLevel} />
                </div>
                <p className="text-xs text-zinc-500 mb-2">{item.reason}</p>
                <div className="flex items-center gap-4 text-[10px] text-zinc-600">
                  <span>Score: {item.credibilityScore}</span>
                  <span>{formatDate(item.submittedAt)}</span>
                  {item.assignedTo && (
                    <span>Assigned: {item.assignedTo}</span>
                  )}
                </div>
              </div>

              {isSelected && item.status !== "resolved" && (
                <div className="border-t border-zinc-800 px-4 py-3 flex gap-2">
                  <Button
                    variant="success"
                    size="sm"
                    loading={loadingId === item.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDecision(item.id, "approve");
                    }}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Approve
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={loadingId === item.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDecision(item.id, "challenge");
                    }}
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Challenge
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    loading={loadingId === item.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDecision(item.id, "override");
                    }}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Override
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.location.href = `/dashboard?case=${item.caseId}`;
                    }}
                  >
                    View Case
                  </Button>
                </div>
              )}

              {item.status === "resolved" && (
                <div className="border-t border-zinc-800 px-4 py-2 flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Resolved by {item.assignedTo}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
