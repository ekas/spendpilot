const MAX_READ_BYTES = 2 * 1024 * 1024;

const NUMBER_PATTERNS: Record<string, RegExp[]> = {
  monthly_income: [
    /monthly[_\s-]*income\D*([0-9]+(?:\.[0-9]+)?)/i,
    /income\D*([0-9]+(?:\.[0-9]+)?)/i,
  ],
  monthly_expenses: [
    /monthly[_\s-]*expenses\D*([0-9]+(?:\.[0-9]+)?)/i,
    /expenses\D*([0-9]+(?:\.[0-9]+)?)/i,
  ],
  existing_debt: [
    /existing[_\s-]*debt\D*([0-9]+(?:\.[0-9]+)?)/i,
    /debt\D*([0-9]+(?:\.[0-9]+)?)/i,
  ],
  credit_utilization: [
    /credit[_\s-]*utilization\D*([0-9]+(?:\.[0-9]+)?)/i,
    /utilization\D*([0-9]+(?:\.[0-9]+)?)/i,
  ],
  delinquencies_12m: [
    /delinquencies[_\s-]*12m\D*([0-9]+)/i,
    /delinquencies\D*([0-9]+)/i,
  ],
  employment_months: [
    /employment[_\s-]*months\D*([0-9]+)/i,
    /employment\D*([0-9]+)\s*months/i,
  ],
  overdrafts_90d: [
    /overdrafts[_\s-]*90d\D*([0-9]+)/i,
    /overdrafts\D*([0-9]+)/i,
  ],
};

export interface UploadedFileInput {
  filename: string;
  buffer: Buffer;
}

export interface DocumentAnalysis {
  evidence_refs: string[];
  document_text: string;
  document_signals: {
    numeric_hints: Record<string, number>;
    consistency_flags: string[];
    coverage_score: number;
    income_verified_from_docs: boolean;
    unreadable_files: string[];
    stored_paths?: string[];
  };
}

function safeDecode(raw: Buffer): string {
  return raw.toString("utf-8");
}

function extractFromCsv(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  const lines = text.trim().split("\n");
  if (lines.length < 2) return out;

  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const values = lines[1].split(",").map((v) => v.trim());

  for (const key of Object.keys(NUMBER_PATTERNS)) {
    const idx = headers.findIndex((h) => h.includes(key.replace(/_/g, "")) || h === key);
    if (idx >= 0 && values[idx]) {
      const num = parseFloat(values[idx]);
      if (!isNaN(num)) out[key] = num;
    }
    if (headers.includes(key) && values[headers.indexOf(key)]) {
      const num = parseFloat(values[headers.indexOf(key)]);
      if (!isNaN(num)) out[key] = num;
    }
  }

  return out;
}

function extractFromJson(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  try {
    const payload = JSON.parse(text);
    const source = Array.isArray(payload) ? payload[0] : payload;
    if (!source || typeof source !== "object") return out;

    for (const key of Object.keys(NUMBER_PATTERNS)) {
      if (key in source) {
        const num = parseFloat(String(source[key]));
        if (!isNaN(num)) out[key] = num;
      }
    }
  } catch {
    // ignore
  }
  return out;
}

function extractWithRegex(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [key, patterns] of Object.entries(NUMBER_PATTERNS)) {
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match?.[1]) {
        const num = parseFloat(match[1]);
        if (!isNaN(num)) {
          out[key] = num;
          break;
        }
      }
    }
  }
  return out;
}

function normalizeHints(hints: Record<string, number>): Record<string, number> {
  const normalized = { ...hints };
  if (normalized.credit_utilization !== undefined) {
    const util = normalized.credit_utilization;
    normalized.credit_utilization = util > 1 ? util / 100 : util;
  }
  for (const intKey of [
    "delinquencies_12m",
    "employment_months",
    "overdrafts_90d",
  ] as const) {
    if (normalized[intKey] !== undefined) {
      normalized[intKey] = Math.round(normalized[intKey]);
    }
  }
  return normalized;
}

function signalsFromText(text: string) {
  const lowered = text.toLowerCase();
  const incomeVerified =
    lowered.includes("income verified") || lowered.includes("verified income");
  const consistencyFlags: string[] = [];

  if (lowered.includes("fraud") || lowered.includes("forg")) {
    consistencyFlags.push("POTENTIAL_FRAUD_SIGNAL");
  }
  if (lowered.includes("inconsistent") || lowered.includes("mismatch")) {
    consistencyFlags.push("DOCUMENT_DATA_MISMATCH");
  }

  return {
    income_verified_from_docs: incomeVerified,
    consistency_flags: consistencyFlags,
    numeric_hints: extractWithRegex(text),
  };
}

export function analyzeUploadedDocuments(
  files: UploadedFileInput[]
): DocumentAnalysis {
  const evidenceRefs: string[] = [];
  const allTextParts: string[] = [];
  const mergedHints: Record<string, number> = {};
  const consistencyFlags: string[] = [];
  const unreadableFiles: string[] = [];

  for (const file of files) {
    const filename = file.filename || "unnamed_document";
    evidenceRefs.push(filename);

    const raw = file.buffer.subarray(0, MAX_READ_BYTES);
    const ext = filename.split(".").pop()?.toLowerCase() ?? "";

    if (!raw.length) {
      unreadableFiles.push(filename);
      continue;
    }

    const text = safeDecode(raw);
    if (!text.trim() && [".pdf", ".png", ".jpg", ".jpeg"].some((e) => ext === e.slice(1))) {
      unreadableFiles.push(filename);
      continue;
    }

    allTextParts.push(text);

    let perFileHints: Record<string, number> = {};
    if (ext === "json") perFileHints = extractFromJson(text);
    else if (ext === "csv") perFileHints = extractFromCsv(text);

    const signal = signalsFromText(text);
    perFileHints = { ...perFileHints, ...signal.numeric_hints };

    Object.assign(mergedHints, perFileHints);
    for (const flag of signal.consistency_flags) {
      if (!consistencyFlags.includes(flag)) consistencyFlags.push(flag);
    }
  }

  const normalizedHints = normalizeHints(mergedHints);
  const joinedText = allTextParts.join("\n");
  const coverageScore = Math.min(1, Object.keys(normalizedHints).length / 7);
  const loweredAll = joinedText.toLowerCase();
  const incomeVerifiedFromDocs =
    loweredAll.includes("income verified") ||
    loweredAll.includes("verified income");

  return {
    evidence_refs: evidenceRefs,
    document_text: joinedText.slice(0, 12000),
    document_signals: {
      numeric_hints: normalizedHints,
      consistency_flags: consistencyFlags,
      coverage_score: Math.round(coverageScore * 100) / 100,
      income_verified_from_docs: incomeVerifiedFromDocs,
      unreadable_files: unreadableFiles,
    },
  };
}

export { inferDocumentType } from "@/lib/utils";
