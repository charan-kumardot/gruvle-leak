"use client";

import { useCallback, useId, useRef, useState, type DragEvent } from "react";

export type UploadFileStatus = "ready" | "error";

export interface UploadFile {
  id: string;
  file: File;
  status: UploadFileStatus;
  error?: string;
}

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx", ".xls", ".pdf", ".json", ".txt"];
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB client-side pre-check

export interface FileDropzoneProps {
  files: UploadFile[];
  onFilesChange: (files: UploadFile[]) => void;
  disabled?: boolean;
}

function extensionOf(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx === -1 ? "" : name.slice(idx).toLowerCase();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function validate(file: File): { status: UploadFileStatus; error?: string } {
  const ext = extensionOf(file.name);
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return {
      status: "error",
      error: `Unsupported file type (${ext || "unknown"}). Use CSV, Excel, PDF, JSON or TXT.`,
    };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { status: "error", error: `File is too large (max ${formatBytes(MAX_FILE_SIZE_BYTES)}).` };
  }
  return { status: "ready" };
}

export function FileDropzone({ files, onFilesChange, disabled }: FileDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const addFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      const next: UploadFile[] = Array.from(fileList).map((file) => {
        const { status, error } = validate(file);
        return {
          id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
          file,
          status,
          error,
        };
      });
      onFilesChange([...files, ...next]);
    },
    [files, onFilesChange]
  );

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    addFiles(e.dataTransfer.files);
  }

  function removeFile(id: string) {
    onFilesChange(files.filter((f) => f.id !== id));
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        aria-disabled={disabled}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
          disabled
            ? "cursor-not-allowed border-ink-100 bg-ink-50"
            : isDragging
              ? "border-accent-400 bg-accent-50"
              : "border-ink-200 bg-white hover:border-ink-300"
        }`}
      >
        <UploadIcon />
        <p className="mt-4 text-sm font-medium text-ink-800">
          Drag files here, or click to browse
        </p>
        <p className="mt-1 text-xs text-ink-400">
          CSV, Excel (.xlsx/.xls), PDF, JSON or TXT — up to {formatBytes(MAX_FILE_SIZE_BYTES)} each
        </p>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          multiple
          disabled={disabled}
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="flex flex-col divide-y divide-ink-100 rounded-xl border border-ink-100 bg-white">
          {files.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-900">{f.file.name}</p>
                <p className="mt-0.5 text-xs text-ink-400">
                  {formatBytes(f.file.size)} &middot;{" "}
                  {extensionOf(f.file.name).replace(".", "").toUpperCase() || "—"}
                </p>
                {f.status === "error" && (
                  <p className="mt-0.5 text-xs text-accent-600">{f.error}</p>
                )}
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  f.status === "ready"
                    ? "bg-emerald-50 text-risk-low"
                    : "bg-accent-50 text-risk-high"
                }`}
              >
                {f.status === "ready" ? "Ready" : "Error"}
              </span>
              <button
                type="button"
                onClick={() => removeFile(f.id)}
                className="shrink-0 text-xs font-medium text-ink-400 hover:text-ink-800"
                aria-label={`Remove ${f.file.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-ink-300" aria-hidden="true">
      <path
        d="M12 15V4M12 4l-4 4M12 4l4 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
