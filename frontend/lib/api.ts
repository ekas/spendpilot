import { MOCK_ANALYSIS, MOCK_REVIEW_QUEUE } from "./mock-data";
import type { AnalysisResult, HumanReviewItem, UploadedDocument } from "./types";
import { delay } from "./utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function uploadDocuments(
  files: File[]
): Promise<UploadedDocument[]> {
  if (API_BASE) {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  }

  await delay(1500);
  return files.map((file, i) => ({
    id: `doc-${Date.now()}-${i}`,
    name: file.name,
    type: inferDocumentType(file.name),
    size: file.size,
    uploadedAt: new Date().toISOString(),
    status: "ready" as const,
  }));
}

export async function runAnalysis(
  documents: UploadedDocument[]
): Promise<AnalysisResult> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ documents }),
    });
    if (!res.ok) throw new Error("Analysis failed");
    return res.json();
  }

  await delay(3000);
  return {
    ...MOCK_ANALYSIS,
    snapshot: {
      ...MOCK_ANALYSIS.snapshot,
      documents,
      applicationDate: new Date().toISOString(),
    },
    caseId: `CASE-${Date.now().toString(36).toUpperCase()}`,
    pipelineStage: "complete",
  };
}

export async function getAnalysis(caseId: string): Promise<AnalysisResult> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/cases/${caseId}`);
    if (!res.ok) throw new Error("Case not found");
    return res.json();
  }

  await delay(500);
  return { ...MOCK_ANALYSIS, caseId };
}

export async function getReviewQueue(): Promise<HumanReviewItem[]> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/review-queue`);
    if (!res.ok) throw new Error("Failed to fetch review queue");
    return res.json();
  }

  await delay(300);
  return MOCK_REVIEW_QUEUE;
}

export async function submitReviewDecision(
  reviewId: string,
  decision: "approve" | "challenge" | "override",
  notes?: string
): Promise<void> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/review-queue/${reviewId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, notes }),
    });
    if (!res.ok) throw new Error("Failed to submit decision");
    return;
  }

  await delay(800);
  console.log("Review decision submitted:", { reviewId, decision, notes });
}

function inferDocumentType(filename: string) {
  const lower = filename.toLowerCase();
  if (lower.includes("invoice")) return "invoice" as const;
  if (lower.includes("quote")) return "quote" as const;
  if (lower.includes("contract")) return "contract" as const;
  if (lower.includes("bank") || lower.includes("statement"))
    return "bank-statement" as const;
  if (lower.endsWith(".csv") || lower.includes("spend"))
    return "spend-export" as const;
  return "other" as const;
}
