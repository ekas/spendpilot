import { NextResponse } from "next/server";
import { runCase } from "@/lib/backend/case-runner";
import {
  analyzeUploadedDocuments,
  inferDocumentType,
} from "@/lib/backend/document-intelligence";
import { saveDocumentRecord } from "@/lib/backend/case-repository";
import { uploadToStorage } from "@/lib/supabase/storage";
import { caseResultToAnalysis } from "@/lib/backend/transform";
import { applicantFromHints } from "@/lib/backend/api-helpers";
import { parseApplicantFromForm } from "@/lib/backend/api-helpers";
import type { UploadedDocument } from "@/lib/types";

interface AnalyzeBody {
  documents?: UploadedDocument[];
  applicant?: {
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
  };
  files?: { name: string; content: string }[];
}

export async function POST(request: Request) {
  try {
    const contentType = request.headers.get("content-type") ?? "";

    if (contentType.includes("multipart/form-data")) {
      return handleMultipart(request);
    }

    const body = (await request.json()) as AnalyzeBody;
    return handleJson(body);
  } catch (err) {
    console.error("analyze error:", err);
    return NextResponse.json({ error: "Analysis failed" }, { status: 500 });
  }
}

async function handleMultipart(request: Request) {
  const form = await request.formData();
  const files = form.getAll("files").filter((f) => f instanceof File) as File[];

  if (!files.length) {
    return NextResponse.json({ error: "No files provided" }, { status: 400 });
  }

  const caseId = crypto.randomUUID().slice(0, 8);
  const fileInputs = await Promise.all(
    files.map(async (file) => ({
      filename: file.name,
      buffer: Buffer.from(await file.arrayBuffer()),
    }))
  );

  const analysis = analyzeUploadedDocuments(fileInputs);
  const uploadedDocs: UploadedDocument[] = [];
  const storedPaths: string[] = [];

  for (let i = 0; i < fileInputs.length; i++) {
    const file = fileInputs[i];
    const path = await uploadToStorage(caseId, file.filename, file.buffer);
    if (path) storedPaths.push(path);

    uploadedDocs.push({
      id: `doc-${caseId}-${i}`,
      name: file.filename,
      type: inferDocumentType(file.filename) as UploadedDocument["type"],
      size: file.buffer.length,
      uploadedAt: new Date().toISOString(),
      status: "ready",
    });

    await saveDocumentRecord({
      case_id: caseId,
      file_name: file.filename,
      file_type: inferDocumentType(file.filename),
      file_size: file.buffer.length,
      storage_path: path ?? undefined,
      document_signals: analysis.document_signals,
    });
  }

  const hintedApplicant = applicantFromHints(
    String(form.get("name") ?? "Applicant"),
    analysis.document_signals.numeric_hints,
    analysis.evidence_refs,
  );
  const applicant = parseApplicantFromForm(form, hintedApplicant);
  applicant.documents = analysis.evidence_refs;

  applicant.document_text = analysis.document_text;
  applicant.document_signals = {
    ...analysis.document_signals,
    stored_paths: storedPaths,
  };
  if (analysis.document_signals.income_verified_from_docs) {
    applicant.income_verified = true;
  }

  const result = await runCase(applicant, caseId);
  return NextResponse.json(caseResultToAnalysis(result));
}

async function handleJson(body: AnalyzeBody) {
  const caseId = crypto.randomUUID().slice(0, 8);
  const documentNames = body.documents?.map((d) => d.name) ?? [];

  let fileInputs: { filename: string; buffer: Buffer }[] = [];

  if (body.files?.length) {
    fileInputs = body.files.map((f) => ({
      filename: f.name,
      buffer: Buffer.from(f.content, "utf-8"),
    }));
  }

  const analysis = fileInputs.length
    ? analyzeUploadedDocuments(fileInputs)
    : {
        evidence_refs: documentNames,
        document_text: "",
        document_signals: {
          numeric_hints: {} as Record<string, number>,
          consistency_flags: [] as string[],
          coverage_score: 0,
          income_verified_from_docs: false,
          unreadable_files: [] as string[],
        },
      };

  const applicantData = body.applicant ?? {};
  const mergedHints: Record<string, number | undefined> = {
    ...analysis.document_signals.numeric_hints,
  };
  if (applicantData.monthly_income !== undefined)
    mergedHints.monthly_income = applicantData.monthly_income;
  if (applicantData.monthly_expenses !== undefined)
    mergedHints.monthly_expenses = applicantData.monthly_expenses;
  if (applicantData.existing_debt !== undefined)
    mergedHints.existing_debt = applicantData.existing_debt;
  if (applicantData.credit_utilization !== undefined)
    mergedHints.credit_utilization = applicantData.credit_utilization;
  if (applicantData.delinquencies_12m !== undefined)
    mergedHints.delinquencies_12m = applicantData.delinquencies_12m;
  if (applicantData.employment_months !== undefined)
    mergedHints.employment_months = applicantData.employment_months;
  if (applicantData.overdrafts_90d !== undefined)
    mergedHints.overdrafts_90d = applicantData.overdrafts_90d;

  const applicant = applicantFromHints(
    applicantData.name ?? "Applicant",
    mergedHints,
    analysis.evidence_refs.length ? analysis.evidence_refs : documentNames
  );

  if (applicantData.monthly_income)
    applicant.monthly_income = applicantData.monthly_income;
  if (applicantData.monthly_expenses)
    applicant.monthly_expenses = applicantData.monthly_expenses;
  if (applicantData.requested_amount)
    applicant.requested_amount = applicantData.requested_amount;
  if (applicantData.existing_debt)
    applicant.existing_debt = applicantData.existing_debt;
  if (applicantData.credit_utilization !== undefined)
    applicant.credit_utilization = applicantData.credit_utilization;
  if (applicantData.delinquencies_12m !== undefined)
    applicant.delinquencies_12m = applicantData.delinquencies_12m;
  if (applicantData.employment_months !== undefined)
    applicant.employment_months = applicantData.employment_months;
  if (applicantData.overdrafts_90d !== undefined)
    applicant.overdrafts_90d = applicantData.overdrafts_90d;
  if (applicantData.income_verified !== undefined)
    applicant.income_verified = applicantData.income_verified;

  applicant.document_text = analysis.document_text;
  applicant.document_signals = analysis.document_signals;

  if (analysis.document_signals.income_verified_from_docs) {
    applicant.income_verified = true;
  }

  const result = await runCase(applicant, caseId);
  return NextResponse.json(caseResultToAnalysis(result));
}
