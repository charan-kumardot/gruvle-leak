"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, ConfidenceBadge, StatusBadge } from "@/components/ui/Badge";
import { getFindingWithDetail, updateFindingStatus } from "@/lib/scans-client";
import type { Finding } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  UNBILLED: "Unbilled revenue",
  PRICING: "Pricing inconsistency",
  INVOICE: "Invoice mismatch",
  RENEWAL: "Renewal risk",
  INVENTORY: "Inventory",
  DISCOUNT: "Discount",
  REFUND: "Refund",
  CUSTOMER: "Customer",
  CONTRACT: "Contract",
  OPERATIONS: "Operations",
};

const IMPACT_LABELS: Record<string, string> = {
  POTENTIAL_LEAKAGE: "Potential leakage",
  AT_RISK_REVENUE: "At-risk revenue",
  REVENUE_OPPORTUNITY: "Revenue opportunity",
  CAPITAL_TIED_UP: "Capital tied up",
};

function formatAmount(finding: Finding): string {
  const amount = Number(finding.financial_impact.amount);
  const formatted = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(amount);
  const suffix = finding.financial_impact.is_recurring
    ? `/${finding.financial_impact.recurrence_period === "monthly" ? "mo" : "yr"}`
    : "";
  return `${finding.financial_impact.currency} ${formatted}${suffix}`;
}

export default function LeakDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getFindingWithDetail(id)
      .then((f) => !cancelled && setFinding(f))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Could not load this finding."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleStatus(status: "CONFIRMED" | "DISMISSED" | "RESOLVED") {
    if (!finding) return;
    setUpdating(true);
    try {
      const updated = await updateFindingStatus(finding.id, status);
      setFinding(updated);
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
        Loading…
      </div>
    );
  }

  if (error || !finding) {
    return <p className="py-16 text-center text-sm text-accent-600">{error ?? "Finding not found."}</p>;
  }

  return (
    <div className="flex flex-col gap-8">
      <Link href="/leaks" className="text-sm font-medium text-ink-500 hover:text-ink-800">
        &larr; Back to leaks
      </Link>

      <div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{CATEGORY_LABELS[finding.category] ?? finding.category}</Badge>
          <ConfidenceBadge confidence={finding.confidence} />
          <StatusBadge status={finding.status} />
        </div>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950">{finding.title}</h1>
        <p className="mt-3 text-3xl font-semibold tabular-nums text-ink-950">{formatAmount(finding)}</p>
        <p className="mt-1 text-sm text-ink-500">{IMPACT_LABELS[finding.financial_impact.impact_type] ?? finding.financial_impact.impact_type}</p>
      </div>

      <Section title="Why this matters">
        <p className="text-sm leading-relaxed text-ink-700">{finding.why_it_matters}</p>
      </Section>

      <Section title="Evidence">
        {finding.evidence.length === 0 ? (
          <p className="text-sm text-ink-400">No individual records to display for this finding.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-ink-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-400">
                <tr>
                  {Object.keys(finding.evidence[0]?.display_fields ?? {}).map((key) => (
                    <th key={key} className="px-4 py-2 font-medium">
                      {key.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {finding.evidence.map((e) => (
                  <tr key={e.id}>
                    {Object.values(e.display_fields).map((val, i) => (
                      <td key={i} className="px-4 py-2 text-ink-700">
                        {val === null || val === undefined ? "—" : String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {finding.calculation && (
        <Section title="Calculation">
          <p className="text-sm text-ink-700">{finding.calculation.method}</p>
          <p className="mt-2 rounded-lg bg-ink-50 px-4 py-3 font-mono text-xs text-ink-700">
            {finding.calculation.formula}
          </p>
        </Section>
      )}

      {finding.what_we_dont_know && finding.what_we_dont_know.length > 0 && (
        <Section title="What we don't know">
          <ul className="flex flex-col gap-1.5 text-sm text-ink-500">
            {finding.what_we_dont_know.map((item, i) => (
              <li key={i}>&bull; {item}</li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Recommended action">
        <p className="text-sm leading-relaxed text-ink-700">{finding.recommended_action}</p>
      </Section>

      <Card className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-ink-500">Confirm this finding, or dismiss it if it&apos;s not relevant.</p>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={updating} onClick={() => handleStatus("DISMISSED")}>
            Dismiss
          </Button>
          <Button variant="secondary" disabled={updating} onClick={() => handleStatus("RESOLVED")}>
            Mark resolved
          </Button>
          <Button disabled={updating} onClick={() => handleStatus("CONFIRMED")}>
            Confirm
          </Button>
        </div>
      </Card>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardBody className="pt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-400">{title}</h2>
        <div className="mt-3">{children}</div>
      </CardBody>
    </Card>
  );
}
