"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  PieChart,
  DollarSign,
  LineChart,
  CreditCard,
  Upload,
  FileText,
} from "lucide-react";
import { loadStoredAnalysis } from "@/hooks/useAnalysis";
import { getAnalysis, getMockAnalysis } from "@/lib/api";
import { computeExecutiveMetrics } from "@/lib/dashboard-metrics";
import { formatCompactCurrency, formatPercent } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

import { MetricCard } from "@/components/dashboard/MetricCard";
import { SpendByCategoryChart } from "@/components/dashboard/SpendByCategoryChart";
import { SpendOverTimeChart } from "@/components/dashboard/SpendOverTimeChart";
import { SpecialistAgentPanel } from "@/components/dashboard/SpecialistAgentPanel";
import { ManagerSummaryPanel } from "@/components/dashboard/ManagerSummaryPanel";
import { DecisionEvolutionChart } from "@/components/dashboard/DecisionEvolutionChart";
import { CounterfactualChart } from "@/components/dashboard/CounterfactualChart";
import { RiskDriversChart } from "@/components/dashboard/RiskDriversChart";
import { ReasonCodeChart } from "@/components/dashboard/ReasonCodeChart";
import { PolicyEnginePanel } from "@/components/dashboard/PolicyEnginePanel";
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
        setAnalysis(getMockAnalysis());
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
        <p className="text-muted-foreground">No analysis data available.</p>
        <Button onClick={() => router.push("/")}>
          <Upload className="h-4 w-4" />
          Start Application
        </Button>
      </div>
    );
  }

  const { snapshot } = analysis;
  const specialistReports = analysis.agentReports.filter(
    (r) => r.agentId !== "manager"
  );
  const metrics = computeExecutiveMetrics(analysis);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">
            Executive Overview
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Explainable affordability, evidence, and credit assessment ·{" "}
            {snapshot.applicantName}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm">
            <FileText className="h-3.5 w-3.5" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Top tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
        <MetricCard
          label="Monthly Expenses"
          value={formatCompactCurrency(metrics.totalSpend)}
          icon={User}
          accent="violet"
          trend="up"
          trendPercent={`${formatPercent(metrics.totalSpendTrend)}`}
          trendLabel={`vs ${metrics.priorMonthLabel}`}
        />
        <MetricCard
          label="Income Used"
          value={formatPercent(metrics.budgetUtilization, 0)}
          icon={PieChart}
          accent="emerald"
          progress={metrics.budgetUtilization}
          progressSubtext={`${formatCompactCurrency(metrics.totalSpend)} of ${formatCompactCurrency(metrics.budgetCap)}`}
        />
        <MetricCard
          label="Savings Identified"
          value={formatCompactCurrency(metrics.savingsIdentified)}
          icon={DollarSign}
          accent="blue"
          trend="up"
          trendPercent={`${formatPercent(metrics.savingsTrend)}`}
          trendLabel={`vs ${metrics.priorMonthLabel}`}
        />
        <MetricCard
          label={`Forecast (${metrics.forecastMonthLabel})`}
          value={formatCompactCurrency(metrics.forecast)}
          icon={LineChart}
          accent="amber"
          trend="up"
          trendPercent={`${formatPercent(metrics.forecastTrend)}`}
          trendLabel={`vs ${metrics.priorMonthShort}`}
        />
        <MetricCard
          label="Evidence Items"
          value={snapshot.documents.length.toLocaleString()}
          icon={CreditCard}
          accent="rose"
          progress={snapshot.validationStatus === "valid" ? 100 : 50}
          progressSubtext={snapshot.validationStatus.replace("-", " ")}
        />
      </div>

      {/* Spend charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <SpendByCategoryChart analysis={analysis} />
        <SpendOverTimeChart analysis={analysis} />
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
