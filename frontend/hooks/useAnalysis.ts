"use client";

import { useState, useCallback, useRef } from "react";
import { runAnalysis, type ApplicantInput } from "@/lib/api";
import { inferDocumentType } from "@/lib/utils";
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
  const fileMapRef = useRef<Map<string, File>>(new Map());

  const addFiles = useCallback((files: File[]) => {
    setError(null);
    const pending: UploadedDocument[] = files.map((file, i) => {
      const id = `pending-${Date.now()}-${i}`;
      fileMapRef.current.set(id, file);
      return {
        id,
        name: file.name,
        type: inferDocumentType(file.name) as UploadedDocument["type"],
        size: file.size,
        uploadedAt: new Date().toISOString(),
        status: "ready" as const,
      };
    });
    setDocuments((prev) => [...prev, ...pending]);
  }, []);

  const removeDocument = useCallback((id: string) => {
    fileMapRef.current.delete(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const startAnalysis = useCallback(
    async (applicant?: ApplicantInput) => {
      const files = documents
        .map((d) => fileMapRef.current.get(d.id))
        .filter((f): f is File => f !== undefined);

      if (!files.length) return;

      setPhase("analyzing");
      setError(null);

      try {
        const analysis = await runAnalysis(files, applicant);
        setResult(analysis);
        setPhase("complete");
        if (typeof window !== "undefined") {
          sessionStorage.setItem(
            "spendpilot-analysis",
            JSON.stringify(analysis)
          );
        }
        return analysis;
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Analysis failed. Please try again."
        );
        setPhase("error");
      }
    },
    [documents]
  );

  const reset = useCallback(() => {
    setPhase("idle");
    setDocuments([]);
    setResult(null);
    setError(null);
    fileMapRef.current.clear();
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
