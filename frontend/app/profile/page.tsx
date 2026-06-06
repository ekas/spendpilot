"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  User,
  FileText,
  Clock,
  CheckCircle2,
  TrendingUp,
  Shield,
} from "lucide-react";
import { getReviewQueue } from "@/lib/api";
import { HumanReviewQueue } from "@/components/decision/HumanReviewQueue";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { Card, CardHeader } from "@/components/ui/Card";
import { RiskBadge } from "@/components/ui/Badge";
import { loadStoredAnalysis } from "@/hooks/useAnalysis";
import { formatDate } from "@/lib/utils";
import type { AnalysisResult, HumanReviewItem } from "@/lib/types";

export default function ProfilePage() {
  const [items, setItems] = useState<HumanReviewItem[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = async () => {
    const data = await getReviewQueue();
    setItems(data);
    setAnalysis(loadStoredAnalysis());
    setLoading(false);
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const pending = items.filter((i) => i.status !== "resolved").length;
  const resolved = items.filter((i) => i.status === "resolved").length;
  const avgScore =
    items.length > 0
      ? Math.round(
          items.reduce((sum, i) => sum + i.credibilityScore, 0) / items.length
        )
      : analysis?.credibility.overallScore ?? 0;

  const applicantName =
    analysis?.snapshot.applicantName ??
    items[0]?.applicantName ??
    "Applicant";
  const caseId = analysis?.caseId ?? items[0]?.caseId;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-8">
      <Card className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 p-5 sm:p-6">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-accent-muted border border-accent-border">
            <User className="h-7 w-7 text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-foreground truncate">
              {applicantName}
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Applicant profile and case history
            </p>
            {caseId && (
              <p className="text-xs text-muted-foreground/80 font-mono mt-1">
                Latest case: {caseId}
              </p>
            )}
          </div>
          {analysis && (
            <div className="flex items-center gap-3 shrink-0">
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Credibility
                </p>
                <p className="text-2xl font-bold text-foreground tabular-nums">
                  {analysis.credibility.overallScore}
                </p>
              </div>
              <RiskBadge level={analysis.credibility.riskLevel} />
            </div>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Applications"
          value={String(items.length)}
          icon={FileText}
          accent="blue"
        />
        <MetricCard
          label="Active"
          value={String(pending)}
          icon={Clock}
          accent="amber"
        />
        <MetricCard
          label="Resolved"
          value={String(resolved)}
          icon={CheckCircle2}
          accent="emerald"
        />
        <MetricCard
          label="Avg Score"
          value={String(avgScore)}
          icon={TrendingUp}
          accent="violet"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <HumanReviewQueue items={items} onUpdate={loadProfile} />
        </div>

        <div className="space-y-6">
          {analysis ? (
            <Card>
              <CardHeader
                title="Financial Snapshot"
                subtitle="From your latest application"
              />
              <div className="space-y-3 text-sm">
                <SnapshotRow
                  label="Monthly income"
                  value={`$${analysis.snapshot.monthlyIncome.toLocaleString()}`}
                />
                <SnapshotRow
                  label="Monthly expenses"
                  value={`$${analysis.snapshot.monthlyExpenses.toLocaleString()}`}
                />
                <SnapshotRow
                  label="Debt-to-income"
                  value={`${(analysis.snapshot.debtToIncome * 100).toFixed(1)}%`}
                />
                <SnapshotRow
                  label="Savings rate"
                  value={`${(analysis.snapshot.savingsRate * 100).toFixed(1)}%`}
                />
                <SnapshotRow
                  label="Submitted"
                  value={formatDate(analysis.snapshot.applicationDate)}
                />
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <Link
                  href={`/dashboard?case=${analysis.caseId}`}
                  className="inline-flex w-full items-center justify-center rounded-lg border border-border bg-muted px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/80"
                >
                  View Dashboard
                </Link>
              </div>
            </Card>
          ) : (
            <Card>
              <CardHeader
                title="Get Started"
                subtitle="No application on file yet"
              />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Submit documents on the Application page to build your profile
                and run a credibility analysis.
              </p>
              <Link
                href="/"
                className="inline-flex w-full items-center justify-center rounded-lg border border-border bg-muted px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/80 mt-4"
              >
                Start Application
              </Link>
            </Card>
          )}

          <Card>
            <CardHeader
              title="Credibility Breakdown"
              subtitle="Agent scores from latest case"
            />
            {analysis ? (
              <div className="space-y-3">
                <ScoreRow
                  label="Evidence"
                  score={analysis.credibility.evidenceScore}
                />
                <ScoreRow
                  label="Affordability"
                  score={analysis.credibility.affordabilityScore}
                />
                <ScoreRow
                  label="Credit Risk"
                  score={analysis.credibility.creditRiskScore}
                />
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Shield className="h-4 w-4 shrink-0" />
                <span>Run an analysis to see your credibility scores.</span>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function SnapshotRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground tabular-nums">{value}</span>
    </div>
  );
}

function ScoreRow({ label, score }: { label: string; score: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono text-foreground">{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
    </div>
  );
}
