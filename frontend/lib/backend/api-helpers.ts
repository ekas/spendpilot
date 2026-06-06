import { NextResponse } from "next/server";
import type { Applicant } from "./schemas";

export function jsonError(message: string, status: number) {
  return NextResponse.json({ error: message }, { status });
}

export function parseApplicantFromForm(
  form: FormData,
  defaults?: Partial<Applicant>
): Applicant {
  const getNum = (key: string, fallback: number) => {
    const v = form.get(key);
    if (v === null || v === "") return fallback;
    return parseFloat(String(v));
  };

  const getInt = (key: string, fallback: number) => {
    const v = form.get(key);
    if (v === null || v === "") return fallback;
    return parseInt(String(v), 10);
  };

  const getBool = (key: string, fallback: boolean) => {
    const v = form.get(key);
    if (v === null || v === "") return fallback;
    return String(v).toLowerCase() === "true";
  };

  return {
    name: String(form.get("name") ?? defaults?.name ?? "Applicant"),
    monthly_income: getNum("monthly_income", defaults?.monthly_income ?? 4500),
    monthly_expenses: getNum(
      "monthly_expenses",
      defaults?.monthly_expenses ?? 2800
    ),
    requested_amount: getNum(
      "requested_amount",
      defaults?.requested_amount ?? 8000
    ),
    existing_debt: getNum("existing_debt", defaults?.existing_debt ?? 1200),
    credit_utilization: getNum(
      "credit_utilization",
      defaults?.credit_utilization ?? 0.35
    ),
    delinquencies_12m: getInt(
      "delinquencies_12m",
      defaults?.delinquencies_12m ?? 0
    ),
    employment_months: getInt(
      "employment_months",
      defaults?.employment_months ?? 18
    ),
    overdrafts_90d: getInt("overdrafts_90d", defaults?.overdrafts_90d ?? 0),
    income_verified: getBool(
      "income_verified",
      defaults?.income_verified ?? false
    ),
    documents: [],
  };
}

export function applicantFromHints(
  name: string,
  hints: Record<string, number | undefined>,
  documentNames: string[]
): Applicant {
  const num = (key: string, fallback: number) => {
    const v = hints[key];
    return v !== undefined && !isNaN(v) ? v : fallback;
  };

  const existingDebt = num("existing_debt", 1200);

  return {
    name,
    monthly_income: num("monthly_income", 4500),
    monthly_expenses: num("monthly_expenses", 2800),
    requested_amount: existingDebt > 0 ? existingDebt * 0.5 : 8000,
    existing_debt: existingDebt,
    credit_utilization: num("credit_utilization", 0.35),
    delinquencies_12m: num("delinquencies_12m", 0),
    employment_months: num("employment_months", 18),
    overdrafts_90d: num("overdrafts_90d", 0),
    income_verified: false,
    documents: documentNames,
  };
}
