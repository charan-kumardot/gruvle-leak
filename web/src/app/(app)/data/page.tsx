"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { FileDropzone, type UploadFile } from "@/components/upload/FileDropzone";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { useAuth } from "@/lib/auth-context";
import {
  uploadDataset,
  startScan,
  listDatasets,
  deleteDataset,
  ApiClientError,
  type DatasetSummary,
} from "@/lib/api-client";

type Stage = "idle" | "uploading" | "scanning";

const SOURCE_LABELS: Record<string, string> = {
  upload: "Uploaded",
  shopify: "Shopify",
  hubspot: "HubSpot",
  quickbooks: "QuickBooks",
  zoho: "Zoho",
  salesforce: "Salesforce",
};

export default function DataPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const syncedDatasetId = searchParams.get("syncedDataset");
  const { user } = useAuth();
  const { business } = useCurrentBusiness();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [stage, setStage] = useState<Stage>("idle");
  const [progressLabel, setProgressLabel] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const readyFiles = files.filter((f) => f.status === "ready");
  const canSubmit = (readyFiles.length > 0 || selectedIds.size > 0) && !!business && !!user && stage === "idle";

  async function refreshDatasets() {
    if (!business) return;
    const list = await listDatasets(business.id, business.team_id);
    setDatasets(list);
  }

  useEffect(() => {
    if (business) refreshDatasets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [business]);

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleStartScan() {
    if (!business || !user) return;
    setError(null);

    try {
      setStage("uploading");
      const datasetIds: string[] = [...selectedIds];
      let i = 0;
      for (const uploadFile of readyFiles) {
        i += 1;
        setProgressLabel(`Analyzing ${uploadFile.file.name} (${i} of ${readyFiles.length})…`);
        const result = await uploadDataset(business.id, business.team_id, uploadFile.file);
        datasetIds.push(result.dataset_id);
      }

      setStage("scanning");
      setProgressLabel("Checking for unbilled work, pricing gaps, invoice mismatches and renewal risk…");
      const scan = await startScan(business.id, business.team_id, user.$id, datasetIds, business.currency);

      router.push(`/leaks?scanId=${encodeURIComponent(scan.scan_id)}`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Something went wrong starting the scan.");
      setStage("idle");
    }
  }

  async function handleScanSyncedDataset() {
    if (!business || !user || !syncedDatasetId) return;
    setError(null);
    setStage("scanning");
    setProgressLabel("Checking for unbilled work, pricing gaps, invoice mismatches and renewal risk…");
    try {
      const scan = await startScan(business.id, business.team_id, user.$id, [syncedDatasetId], business.currency);
      router.push(`/leaks?scanId=${encodeURIComponent(scan.scan_id)}`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Something went wrong starting the scan.");
      setStage("idle");
    }
  }

  async function handleDeleteDataset(id: string) {
    if (!business) return;
    if (!confirm("Delete this dataset? Past scans that used it keep their results, but you'll need to re-upload to scan it again.")) return;
    setDeletingId(id);
    try {
      await deleteDataset(id, business.team_id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await refreshDatasets();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Could not delete this dataset.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Data</h1>
        <p className="mt-1 text-sm text-ink-500">
          Upload the exports you already have, or{" "}
          <Link href="/integrations" className="font-medium text-ink-700 underline">
            connect a live data source
          </Link>{" "}
          — Gruvle will look for revenue leakage across them either way. No bank connection required.
        </p>
      </div>

      {syncedDatasetId && (
        <Card>
          <CardBody className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-ink-950">Fresh data synced from your connection</p>
              <p className="mt-0.5 text-xs text-ink-400">Ready to scan whenever you are.</p>
            </div>
            <Button onClick={handleScanSyncedDataset} disabled={stage !== "idle"}>
              {stage === "scanning" ? "Scanning…" : "Scan this data now"}
            </Button>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-ink-900">Upload files</h2>
        </CardHeader>
        <CardBody className="flex flex-col gap-5">
          <FileDropzone files={files} onFilesChange={setFiles} disabled={stage !== "idle"} />

          {stage !== "idle" && (
            <div className="flex items-center gap-2 text-sm text-ink-500">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
              {progressLabel}
            </div>
          )}

          {error && <p className="text-sm text-accent-600">{error}</p>}

          {!business && (
            <p className="text-sm text-ink-400">
              Finish{" "}
              <a href="/onboarding" className="font-medium text-ink-700 underline">
                onboarding
              </a>{" "}
              before starting a scan.
            </p>
          )}

          <div>
            <Button onClick={handleStartScan} disabled={!canSubmit} size="lg">
              {stage === "idle"
                ? selectedIds.size > 0
                  ? `Start a scan (${readyFiles.length + selectedIds.size} dataset${readyFiles.length + selectedIds.size === 1 ? "" : "s"})`
                  : "Start a scan"
                : "Working…"}
            </Button>
          </div>
        </CardBody>
      </Card>

      {datasets && datasets.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-ink-900">Your datasets</h2>
          <p className="mt-1 text-xs text-ink-400">Select any to include in your next scan alongside new uploads.</p>
          <div className="mt-3 flex flex-col divide-y divide-ink-100 rounded-xl border border-ink-100 bg-white">
            {datasets.map((d) => (
              <label
                key={d.id}
                className="flex cursor-pointer items-center justify-between gap-4 px-4 py-3 hover:bg-paper"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(d.id)}
                    onChange={() => toggleSelected(d.id)}
                    disabled={stage !== "idle"}
                    className="h-4 w-4 rounded border-ink-300"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-900">{d.original_filename}</p>
                    <p className="mt-0.5 text-xs text-ink-400">
                      {d.kind} · {d.row_count.toLocaleString()} rows · {new Date(d.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Badge tone="neutral">{SOURCE_LABELS[d.source] ?? d.source}</Badge>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      handleDeleteDataset(d.id);
                    }}
                    disabled={deletingId === d.id}
                    className="text-xs font-medium text-ink-400 hover:text-accent-600"
                  >
                    {deletingId === d.id ? "Deleting…" : "Delete"}
                  </button>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
