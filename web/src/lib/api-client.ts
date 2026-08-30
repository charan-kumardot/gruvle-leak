"use client";

/**
 * Browser-side calls to this app's own /api/* route handlers, which proxy
 * to the Python worker after verifying (via a fresh Appwrite JWT) that the
 * signed-in user actually belongs to the business/team being acted on —
 * see src/lib/server/auth.ts for that check.
 */
import { account } from "@/lib/appwrite";
import type { ReportFormat } from "@/lib/types";

export class ApiClientError extends Error {}

async function freshJwt(): Promise<string> {
  const { jwt } = await account.createJWT();
  return jwt;
}

export interface DatasetUploadResult {
  dataset_id: string;
  kind: string;
  kind_confidence: number;
  row_count: number;
  column_count: number;
  warnings: string[];
  mapping: Array<{
    raw_name: string;
    canonical_field: string | null;
    confidence: number;
    source: string;
    reason: string;
  }>;
  unmapped_required_fields: string[];
  data_quality_score: number;
  data_quality_explanations: string[];
}

export async function uploadDataset(
  businessId: string,
  teamId: string,
  file: File
): Promise<DatasetUploadResult> {
  const jwt = await freshJwt();
  const form = new FormData();
  form.set("business_id", businessId);
  form.set("team_id", teamId);
  form.set("file", file);

  const res = await fetch("/api/datasets", {
    method: "POST",
    headers: { Authorization: `Bearer ${jwt}` },
    body: form,
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  return res.json();
}

export async function startScan(
  businessId: string,
  teamId: string,
  createdByUserId: string,
  datasetIds: string[],
  currency: string
): Promise<{ scan_id: string }> {
  const jwt = await freshJwt();
  const res = await fetch("/api/scans", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
    body: JSON.stringify({ businessId, teamId, createdByUserId, datasetIds, currency }),
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  return res.json();
}

/** Downloads a report export and triggers a browser save via a temporary object URL. */
export async function downloadReport(scanId: string, teamId: string, format: ReportFormat): Promise<void> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/scans/${encodeURIComponent(scanId)}/report?teamId=${encodeURIComponent(teamId)}&format=${format}`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));

  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  const filename = match?.[1] ?? `scan-${scanId}-report.${format}`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? `Request failed with ${res.status}.`;
  } catch {
    return `Request failed with ${res.status}.`;
  }
}
