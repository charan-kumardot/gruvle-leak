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
 * Only the three operations that genuinely need the Python worker live here:
 * uploading + parsing a file, running detection, and rendering a report
 * export. Everything else (listing scans, reading findings, confirming /
 * dismissing a finding) reads and writes Appwrite directly from the client
 * via the Web SDK (see src/lib/scans-client.ts) — those documents are
 * already team-permissioned in Appwrite, so proxying them through here
 * would just be reimplementing access control Appwrite already enforces.
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
