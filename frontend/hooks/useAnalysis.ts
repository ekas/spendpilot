"use client";

import { useState, useCallback } from "react";
import { uploadDocuments, runAnalysis } from "@/lib/api";
import type { AnalysisResult, UploadedDocument } from "@/lib/types";

type AnalysisPhase =
  | "idle"
  | "uploading"
  | "analyzing"
  | "complete"
  | "error";

export function useAnalysis() {
  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addFiles = useCallback(async (files: File[]) => {
    setError(null);
    const pending: UploadedDocument[] = files.map((f, i) => ({
      id: `pending-${Date.now()}-${i}`,
      name: f.name,
      type: "other" as const,
      size: f.size,
      uploadedAt: new Date().toISOString(),
      status: "uploading" as const,
    }));
    setDocuments((prev) => [...prev, ...pending]);

    try {
      const uploaded = await uploadDocuments(files);
      setDocuments((prev) => {
        const withoutPending = prev.filter(
          (d) => !pending.some((p) => p.id === d.id)
        );
        return [...withoutPending, ...uploaded];
      });
    } catch {
      setError("Failed to upload documents");
      setDocuments((prev) =>
        prev.map((d) =>
          pending.some((p) => p.id === d.id)
            ? { ...d, status: "error" as const }
            : d
        )
      );
    }
  }, []);

  const removeDocument = useCallback((id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const startAnalysis = useCallback(async () => {
    if (documents.length === 0) return;
    setPhase("analyzing");
    setError(null);

    try {
      const analysis = await runAnalysis(documents);
      setResult(analysis);
      setPhase("complete");
      if (typeof window !== "undefined") {
        sessionStorage.setItem("spendpilot-analysis", JSON.stringify(analysis));
      }
      return analysis;
    } catch {
      setError("Analysis failed. Please try again.");
      setPhase("error");
    }
  }, [documents]);

  const reset = useCallback(() => {
    setPhase("idle");
    setDocuments([]);
    setResult(null);
    setError(null);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("spendpilot-analysis");
    }
  }, []);

  return {
    phase,
    documents,
    result,
    error,
    addFiles,
    removeDocument,
    startAnalysis,
    reset,
  };
}

export function loadStoredAnalysis(): AnalysisResult | null {
  if (typeof window === "undefined") return null;
  const stored = sessionStorage.getItem("spendpilot-analysis");
  if (!stored) return null;
  try {
    return JSON.parse(stored) as AnalysisResult;
  } catch {
    return null;
  }
}
