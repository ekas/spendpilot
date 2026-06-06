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
            ? "border-cyan-500 bg-cyan-500/5"
            : "border-zinc-700 hover:border-zinc-600 bg-zinc-900/30",
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
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800 mb-4">
          <Upload className="h-5 w-5 text-zinc-400" />
        </div>
        <p className="text-sm font-medium text-zinc-300">
          Drop files here or click to browse
        </p>
        <p className="text-xs text-zinc-500 mt-1">
          Invoices, quotes, contracts, bank statements, spend exports (PDF, TXT, CSV)
        </p>
      </div>

      {documents.length > 0 && (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3"
            >
              <FileText className="h-4 w-4 text-zinc-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-200 truncate">{doc.name}</p>
                <p className="text-xs text-zinc-500">
                  {formatFileSize(doc.size)} · {doc.type.replace("-", " ")}
                </p>
              </div>
              {doc.status === "uploading" || doc.status === "extracting" ? (
                <Loader2 className="h-4 w-4 text-cyan-400 animate-spin shrink-0" />
              ) : doc.status === "ready" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              ) : null}
              {onRemove && (
                <button
                  onClick={() => onRemove(doc.id)}
                  className="text-zinc-600 hover:text-zinc-400 transition-colors"
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
