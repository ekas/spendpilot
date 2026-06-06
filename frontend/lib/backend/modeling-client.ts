import type { Applicant, CaseResult } from "./schemas";

const DEFAULT_MODELING_API_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 30_000;

function modelingApiUrl(): string {
  return (
    process.env.SPENDPILOT_MODELING_API_URL ?? DEFAULT_MODELING_API_URL
  ).replace(/\/$/, "");
}

export async function runPythonModelingCase(
  applicant: Applicant,
  caseId: string
): Promise<CaseResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${modelingApiUrl()}/modeling/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        case_id: caseId,
        snapshot_id: "snapshot_1",
        applicant,
      }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail =
        typeof error.detail === "string"
          ? error.detail
          : `Modeling API returned ${response.status}`;
      throw new Error(detail);
    }

    return (await response.json()) as CaseResult;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Modeling API timed out after 30 seconds.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getModelingHealth(): Promise<Record<string, unknown>> {
  const response = await fetch(`${modelingApiUrl()}/modeling/health`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Modeling API returned ${response.status}`);
  }
  return response.json();
}
