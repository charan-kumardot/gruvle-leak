/**
 * Typed calling convention for the Python FastAPI worker (localhost:8000 in
 * dev). SERVER-SIDE ONLY — `WORKER_API_URL` and `WORKER_API_INTERNAL_TOKEN`
 * have no `NEXT_PUBLIC_` prefix on purpose, so this module must only be
 * imported from Route Handlers / Server Components, never a "use client"
 * file. Every function here assumes the CALLER has already verified (via
 * `lib/server/auth.ts`) that the requesting user actually belongs to the
 * business/team_id being passed in — this module does not re-check that.
 *
 * No detection/calculation logic belongs here — this file only shapes and
 * moves data to/from the real, live worker endpoints (see worker/app/api/).
 *
 * Only operations that genuinely need the Python worker live here: uploading
 * + parsing a file, running detection, rendering a report export, and
 * managing data source connections (Shopify etc. — these hold a live
 * external API credential the browser must never see, so the worker is the
 * only thing that ever reads/writes them). Everything else (listing scans,
 * reading findings, confirming / dismissing a finding) reads and writes
 * Appwrite directly from the client via the Web SDK (see
 * src/lib/scans-client.ts) — those documents are already team-permissioned
 * in Appwrite, so proxying them through here would just be reimplementing
 * access control Appwrite already enforces.
 */
import "server-only";

import type { Finding, ReportFormat } from "@/lib/types";

const WORKER_API_URL = process.env.WORKER_API_URL ?? "http://localhost:8000";
const WORKER_API_INTERNAL_TOKEN = process.env.WORKER_API_INTERNAL_TOKEN ?? "";

export class WorkerApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly endpoint?: string
  ) {
    super(message);
    this.name = "WorkerApiError";
  }
}

async function workerFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${WORKER_API_URL}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "X-Internal-Token": WORKER_API_INTERNAL_TOKEN,
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch (err) {
    throw new WorkerApiError(
      `Could not reach the worker service at ${url}. (${(err as Error).message})`,
      undefined,
      path
    );
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new WorkerApiError(
      `Worker request to ${path} failed with ${res.status}${detail ? `: ${detail}` : ""}`,
      res.status,
      path
    );
  }

  return res;
}

async function workerJson<T>(path: string, init?: RequestInit): Promise<T> {
  return (await workerFetch(path, init)).json() as Promise<T>;
}

