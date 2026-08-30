"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatTile } from "@/components/ui/StatTile";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { ConfidenceBadge } from "@/components/ui/Badge";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { listFindings, listScans } from "@/lib/scans-client";
import type { Finding, Scan } from "@/lib/types";

function money(currency: string, amount: number): string {
  return `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(amount)}`;
}

export default function OverviewPage() {
  const { business, loading: businessLoading } = useCurrentBusiness();
  const [scan, setScan] = useState<Scan | null | undefined>(undefined);
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!business) return;
      const scans = await listScans(business.team_id, 1);
      const latest = scans[0] ?? null;
      if (cancelled) return;
      setScan(latest);
      if (latest) {
        const f = await listFindings(latest.id);
        if (!cancelled) setFindings(f);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [business]);

  if (businessLoading || scan === undefined) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
        Loading…
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="flex flex-col gap-8">
        <Header />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatTile label="Potential leakage" value="—" hint="No scan yet" tone="risk" />
          <StatTile label="High-confidence leaks" value="—" hint="No scan yet" />
          <StatTile label="At-risk revenue" value="—" hint="No scan yet" />
          <StatTile label="Open issues" value="—" hint="No scan yet" />
          <StatTile label="Records analyzed" value="—" hint="No scan yet" />
        </div>
        <EmptyState
          eyebrow="Get started"
          title="Let's find your first leak."
          description="Upload your business data and Gruvle will look for revenue leakage and missed opportunities."
          action={
            <Link href="/data">
              <Button size="lg">Start a scan</Button>
            </Link>
          }
          secondary="No bank connection required."
        />
      </div>
    );
  }

  const atRiskRevenue = findings
    .filter((f) => f.financial_impact.impact_type === "AT_RISK_REVENUE")
    .reduce((sum, f) => sum + Number(f.financial_impact.amount), 0);
  const openIssues = findings.filter((f) => f.status === "NEW" || f.status === "REVIEWING").length;
  const topFindings = [...findings].sort((a, b) => b.priority_score - a.priority_score).slice(0, 5);

  return (
    <div className="flex flex-col gap-8">
      <Header />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatTile
          label="Potential leakage"
          value={money(scan.currency, scan.total_potential_leakage)}
          tone="risk"
        />
        <StatTile
          label="High-confidence leaks"
          value={money(scan.currency, scan.total_high_confidence_leakage)}
        />
        <StatTile label="At-risk revenue" value={money(scan.currency, atRiskRevenue)} />
        <StatTile label="Open issues" value={String(openIssues)} />
        <StatTile label="Records analyzed" value={scan.records_analyzed.toLocaleString()} />
      </div>

      {topFindings.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-ink-900">Fix these first</h2>
          <div className="mt-3 flex flex-col gap-3">
            {topFindings.map((f, i) => (
              <Link key={f.id} href={`/leaks/${f.id}`}>
                <Card className="p-4 transition-colors hover:border-ink-300">
                  <div className="flex items-center gap-4">
                    <span className="text-lg font-semibold tabular-nums text-ink-300">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-ink-950">{f.title}</p>
                      <p className="text-xs text-ink-400">{money(f.financial_impact.currency, Number(f.financial_impact.amount))}</p>
                    </div>
                    <ConfidenceBadge confidence={f.confidence} />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

      <Card>
        <CardBody className="flex items-center justify-between pt-6">
          <p className="text-sm text-ink-500">Want a full breakdown of every finding?</p>
          <Link href="/leaks">
            <Button variant="secondary">View all leaks</Button>
          </Link>
        </CardBody>
      </Card>
    </div>
  );
}

function Header() {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Your business at a glance</h1>
      <p className="mt-1 text-sm text-ink-500">A running summary of potential leakage across every scan.</p>
    </div>
  );
}
