"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge, ConfidenceBadge } from "@/components/ui/Badge";

interface DemoFinding {
  id: string;
  title: string;
  summary: string;
  category: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  why_it_matters: string;
  what_we_dont_know: string[];
  recommended_action: string;
  financial_impact: {
    impact_type: string;
    amount: string;
    currency: string;
    is_recurring: boolean;
    recurrence_period?: string | null;
  };
  evidence: Array<{ dataset_id: string; row_index: number; display_fields: Record<string, unknown> }>;
  calculation: { method: string; formula: string; result: string };
}

interface DemoSummary {
  business_name: string;
  records_analyzed: number;
  finding_count: number;
  high_confidence_count: number;
  impact_totals: Array<{ impact_type: string; currency: string; amount: string }>;
  top_findings: DemoFinding[];
  is_demo: boolean;
}

const WORKER_URL = process.env.NEXT_PUBLIC_WORKER_URL ?? "http://localhost:8000";

const LOADING_STEPS = [
  "Profiling 258 records across 3 datasets…",
  "Checking for unbilled work…",
  "Checking pricing inconsistencies…",
  "Checking invoice mismatches…",
  "Checking renewal risk…",
  "Prioritizing findings…",
];

const CATEGORY_LABELS: Record<string, string> = {
  UNBILLED: "Unbilled",
  PRICING: "Pricing",
  INVOICE: "Invoice",
  RENEWAL: "Renewal",
  DISCOUNT: "Discount",
};

function money(currency: string, amount: string, recurring: boolean, period?: string | null) {
  const n = Number(amount);
  const formatted = `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n)}`;
  return recurring ? `${formatted}/${period === "monthly" ? "mo" : "yr"}` : formatted;
}

export function LiveDemo() {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [step, setStep] = useState(0);
  const [data, setData] = useState<DemoSummary | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function stopStepper() {
    if (timerRef.current) clearInterval(timerRef.current);
  }

  async function runDemo() {
    setStatus("loading");
    setStep(0);
    timerRef.current = setInterval(() => {
      setStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 550);

    try {
      const res = await fetch(`${WORKER_URL}/demo/scan`);
      if (!res.ok) throw new Error(`Demo request failed (${res.status})`);
      const json = (await res.json()) as DemoSummary;
      // let the step animation catch up so it doesn't jump-cut on a fast response
      await new Promise((r) => setTimeout(r, LOADING_STEPS.length * 550 - 550));
      stopStepper();
      setData(json);
      setStatus("done");
    } catch {
      stopStepper();
      setStatus("error");
    }
  }

  useEffect(() => () => stopStepper(), []);

  return (
    <section id="live-demo" className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-5xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">See it work</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Watch Gruvle find real leaks — live, right now.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            This runs the actual detection engine against a synthetic retail business — not a
            mockup, not pre-recorded. Click through the evidence for any finding, the same way
            you would with your own data.
          </p>
        </div>

        <div className="mx-auto mt-10 max-w-3xl">
          {status === "idle" && (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-ink-200 bg-paper px-6 py-16 text-center">
              <Button size="lg" onClick={runDemo}>
                Run the live demo
              </Button>
              <p className="text-xs text-ink-400">Runs Gruvle&apos;s real detectors on synthetic demo data — no signup needed.</p>
            </div>
          )}

          {status === "loading" && (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-ink-100 bg-paper px-6 py-16 text-center">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-600" />
              <p className="text-sm font-medium text-ink-700">{LOADING_STEPS[step]}</p>
            </div>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-accent-200 bg-accent-50 px-6 py-12 text-center">
              <p className="text-sm text-accent-700">
                Couldn&apos;t reach the live demo service right now.
              </p>
              <Button variant="secondary" size="sm" onClick={runDemo}>
                Try again
              </Button>
            </div>
          )}

          {status === "done" && data && (
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between rounded-lg bg-ink-950 px-4 py-2.5 text-xs font-medium text-white">
                <span>DEMO DATA — {data.business_name}</span>
                <span className="text-ink-300">{data.records_analyzed.toLocaleString()} records analyzed</span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {data.impact_totals.slice(0, 1).map((t) => (
                  <StatBlock key="pl" label="Potential leakage" value={money(t.currency, t.amount, false)} risk />
                ))}
                {data.impact_totals.length === 0 && <StatBlock label="Potential leakage" value="—" risk />}
                <StatBlock label="High confidence" value={String(data.high_confidence_count)} />
                <StatBlock label="Findings" value={String(data.finding_count)} />
                <StatBlock label="Records analyzed" value={data.records_analyzed.toLocaleString()} />
              </div>

              <div className="flex flex-col gap-3">
                {data.top_findings.map((f) => {
                  const isOpen = expanded === f.id;
                  return (
                    <div key={f.id} className="rounded-xl border border-ink-100 bg-white shadow-card">
                      <button
                        type="button"
                        onClick={() => setExpanded(isOpen ? null : f.id)}
                        className="flex w-full flex-col gap-3 p-5 text-left sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <Badge tone="neutral">{CATEGORY_LABELS[f.category] ?? f.category}</Badge>
                            <ConfidenceBadge confidence={f.confidence} />
                          </div>
                          <h3 className="mt-2 text-sm font-semibold text-ink-950">{f.title}</h3>
                          <p className="mt-1 text-sm text-ink-500">{f.summary}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-lg font-semibold tabular-nums text-ink-950">
                            {money(
                              f.financial_impact.currency,
                              f.financial_impact.amount,
                              f.financial_impact.is_recurring,
                              f.financial_impact.recurrence_period
                            )}
                          </p>
                          <p className="text-xs font-medium text-ink-400">{isOpen ? "Hide evidence ↑" : "View evidence ↓"}</p>
                        </div>
                      </button>

                      {isOpen && (
                        <div className="border-t border-ink-100 px-5 py-5">
                          <p className="text-sm leading-relaxed text-ink-700">{f.why_it_matters}</p>

                          {f.evidence.length > 0 && (
                            <div className="mt-4 overflow-x-auto rounded-lg border border-ink-100">
                              <table className="w-full text-left text-sm">
                                <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-400">
                                  <tr>
                                    {Object.keys(f.evidence[0]?.display_fields ?? {}).map((key) => (
                                      <th key={key} className="px-3 py-2 font-medium">
                                        {key.replace(/_/g, " ")}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-ink-100">
                                  {f.evidence.slice(0, 5).map((e, i) => (
                                    <tr key={i}>
                                      {Object.values(e.display_fields).map((val, j) => (
                                        <td key={j} className="px-3 py-2 text-ink-700">
                                          {val === null || val === undefined ? "—" : String(val)}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}

                          <p className="mt-4 rounded-lg bg-ink-50 px-4 py-3 font-mono text-xs text-ink-700">
                            {f.calculation.formula}
                          </p>

                          {f.what_we_dont_know.length > 0 && (
                            <p className="mt-4 text-xs text-ink-400">
                              What we don&apos;t know: {f.what_we_dont_know.join(" ")}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-ink-200 bg-paper px-6 py-8 text-center">
                <p className="text-sm text-ink-600">
                  This is real detection on synthetic data. Upload your own to find what your
                  business is actually losing.
                </p>
                <Link href="/signup">
                  <Button size="lg">Find my leaks</Button>
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function StatBlock({ label, value, risk }: { label: string; value: string; risk?: boolean }) {
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-4">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-400">{label}</p>
      <p className={`mt-1.5 text-lg font-semibold tabular-nums ${risk ? "text-accent-600" : "text-ink-950"}`}>
        {value}
      </p>
    </div>
  );
}
