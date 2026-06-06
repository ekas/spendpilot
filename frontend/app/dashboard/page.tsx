"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Banknote,
  WalletCards,
  Percent,
  Gauge,
  Scale,
  Upload,
  Download,
} from "lucide-react";
import { loadStoredAnalysis } from "@/hooks/useAnalysis";
import { getAnalysis } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

import { MetricCard } from "@/components/dashboard/MetricCard";
import { SpecialistAgentPanel } from "@/components/dashboard/SpecialistAgentPanel";
import { ManagerSummaryPanel } from "@/components/dashboard/ManagerSummaryPanel";
import { DecisionEvolutionChart } from "@/components/dashboard/DecisionEvolutionChart";
import { CounterfactualChart } from "@/components/dashboard/CounterfactualChart";
import { RiskDriversChart } from "@/components/dashboard/RiskDriversChart";
import { ReasonCodeChart } from "@/components/dashboard/ReasonCodeChart";
import { PolicyEnginePanel } from "@/components/dashboard/PolicyEnginePanel";
import { SubmittedDataPanel } from "@/components/dashboard/SubmittedDataPanel";
import { EvidencePanel } from "@/components/dashboard/EvidencePanel";
import { Button } from "@/components/ui/Button";

export default function DashboardPage() {
  const router = useRouter();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const stored = loadStoredAnalysis();
      if (stored) {
        setAnalysis(stored);
        setLoading(false);
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const caseId = params.get("case");
      if (caseId) {
        try {
          const data = await getAnalysis(caseId);
          setAnalysis(data);
        } catch {
          setAnalysis(null);
        }
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-foreground">
            Start an application
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Submit applicant data and evidence to generate an underwriting
            result.
          </p>
        </div>
        <Button onClick={() => router.push("/")}>
          <Upload className="h-4 w-4" />
          Start Application
        </Button>
      </div>
    );
  }

  const specialistReports = analysis.agentReports;
  const averageRisk =
    specialistReports.reduce((sum, report) => sum + report.adverseRisk, 0) /
    specialistReports.length;
  const exportAudit = () => {
    const blob = new Blob(
      [JSON.stringify(analysis.auditBundle, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `spendpilot-${analysis.caseId}-audit.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">
            Underwriting Review
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Case {analysis.caseId} · snapshot{" "}
            {analysis.caseContext.snapshotId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={exportAudit}>
            <Download className="h-3.5 w-3.5" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Top tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
        <MetricCard
          label="Requested Amount"
          value={formatMoney(analysis.submittedData.requestedAmount)}
          icon={Banknote}
          accent="violet"
        />
        <MetricCard
          label="Free Cash Flow"
          value={formatMoney(analysis.derivedFeatures.freeCashFlow)}
          icon={WalletCards}
          accent="emerald"
        />
        <MetricCard
          label="Expense Ratio"
          value={formatRatio(analysis.derivedFeatures.expenseRatio)}
          icon={Percent}
          accent="blue"
        />
        <MetricCard
          label="Average Adverse Risk"
          value={`${(averageRisk * 100).toFixed(1)}%`}
          icon={Gauge}
          accent="amber"
          progress={averageRisk * 100}
          progressSubtext="Mean of the three specialist probabilities"
        />
        <MetricCard
          label="Decision Status"
          value={
            analysis.decision.requiresHumanReview
              ? "Review required"
              : analysis.decision.label
          }
          icon={Scale}
          accent="rose"
          progressSubtext={
            analysis.decision.finalized
              ? "Finalized"
              : "Awaiting authorized reviewer"
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <SubmittedDataPanel analysis={analysis} />
        <EvidencePanel analysis={analysis} />
      </div>

      {/* Agent panels */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {specialistReports.map((report) => (
          <SpecialistAgentPanel key={report.agentId} report={report} />
        ))}
        <ManagerSummaryPanel analysis={analysis} />
      </div>

      {/* Decision analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <DecisionEvolutionChart analysis={analysis} />
        <CounterfactualChart analysis={analysis} />
      </div>

      {/* Risk & policy */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
        <RiskDriversChart analysis={analysis} />
        <ReasonCodeChart analysis={analysis} />
        <PolicyEnginePanel analysis={analysis} />
      </div>
    </div>
  );
}

function formatMoney(value: number | null): string {
  return value === null ? "Not provided" : formatCurrency(value);
}

function formatRatio(value: number | null): string {
  return value === null ? "Not provided" : `${(value * 100).toFixed(1)}%`;
}
