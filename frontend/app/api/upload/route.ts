import { NextResponse } from "next/server";
import { inferDocumentType } from "@/lib/backend/document-intelligence";
import type { UploadedDocument } from "@/lib/types";

export async function POST(request: Request) {
  const form = await request.formData();
  const files = form.getAll("files").filter((f) => f instanceof File) as File[];

  if (!files.length) {
    return NextResponse.json({ error: "No files provided" }, { status: 400 });
  }

  const sessionId = crypto.randomUUID().slice(0, 8);
  const documents: UploadedDocument[] = files.map((file, i) => ({
    id: `doc-${sessionId}-${i}`,
    name: file.name,
    type: inferDocumentType(file.name) as UploadedDocument["type"],
    size: file.size,
    uploadedAt: new Date().toISOString(),
    status: "ready",
  }));

  return NextResponse.json({ sessionId, documents });
}
