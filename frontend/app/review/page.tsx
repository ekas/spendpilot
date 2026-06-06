"use client";

import { useEffect, useState } from "react";
import { UserCheck, AlertTriangle, Clock, CheckCircle2 } from "lucide-react";
import { getReviewQueue } from "@/lib/api";
import { HumanReviewQueue } from "@/components/decision/HumanReviewQueue";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { Card, CardHeader } from "@/components/ui/Card";
import type { HumanReviewItem } from "@/lib/types";

export default function ReviewPage() {
  const [items, setItems] = useState<HumanReviewItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadQueue = async () => {
    const data = await getReviewQueue();
    setItems(data);
    setLoading(false);
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const pending = items.filter((i) => i.status === "pending").length;
  const inReview = items.filter((i) => i.status === "in-review").length;
  const resolved = items.filter((i) => i.status === "resolved").length;
  const urgent = items.filter((i) => i.priority === "urgent").length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-8">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">
          Human Review Queue
        </h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Uncertain and adverse cases requiring human oversight
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Pending"
          value={String(pending)}
          icon={Clock}
          accent="amber"
        />
        <MetricCard
          label="In Review"
          value={String(inReview)}
          icon={UserCheck}
          accent="cyan"
        />
        <MetricCard
          label="Urgent"
          value={String(urgent)}
          icon={AlertTriangle}
          accent="rose"
        />
        <MetricCard
          label="Resolved"
          value={String(resolved)}
          icon={CheckCircle2}
          accent="emerald"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <HumanReviewQueue items={items} onUpdate={loadQueue} />
        </div>

        <div>
          <Card>
            <CardHeader
              title="Review Workflow"
              subtitle="Decision paths for uncertain cases"
            />
            <div className="space-y-4 text-xs text-zinc-400">
              <WorkflowStep
                step={1}
                title="Case Escalation"
                desc="Manager Agent flags uncertain or adverse findings for human review"
              />
              <WorkflowStep
                step={2}
                title="Human Assessment"
                desc="Reviewer examines agent reports, conflicts, and policy violations"
              />
              <WorkflowStep
                step={3}
                title="Decision Action"
                desc="Approve the agent recommendation, challenge findings, or override with justification"
              />
              <WorkflowStep
                step={4}
                title="Re-analysis (if needed)"
                desc="Manager Agent requests specialist re-analysis based on human input"
              />
              <WorkflowStep
                step={5}
                title="Final Validation"
                desc="Policy engine re-validates and issues final decision"
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function WorkflowStep({
  step,
  title,
  desc,
}: {
  step: number;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex gap-3">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-mono text-zinc-400 shrink-0">
        {step}
      </span>
      <div>
        <p className="text-sm font-medium text-zinc-300">{title}</p>
        <p className="text-zinc-500 mt-0.5 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}
