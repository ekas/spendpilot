import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export function SubmittedDataPanel({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const data = analysis.submittedData;
  const derived = analysis.derivedFeatures;
  const rows = [
    ["Monthly income", money(data.monthlyIncome)],
    ["Monthly expenses", money(data.monthlyExpenses)],
    ["Requested amount", money(data.requestedAmount)],
    ["Existing debt", money(data.existingDebt)],
    ["Credit utilization", percent(data.creditUtilization)],
    ["Late payments (12 months)", plain(data.delinquencies12m)],
    ["Employment history", months(data.employmentMonths)],
    ["Overdrafts (90 days)", plain(data.overdrafts90d)],
    [
      "Income verification",
      data.incomeVerified === null
        ? "Not provided"
        : data.incomeVerified
          ? "Verified"
          : "Not verified",
    ],
    ["Free cash flow", money(derived.freeCashFlow)],
    ["Expense ratio", percent(derived.expenseRatio)],
    ["Debt / monthly income", percent(derived.debtToMonthlyIncome)],
    ["Estimated 36-month installment", money(derived.estimatedInstallment36m)],
    ["Installment burden", percent(derived.installmentBurden)],
  ];

  return (
    <ChartSection
      title="Submitted And Derived Data"
      subtitle="Submitted values and deterministic calculations used by the workflow"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex items-center justify-between gap-4 border-b border-border-subtle py-2.5 text-xs"
          >
            <span className="text-muted-foreground">{label}</span>
            <span className="text-right font-medium tabular-nums text-foreground">
              {value}
            </span>
          </div>
        ))}
      </div>
    </ChartSection>
  );
}

function money(value: number | null): string {
  return value === null ? "Not provided" : formatCurrency(value);
}

function percent(value: number | null): string {
  return value === null ? "Not provided" : `${(value * 100).toFixed(1)}%`;
}

function plain(value: number | null): string {
  return value === null ? "Not provided" : value.toLocaleString();
}

function months(value: number | null): string {
  return value === null ? "Not provided" : `${value} months`;
}
