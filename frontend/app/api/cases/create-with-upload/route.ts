import { NextResponse } from "next/server";
import { runCase } from "@/lib/backend/case-runner";
import {
  analyzeUploadedDocuments,
  inferDocumentType,
} from "@/lib/backend/document-intelligence";
import { saveDocumentRecord } from "@/lib/backend/case-repository";
import { uploadToStorage } from "@/lib/supabase/storage";
import { jsonError, parseApplicantFromForm } from "@/lib/backend/api-helpers";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const files = form.getAll("files").filter((f) => f instanceof File) as File[];

    if (!files.length) {
      return jsonError("At least one file is required", 400);
    }

    const caseId = crypto.randomUUID().slice(0, 8);
    const applicant = parseApplicantFromForm(form);

    const fileInputs = await Promise.all(
      files.map(async (file) => ({
        filename: file.name,
        buffer: Buffer.from(await file.arrayBuffer()),
      }))
    );

    const analysis = analyzeUploadedDocuments(fileInputs);
    const storedPaths: string[] = [];

    for (const file of fileInputs) {
      const path = await uploadToStorage(caseId, file.filename, file.buffer);
      if (path) storedPaths.push(path);

      await saveDocumentRecord({
        case_id: caseId,
        file_name: file.filename,
        file_type: inferDocumentType(file.filename),
        file_size: file.buffer.length,
        storage_path: path ?? undefined,
        extracted_text: analysis.document_text.slice(0, 5000),
        document_signals: analysis.document_signals,
      });
    }

    const hints = analysis.document_signals.numeric_hints;
    if (hints.monthly_income) applicant.monthly_income = hints.monthly_income;
    if (hints.monthly_expenses)
      applicant.monthly_expenses = hints.monthly_expenses;
    if (hints.existing_debt) applicant.existing_debt = hints.existing_debt;
    if (hints.credit_utilization !== undefined)
      applicant.credit_utilization = hints.credit_utilization;
    if (hints.delinquencies_12m !== undefined)
      applicant.delinquencies_12m = hints.delinquencies_12m;
    if (hints.employment_months !== undefined)
      applicant.employment_months = hints.employment_months;
    if (hints.overdrafts_90d !== undefined)
      applicant.overdrafts_90d = hints.overdrafts_90d;

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
    return NextResponse.json(result);
  } catch (err) {
    console.error("create-with-upload error:", err);
    return jsonError("Failed to process upload", 500);
  }
}
