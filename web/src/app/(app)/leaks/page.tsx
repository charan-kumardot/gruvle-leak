"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Badge, ConfidenceBadge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { listFindings, listScans } from "@/lib/scans-client";
import type { Finding, LeakCategory } from "@/lib/types";

const CATEGORY_LABELS: Record<LeakCategory, string> = {
  UNBILLED: "Unbilled",
  PRICING: "Pricing",
  INVOICE: "Invoice",
  RENEWAL: "Renewal",
  INVENTORY: "Inventory",
  DISCOUNT: "Discount",
  REFUND: "Refund",
  CUSTOMER: "Customer",
  CONTRACT: "Contract",
  OPERATIONS: "Operations",
};

function formatAmount(finding: Finding): string {
  const amount = Number(finding.financial_impact.amount);
  const formatted = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(amount);
  const suffix = finding.financial_impact.is_recurring
    ? `/${finding.financial_impact.recurrence_period === "monthly" ? "mo" : "yr"}`
    : "";
  return `${finding.financial_impact.currency} ${formatted}${suffix}`;
}

export default function LeaksPage() {
  const searchParams = useSearchParams();
  const { business, loading: businessLoading } = useCurrentBusiness();
  const [scanId, setScanId] = useState<string | null>(searchParams.get("scanId"));
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"ALL" | LeakCategory>("ALL");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!business) return;
      setLoading(true);
      try {
        let targetScanId = searchParams.get("scanId");
        if (!targetScanId) {
          const scans = await listScans(business.team_id, 1);
          targetScanId = scans[0]?.id ?? null;
        }
        if (cancelled) return;
        setScanId(targetScanId);
        if (targetScanId) {
          const results = await listFindings(targetScanId);
          if (!cancelled) setFindings(results);
        } else {
          setFindings([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (business) load();
    else if (!businessLoading) setLoading(false);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [business, businessLoading]);

  const filtered = useMemo(() => {
    if (!findings) return [];
    if (filter === "ALL") return findings;
    return findings.filter((f) => f.category === filter);
  }, [findings, filter]);

  const categoriesPresent = useMemo(
    () => Array.from(new Set((findings ?? []).map((f) => f.category))),
    [findings]
  );

  if (loading || businessLoading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
        Loading…
      </div>
    );
  }

  if (!scanId || !findings || findings.length === 0) {
    return (
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Leaks</h1>
          <p className="mt-1 text-sm text-ink-500">
            Every suspected revenue leak Gruvle has found, with evidence and a confidence level.
          </p>
        </div>
        <EmptyState
          eyebrow={scanId ? "No leaks found" : "No findings yet"}
          title={scanId ? "Good news — nothing significant here." : "Nothing to review yet."}
          description={
            scanId
              ? "Gruvle didn't find significant revenue leakage in this scan's data and detectors."
              : "Run a scan on your business data and any suspected leaks — unbilled revenue, pricing gaps, missed renewals and more — will show up here for you to confirm or dismiss."
          }
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
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Leaks</h1>
          <p className="mt-1 text-sm text-ink-500">{findings.length} finding(s) from this scan.</p>
        </div>
        <Link href="/data">
          <Button variant="secondary">New scan</Button>
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        <FilterPill active={filter === "ALL"} onClick={() => setFilter("ALL")}>
          All
        </FilterPill>
        {categoriesPresent.map((c) => (
          <FilterPill key={c} active={filter === c} onClick={() => setFilter(c)}>
            {CATEGORY_LABELS[c]}
          </FilterPill>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {filtered.map((finding) => (
          <Link key={finding.id} href={`/leaks/${finding.id}`}>
            <Card className="p-5 transition-colors hover:border-ink-300">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{CATEGORY_LABELS[finding.category]}</Badge>
                    <ConfidenceBadge confidence={finding.confidence} />
                  </div>
                  <h3 className="mt-2 truncate text-sm font-semibold text-ink-950">{finding.title}</h3>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{finding.summary}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-lg font-semibold tabular-nums text-ink-950">{formatAmount(finding)}</p>
                  <p className="text-xs text-ink-400">{finding.evidence.length} evidence record(s)</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
        active ? "border-ink-900 bg-ink-900 text-white" : "border-ink-200 text-ink-600 hover:border-ink-300"
      }`}
    >
      {children}
    </button>
  );
}
