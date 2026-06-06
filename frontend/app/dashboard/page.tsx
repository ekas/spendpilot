"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  DollarSign,
  TrendingUp,
  CreditCard,
  PiggyBank,
  Upload,
} from "lucide-react";
import { loadStoredAnalysis } from "@/hooks/useAnalysis";
import { getAnalysis } from "@/lib/api";
import { MOCK_ANALYSIS } from "@/lib/mock-data";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

import { CaseSnapshot } from "@/components/upload/CaseSnapshot";
import { AgentPipeline } from "@/components/agents/AgentPipeline";
import { AgentCard } from "@/components/agents/AgentCard";
import { AgentCommunicationFeed } from "@/components/agents/AgentCommunicationFeed";
import { CredibilityScore } from "@/components/dashboard/CredibilityScore";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { SpendBreakdown } from "@/components/dashboard/SpendBreakdown";
import { RecurringBills } from "@/components/dashboard/RecurringBills";
import { SavingsOpportunities } from "@/components/dashboard/SavingsOpportunities";
import { ConflictDetection } from "@/components/decision/ConflictDetection";
import { PolicyValidation } from "@/components/decision/PolicyValidation";
import { DecisionPanel } from "@/components/decision/DecisionPanel";
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
        const data = await getAnalysis(caseId);
        setAnalysis(data);
      } else {
        setAnalysis(MOCK_ANALYSIS);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          <p className="text-sm text-zinc-500">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-zinc-400">No analysis data available.</p>
        <Button onClick={() => router.push("/")}>
          <Upload className="h-4 w-4" />
          Start Application
        </Button>
      </div>
    );
  }

  const { snapshot, credibility } = analysis;
  const specialistReports = analysis.agentReports.filter(
    (r) => r.agentId !== "manager"
  );
  const managerReport = analysis.agentReports.find(
    (r) => r.agentId === "manager"
  );

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">
            CFO Dashboard
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {snapshot.applicantName} · {analysis.caseId}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => router.push("/")}>
          <Upload className="h-3.5 w-3.5" />
          New Application
        </Button>
      </div>

      {/* Pipeline */}
      <div className="mb-6 overflow-x-auto">
        <AgentPipeline currentStage={analysis.pipelineStage} />
      </div>

      {/* Top metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Monthly Income"
          value={formatCurrency(snapshot.monthlyIncome)}
          icon={DollarSign}
          accent="emerald"
          trend="stable"
          trendLabel="Verified via contract"
        />
        <MetricCard
          label="Monthly Expenses"
          value={formatCurrency(snapshot.monthlyExpenses)}
          icon={CreditCard}
          accent="rose"
          trend="up"
          trendLabel="Subscriptions +23%"
        />
        <MetricCard
          label="Savings Rate"
          value={formatPercent(snapshot.savingsRate * 100)}
          icon={PiggyBank}
          accent="cyan"
          trend="up"
          trendLabel="Above 15% benchmark"
        />
        <MetricCard
          label="Debt-to-Income"
          value={formatPercent(snapshot.debtToIncome * 100)}
          icon={TrendingUp}
          accent="violet"
          trend="stable"
          trendLabel="Below 35% threshold"
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-1">
          <CredibilityScore credibility={credibility} />
        </div>
        <div className="lg:col-span-2">
          <CaseSnapshot snapshot={snapshot} />
        </div>
      </div>

      {/* Agent reports */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-3 uppercase tracking-wider">
          Specialist Agent Reports
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {specialistReports.map((report) => (
            <AgentCard key={report.agentId} report={report} />
          ))}
        </div>
      </div>

      {/* Manager + Communication */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {managerReport && (
          <AgentCard report={managerReport} defaultExpanded />
        )}
        <AgentCommunicationFeed messages={analysis.agentMessages} />
      </div>

      {/* CFO financial cards */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-3 uppercase tracking-wider">
          Financial Analysis
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <SpendBreakdown categories={analysis.spendCategories} />
          <RecurringBills bills={analysis.recurringBills} />
          <SavingsOpportunities
            opportunities={analysis.savingsOpportunities}
          />
        </div>
      </div>

      {/* Decision layer */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-3 uppercase tracking-wider">
          Decision Layer
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <ConflictDetection conflicts={analysis.conflicts} />
          <PolicyValidation checks={analysis.policyChecks} />
        </div>
        <DecisionPanel decision={analysis.decision} />
      </div>
    </div>
  );
}