export interface UploadDatasetParams {
  businessId: string;
  teamId: string;
  file: Blob;
  fileName: string;
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

/** POST /datasets/upload — parse, profile, and map one uploaded file. */
export async function uploadDataset(params: UploadDatasetParams): Promise<DatasetUploadResult> {
  const form = new FormData();
  form.append("business_id", params.businessId);
  form.append("team_id", params.teamId);
  form.append("file", params.file, params.fileName);

  return workerJson<DatasetUploadResult>("/datasets/upload", { method: "POST", body: form });
}

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

/** GET /datasets — list datasets already uploaded/synced for a business. */
export async function listDatasets(businessId: string, teamId: string): Promise<DatasetSummary[]> {
  const data = await workerJson<{ datasets: DatasetSummary[] }>(
    `/datasets?business_id=${encodeURIComponent(businessId)}&team_id=${encodeURIComponent(teamId)}`
  );
  return data.datasets;
}

/** DELETE /datasets/:id — removes a dataset and its profile/mapping (past scans/findings are untouched). */
export async function deleteDataset(datasetId: string, teamId: string): Promise<void> {
  await workerFetch(`/datasets/${encodeURIComponent(datasetId)}?team_id=${encodeURIComponent(teamId)}`, {
    method: "DELETE",
  });
}

/** POST /account/delete — irreversibly deletes the business's data, Team, and the given Appwrite user. */
export async function deleteAccountAndBusiness(businessId: string, teamId: string, userId: string): Promise<void> {
  await workerFetch("/account/delete", {
    method: "POST",
    body: JSON.stringify({ business_id: businessId, team_id: teamId, user_id: userId }),
  });
}

export interface CreateScanParams {
  businessId: string;
  teamId: string;
  createdByUserId: string;
  datasetIds: string[];
  currency?: string;
}

export interface ReportSummaryResponse {
  scan_id: string;
  finding_count: number;
  high_confidence_count: number;
  impact_totals: Array<{ impact_type: string; currency: string; amount: string }>;
  top_findings: Finding[];
  all_findings: Finding[];
  data_limitations: string[];
  is_demo: boolean;
}

/** POST /scans — run detection across already-uploaded datasets. */
export async function createScan(params: CreateScanParams): Promise<ReportSummaryResponse> {
  return workerJson<ReportSummaryResponse>("/scans", {
    method: "POST",
    body: JSON.stringify({
      business_id: params.businessId,
      team_id: params.teamId,
      created_by_user_id: params.createdByUserId,
      dataset_ids: params.datasetIds,
      currency: params.currency ?? "INR",
    }),
  });
}

export interface ReportFile {
  contentType: string;
  filename: string;
  body: ArrayBuffer;
}

/** GET /scans/:id/report?format= — fetch a generated report export as raw bytes. */
export async function getReport(scanId: string, teamId: string, format: ReportFormat): Promise<ReportFile> {
  const res = await workerFetch(
    `/scans/${encodeURIComponent(scanId)}/report?team_id=${encodeURIComponent(teamId)}&format=${encodeURIComponent(format)}`
  );
  const contentType = res.headers.get("content-type") ?? "application/octet-stream";
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename=([^;]+)/);
  const filename = match?.[1]?.trim() ?? `scan-${scanId}-report.${format}`;
  return { contentType, filename, body: await res.arrayBuffer() };
}

// --- Integrations (Shopify today; HubSpot/QuickBooks/Zoho/Salesforce registered as "coming soon") ---

export interface IntegrationProvider {
  key: string;
  label: string;
  available: boolean;
}

/** GET /integrations/providers */
export async function listIntegrationProviders(): Promise<IntegrationProvider[]> {
  const data = await workerJson<{ providers: IntegrationProvider[] }>("/integrations/providers");
  return data.providers;
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

/** GET /integrations/connections — sanitized, never includes credentials. */
export async function listIntegrationConnections(businessId: string, teamId: string): Promise<IntegrationConnection[]> {
  const data = await workerJson<{ connections: IntegrationConnection[] }>(
    `/integrations/connections?business_id=${encodeURIComponent(businessId)}&team_id=${encodeURIComponent(teamId)}`
  );
  return data.connections;
}

export interface ConnectIntegrationParams {
  businessId: string;
  teamId: string;
  userId: string;
  provider: string;
  credentials: Record<string, string>;
}

/** POST /integrations/connections — tests the credentials, then stores them (worker-only, never client-readable). */
export async function connectIntegration(params: ConnectIntegrationParams): Promise<IntegrationConnection> {
  return workerJson<IntegrationConnection>("/integrations/connections", {
    method: "POST",
    body: JSON.stringify({
      business_id: params.businessId, team_id: params.teamId, user_id: params.userId,
      provider: params.provider, credentials: params.credentials,
    }),
  });
}

/** DELETE /integrations/connections/:id */
export async function disconnectIntegration(connectionId: string, teamId: string): Promise<void> {
  await workerFetch(`/integrations/connections/${encodeURIComponent(connectionId)}?team_id=${encodeURIComponent(teamId)}`, {
    method: "DELETE",
  });
}

/** POST /integrations/connections/:id/sync — pulls fresh data through the same pipeline a file upload uses. */
export async function syncIntegration(
  connectionId: string, businessId: string, teamId: string
): Promise<{ dataset_id: string; row_count: number; kind: string; warnings: string[] }> {
  return workerJson(`/integrations/connections/${encodeURIComponent(connectionId)}/sync`, {
    method: "POST",
    body: JSON.stringify({ business_id: businessId, team_id: teamId }),
  });
}
