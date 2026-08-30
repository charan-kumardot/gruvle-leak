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

// --- Datasets ---

export interface DatasetSummary {
  id: string;
  kind: string;
  original_filename: string;
  file_type: string;
  row_count: number;
  column_count: number;
  source: string;
  processing_status: string;
  created_at: string;
}

export async function listDatasets(businessId: string, teamId: string): Promise<DatasetSummary[]> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/datasets?businessId=${encodeURIComponent(businessId)}&teamId=${encodeURIComponent(teamId)}`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  const body = await res.json();
  return body.datasets;
}

export async function deleteDataset(datasetId: string, teamId: string): Promise<void> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/datasets/${encodeURIComponent(datasetId)}?teamId=${encodeURIComponent(teamId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
}

// --- Account ---

/** Irreversible — deletes the business's data, Team, and the caller's own Appwrite account. */
export async function deleteMyAccount(businessId: string, teamId: string): Promise<void> {
  const jwt = await freshJwt();
  const res = await fetch("/api/account/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
    body: JSON.stringify({ businessId, teamId }),
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
}

// --- Integrations ---

export interface IntegrationProvider {
  key: string;
  label: string;
  available: boolean;
}

export interface IntegrationConnection {
  id: string;
  provider: string;
  display_name: string;
  status: "connected" | "error" | "disconnected";
  last_error?: string | null;
  last_synced_at?: string | null;
  created_at: string;
}

export async function listIntegrationProviders(): Promise<IntegrationProvider[]> {
  const res = await fetch("/api/integrations/providers");
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  const body = await res.json();
  return body.providers;
}

export async function listIntegrationConnections(businessId: string, teamId: string): Promise<IntegrationConnection[]> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/integrations/connections?businessId=${encodeURIComponent(businessId)}&teamId=${encodeURIComponent(teamId)}`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  const body = await res.json();
  return body.connections;
}

export async function connectIntegration(
  businessId: string,
  teamId: string,
  userId: string,
  provider: string,
  credentials: Record<string, string>
): Promise<IntegrationConnection> {
  const jwt = await freshJwt();
  const res = await fetch("/api/integrations/connections", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
    body: JSON.stringify({ businessId, teamId, userId, provider, credentials }),
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  return res.json();
}

export async function disconnectIntegration(connectionId: string, teamId: string): Promise<void> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/integrations/connections/${encodeURIComponent(connectionId)}?teamId=${encodeURIComponent(teamId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
}

export async function syncIntegration(
  connectionId: string,
  businessId: string,
  teamId: string
): Promise<{ dataset_id: string; row_count: number; kind: string; warnings: string[] }> {
  const jwt = await freshJwt();
  const res = await fetch(`/api/integrations/connections/${encodeURIComponent(connectionId)}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
    body: JSON.stringify({ businessId, teamId }),
  });
  if (!res.ok) throw new ApiClientError(await readDetail(res));
  return res.json();
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? `Request failed with ${res.status}.`;
  } catch {
    return `Request failed with ${res.status}.`;
  }
}
