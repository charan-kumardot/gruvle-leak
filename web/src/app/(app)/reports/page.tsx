"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { listScans } from "@/lib/scans-client";
import { downloadReport, ApiClientError } from "@/lib/api-client";
import type { ReportFormat, Scan } from "@/lib/types";

const FORMATS: { value: ReportFormat; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "csv", label: "CSV" },
  { value: "markdown", label: "Markdown" },
  { value: "json", label: "JSON" },
];

export default function ReportsPage() {
  const { business, loading: businessLoading } = useCurrentBusiness();
  const [scans, setScans] = useState<Scan[] | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!business) return;
    listScans(business.team_id).then(setScans);
  }, [business]);

  async function handleDownload(scanId: string, format: ReportFormat) {
    if (!business) return;
    setDownloading(`${scanId}-${format}`);
    setError(null);
    try {
      await downloadReport(scanId, business.team_id, format);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Could not download this report.");
    } finally {
      setDownloading(null);
    }
  }

  if (businessLoading || (business && scans === null)) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
        Loading…
      </div>
    );
  }

  if (!scans || scans.length === 0) {
    return (
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Reports</h1>
          <p className="mt-1 text-sm text-ink-500">
            Export a summary of a scan&apos;s findings to share with your team or accountant.
          </p>
        </div>
        <EmptyState
          eyebrow="No reports yet"
          title="Reports appear after your first scan."
          description="Once a scan finishes, you'll be able to export its findings as a PDF, CSV, Markdown or JSON report."
          action={
            <Link href="/data">
              <Button size="lg">Start a scan</Button>
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Reports</h1>
        <p className="mt-1 text-sm text-ink-500">
          Export a summary of a scan&apos;s findings to share with your team or accountant.
        </p>
      </div>

      {error && <p className="text-sm text-accent-600">{error}</p>}

      <div className="flex flex-col gap-3">
        {scans.map((scan) => (
          <Card key={scan.id}>
            <CardBody className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-ink-950">
                  Scan from {new Date(scan.created_at).toLocaleDateString()}
                </p>
                <p className="mt-0.5 text-xs text-ink-400">
                  {scan.finding_count} finding(s) &middot; {scan.records_analyzed.toLocaleString()} records analyzed
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {FORMATS.map((f) => (
                  <Button
                    key={f.value}
                    variant="secondary"
                    size="sm"
                    disabled={downloading === `${scan.id}-${f.value}`}
                    onClick={() => handleDownload(scan.id, f.value)}
                  >
                    {downloading === `${scan.id}-${f.value}` ? "Preparing…" : f.label}
                  </Button>
                ))}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
