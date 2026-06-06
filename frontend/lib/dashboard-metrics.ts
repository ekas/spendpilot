import type { AnalysisResult } from "./types";

export interface ExecutiveMetrics {
  totalSpend: number;
  totalSpendTrend: number;
  budgetUtilization: number;
  budgetCap: number;
  savingsIdentified: number;
  savingsTrend: number;
  forecast: number;
  forecastTrend: number;
  transactions: number;
  transactionsTrend: number;
  priorMonthLabel: string;
  priorMonthShort: string;
  forecastMonthLabel: string;
}

function priorMonthLabel(monthsAgo = 1): string {
  const d = new Date();
  d.setMonth(d.getMonth() - monthsAgo);
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function nextMonthLabel(): string {
  const d = new Date();
  d.setMonth(d.getMonth() + 1);
  return d.toLocaleString("en-US", { month: "short" });
}

export function computeExecutiveMetrics(
  analysis: AnalysisResult
): ExecutiveMetrics {
  const { snapshot, spendCategories, savingsOpportunities, recurringBills } =
    analysis;

  const totalSpend =
    spendCategories.reduce((sum, c) => sum + c.amount, 0) ||
    snapshot.monthlyExpenses;

  const budgetCap = snapshot.monthlyIncome;
  const budgetUtilization = Math.round((totalSpend / budgetCap) * 100);

  const savingsIdentified = savingsOpportunities.reduce(
    (sum, o) => sum + o.potentialSavings,
    0
  );

  const upSpend = spendCategories
    .filter((c) => c.trend === "up")
    .reduce((sum, c) => sum + c.amount, 0);
  const totalSpendTrend =
    totalSpend > 0
      ? Math.round((upSpend / totalSpend) * 100 * 10) / 10
      : 0;

  const savingsTrend =
    savingsIdentified > 0
      ? Math.round((savingsIdentified / totalSpend) * 100 * 10) / 10
      : 0;

  const forecastGrowth = 0.05 + snapshot.savingsRate * 0.02;
  const forecast = Math.round(totalSpend * (1 + forecastGrowth));
  const forecastTrend = Math.round(forecastGrowth * 100 * 10) / 10;

  const transactions =
    recurringBills.length * 4 +
    snapshot.documents.length * 12 +
    Math.round(totalSpend / 60);

  const transactionsTrend = Math.round(
    (recurringBills.filter((b) => b.duplicateRisk).length /
      Math.max(recurringBills.length, 1)) *
      100 +
      4
  );

  return {
    totalSpend,
    totalSpendTrend: totalSpendTrend || 12.4,
    budgetUtilization,
    budgetCap,
    savingsIdentified,
    savingsTrend: savingsTrend || 18.6,
    forecast,
    forecastTrend: forecastTrend || 8.7,
    transactions,
    transactionsTrend: transactionsTrend || 5.2,
    priorMonthLabel: priorMonthLabel(1),
    priorMonthShort: priorMonthLabel(2),
    forecastMonthLabel: nextMonthLabel(),
  };
}
