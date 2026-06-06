import type { AnalysisResult, HumanReviewItem, UploadedDocument } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function apiUrl(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

export interface ApplicantInput {
  name?: string;
  monthly_income?: number;
  monthly_expenses?: number;
  requested_amount?: number;
  existing_debt?: number;
  credit_utilization?: number;
  delinquencies_12m?: number;
  employment_months?: number;
  overdrafts_90d?: number;
  income_verified?: boolean;
}

export async function uploadDocuments(
  files: File[]
): Promise<UploadedDocument[]> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));

  const res = await fetch(apiUrl("/api/upload"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error("Upload failed");
  const data = await res.json();
  return data.documents ?? data;
}

export async function runAnalysis(
  files: File[],
  applicant?: ApplicantInput
): Promise<AnalysisResult> {
  if (!files.length) {
    const res = await fetch(apiUrl("/api/analyze"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        documents: [],
        applicant: applicant ?? {},
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error ?? "Analysis failed");
    }

    return res.json();
  }

  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));

  if (applicant?.name) formData.append("name", applicant.name);
  if (applicant?.monthly_income !== undefined)
    formData.append("monthly_income", String(applicant.monthly_income));
  if (applicant?.monthly_expenses !== undefined)
    formData.append("monthly_expenses", String(applicant.monthly_expenses));
  if (applicant?.requested_amount !== undefined)
    formData.append("requested_amount", String(applicant.requested_amount));
  if (applicant?.existing_debt !== undefined)
    formData.append("existing_debt", String(applicant.existing_debt));
  if (applicant?.credit_utilization !== undefined)
    formData.append("credit_utilization", String(applicant.credit_utilization));
  if (applicant?.delinquencies_12m !== undefined)
    formData.append("delinquencies_12m", String(applicant.delinquencies_12m));
  if (applicant?.employment_months !== undefined)
    formData.append("employment_months", String(applicant.employment_months));
  if (applicant?.overdrafts_90d !== undefined)
    formData.append("overdrafts_90d", String(applicant.overdrafts_90d));
  if (applicant?.income_verified !== undefined)
    formData.append("income_verified", String(applicant.income_verified));

  const res = await fetch(apiUrl("/api/analyze"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error ?? "Analysis failed");
  }

  return res.json();
}

export async function createCaseWithUpload(
  files: File[],
  applicant: ApplicantInput
): Promise<unknown> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));

  Object.entries(applicant).forEach(([key, value]) => {
    if (value !== undefined) formData.append(key, String(value));
  });

  const res = await fetch(apiUrl("/api/cases/create-with-upload"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error("Case creation failed");
  return res.json();
}

export async function getAnalysis(caseId: string): Promise<AnalysisResult> {
  const res = await fetch(
    apiUrl(`/api/cases/${caseId}?format=analysis`)
  );
  if (!res.ok) throw new Error("Case not found");
  return res.json();
}

export async function getReviewQueue(): Promise<HumanReviewItem[]> {
  const res = await fetch(apiUrl("/api/review-queue"));
  if (!res.ok) throw new Error("Failed to fetch review queue");
  return res.json();
}

export async function submitReviewDecision(
  reviewId: string,
  decision: "approve" | "challenge" | "override",
  notes?: string
): Promise<void> {
  const res = await fetch(apiUrl(`/api/review-queue/${reviewId}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, notes }),
  });
  if (!res.ok) throw new Error("Failed to submit decision");
}

export async function listCases(): Promise<unknown[]> {
  const res = await fetch(apiUrl("/api/cases"));
  if (!res.ok) throw new Error("Failed to list cases");
  return res.json();
}

export async function loadSampleCases(): Promise<unknown[]> {
  const res = await fetch(apiUrl("/api/cases/samples"));
  if (!res.ok) throw new Error("Failed to load samples");
  return res.json();
}

export async function comparePeriods(params: {
  period_a_start: string;
  period_a_end: string;
  period_b_start: string;
  period_b_end: string;
}): Promise<unknown> {
  const qs = new URLSearchParams(params);
  const res = await fetch(apiUrl(`/api/cases/compare-periods?${qs}`));
  if (!res.ok) throw new Error("Failed to compare periods");
  return res.json();
}

export async function checkHealth(): Promise<{
  status: string;
  orm?: string;
  database?: string;
  storage?: string;
}> {
  const res = await fetch(apiUrl("/api/health"));
  if (!res.ok) throw new Error("API unavailable");
  return res.json();
}
