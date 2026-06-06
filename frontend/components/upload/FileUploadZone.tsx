"use client";

import { useCallback, useState } from "react";
import { Upload, FileText, X, CheckCircle2, Loader2 } from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import type { UploadedDocument } from "@/lib/types";

interface FileUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  documents?: UploadedDocument[];
  onRemove?: (id: string) => void;
  disabled?: boolean;
}

export function FileUploadZone({
  onFilesSelected,
  documents = [],
  onRemove,
  disabled,
}: FileUploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length) onFilesSelected(files);
    },
    [onFilesSelected, disabled]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFilesSelected(files);
    e.target.value = "";
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors",
          dragging
            ? "border-accent bg-accent-muted"
            : "border-border hover:border-accent-border bg-surface",
          disabled && "opacity-50 pointer-events-none"
        )}
      >
        <input
          type="file"
          multiple
          accept=".pdf,.txt,.csv,.doc,.docx"
          onChange={handleChange}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={disabled}
        />
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
          <Upload className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground/90">
          Drop files here or click to browse
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Invoices, quotes, contracts, bank statements, spend exports (PDF, TXT, CSV)
        </p>
      </div>

      {documents.length > 0 && (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
            >
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">{doc.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(doc.size)} · {doc.type.replace("-", " ")}
                </p>
              </div>
              {doc.status === "uploading" || doc.status === "extracting" ? (
                <Loader2 className="h-4 w-4 text-accent animate-spin shrink-0" />
              ) : doc.status === "ready" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              ) : null}
              {onRemove && (
                <button
                  onClick={() => onRemove(doc.id)}
                  className="text-muted-foreground/80 hover:text-muted-foreground transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
