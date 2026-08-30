"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileDropzone, type UploadFile } from "@/components/upload/FileDropzone";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { useAuth } from "@/lib/auth-context";
import { uploadDataset, startScan, ApiClientError } from "@/lib/api-client";

type Stage = "idle" | "uploading" | "scanning";

export default function DataPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { business } = useCurrentBusiness();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [stage, setStage] = useState<Stage>("idle");
  const [progressLabel, setProgressLabel] = useState("");
  const [error, setError] = useState<string | null>(null);

  const readyFiles = files.filter((f) => f.status === "ready");
  const canSubmit = readyFiles.length > 0 && !!business && !!user && stage === "idle";

  async function handleStartScan() {
    if (!business || !user) return;
    setError(null);

    try {
      setStage("uploading");
      const datasetIds: string[] = [];
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

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Data</h1>
        <p className="mt-1 text-sm text-ink-500">
          Upload the exports you already have — billing, invoicing, CRM, inventory — and Gruvle
          will look for revenue leakage across them. No bank connection required.
        </p>
      </div>

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
              {stage === "idle" ? "Start a scan" : "Working…"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
