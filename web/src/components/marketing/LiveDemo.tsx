"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { Badge, ConfidenceBadge } from "@/components/ui/Badge";
import { Reveal } from "@/components/marketing/Reveal";
import { AnimatedCounter } from "@/components/marketing/AnimatedCounter";

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

interface IndustryOption {
  key: string;
  label: string;
  business_name: string;
  tagline: string;
}

const WORKER_URL = process.env.NEXT_PUBLIC_WORKER_URL ?? "http://localhost:8000";

// Mirrors worker/app/demo/demo_data.py's PROFILES — used only if /demo/industries
// can't be reached, so the picker still renders something sensible.
const FALLBACK_INDUSTRIES: IndustryOption[] = [
  { key: "retail", label: "Retail", business_name: "Demo Retail Co.", tagline: "an online retailer selling home appliances" },
  { key: "saas", label: "SaaS", business_name: "Demo Cloudstack Inc.", tagline: "a B2B SaaS company selling subscription plans" },
  { key: "agency", label: "Agency", business_name: "Demo Northlight Studio", tagline: "a creative agency billing for projects and retainers" },
  { key: "restaurant", label: "Restaurant", business_name: "Demo Copper Kettle Kitchen", tagline: "a restaurant group billing catering and private events" },
  { key: "logistics", label: "Logistics", business_name: "Demo Vantage Freight Co.", tagline: "a logistics provider billing shipments and freight contracts" },
];

const LOADING_STEPS = [
  "Profiling records across your datasets…",
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
  const [industries, setIndustries] = useState<IndustryOption[]>(FALLBACK_INDUSTRIES);
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [step, setStep] = useState(0);
  const [data, setData] = useState<DemoSummary | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetch(`${WORKER_URL}/demo/industries`)
      .then((r) => (r.ok ? r.json() : null))
      .then((json: { industries: IndustryOption[] } | null) => {
        if (json?.industries?.length) setIndustries(json.industries);
      })
      .catch(() => {});
  }, []);

  function stopStepper() {
    if (timerRef.current) clearInterval(timerRef.current);
  }

  async function runDemo(industryKey: string) {
    setSelected(industryKey);
    setStatus("loading");
    setStep(0);
    setExpanded(null);
    timerRef.current = setInterval(() => {
      setStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 550);

    try {
      const res = await fetch(`${WORKER_URL}/demo/scan?industry=${encodeURIComponent(industryKey)}`);
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

  const potentialLeakage = data?.impact_totals[0];
  const selectedOption = industries.find((i) => i.key === selected);

  return (
    <section id="live-demo" className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-5xl px-6 py-20">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">See it work</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Pick a business like yours. Watch Gruvle find real leaks — live.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Runs the actual detection engine against synthetic data for the business type you
            pick. Click any finding to see its evidence, the same way you would with your own data.
          </p>
        </Reveal>

        <div className="mx-auto mt-8 flex max-w-3xl flex-wrap items-center justify-center gap-2">
          {industries.map((ind) => (
            <motion.button
              key={ind.key}
              type="button"
              onClick={() => runDemo(ind.key)}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              disabled={status === "loading"}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                selected === ind.key
                  ? "border-ink-900 bg-ink-950 text-white"
                  : "border-ink-200 bg-white text-ink-600 hover:border-ink-400 hover:text-ink-900"
              }`}
            >
              {ind.label}
            </motion.button>
          ))}
        </div>
        {selectedOption && status !== "idle" && (
          <p className="mt-3 text-center text-xs text-ink-400">
            Showing {selectedOption.tagline}
          </p>
        )}

        <div className="mx-auto mt-8 max-w-3xl">
          <AnimatePresence mode="wait">
            {status === "idle" && (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-ink-200 bg-paper px-6 py-14 text-center"
              >
                <p className="text-sm font-medium text-ink-700">Pick a business type above to run the live demo.</p>
                <p className="text-xs text-ink-400">No signup needed — runs Gruvle&apos;s real detectors on synthetic data.</p>
              </motion.div>
            )}

            {status === "loading" && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-4 rounded-xl border border-ink-100 bg-paper px-6 py-16 text-center"
              >
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-600" />
                <AnimatePresence mode="wait">
                  <motion.p
                    key={step}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.2 }}
                    className="text-sm font-medium text-ink-700"
                  >
                    {LOADING_STEPS[step]}
                  </motion.p>
                </AnimatePresence>
              </motion.div>
            )}

            {status === "error" && (
              <motion.div
                key="error"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-3 rounded-xl border border-accent-200 bg-accent-50 px-6 py-12 text-center"
              >
                <p className="text-sm text-accent-700">Couldn&apos;t reach the live demo service right now.</p>
                <Button variant="secondary" size="sm" onClick={() => selected && runDemo(selected)}>
                  Try again
                </Button>
              </motion.div>
            )}

            {status === "done" && data && (
              <motion.div
                key="done"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col gap-6"
              >
                <div className="flex items-center justify-between rounded-lg bg-ink-950 px-4 py-2.5 text-xs font-medium text-white">
                  <span>DEMO DATA — {data.business_name}</span>
                  <span className="text-ink-300">
                    <AnimatedCounter value={data.records_analyzed} /> records analyzed
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatBlock
                    label="Potential leakage"
                    value={
                      potentialLeakage ? (
                        <AnimatedCounter
                          value={Number(potentialLeakage.amount)}
                          prefix={`${potentialLeakage.currency} `}
                        />
                      ) : (
                        "—"
                      )
                    }
                    risk
                  />
                  <StatBlock label="High confidence" value={<AnimatedCounter value={data.high_confidence_count} />} />
                  <StatBlock label="Findings" value={<AnimatedCounter value={data.finding_count} />} />
                  <StatBlock label="Records analyzed" value={<AnimatedCounter value={data.records_analyzed} />} />
                </div>

                {data.top_findings.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-ink-200 bg-paper px-6 py-10 text-center">
                    <p className="text-sm text-ink-600">
                      No significant leaks in this particular synthetic run — try another business type above.
                    </p>
                  </div>
                ) : (
                  <motion.div
                    className="flex flex-col gap-3"
                    initial="hidden"
                    animate="visible"
                    variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
                  >
                    {data.top_findings.map((f) => {
                      const isOpen = expanded === f.id;
                      return (
                        <motion.div
                          key={f.id}
                          variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                          whileHover={{ y: -2 }}
                          className="rounded-xl border border-ink-100 bg-white shadow-card transition-shadow hover:shadow-lg"
                        >
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
                              <p className="text-xs font-medium text-ink-400">
                                {isOpen ? "Hide evidence ↑" : "View evidence ↓"}
                              </p>
                            </div>
                          </button>

                          <AnimatePresence initial={false}>
                            {isOpen && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.3, ease: "easeInOut" }}
                                className="overflow-hidden border-t border-ink-100"
                              >
                                <div className="px-5 py-5">
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
                                            <tr key={i} className="transition-colors hover:bg-paper">
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
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.div>
                      );
                    })}
                  </motion.div>
                )}

                <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-ink-200 bg-paper px-6 py-8 text-center">
                  <p className="text-sm text-ink-600">
                    This is real detection on synthetic data. Upload your own to find what your
                    business is actually losing.
                  </p>
                  <Link href="/signup">
                    <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
                      <Button size="lg">Find my leaks</Button>
                    </motion.div>
                  </Link>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

function StatBlock({ label, value, risk }: { label: string; value: React.ReactNode; risk?: boolean }) {
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-4 transition-colors hover:border-ink-300">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-400">{label}</p>
      <p className={`mt-1.5 text-lg font-semibold tabular-nums ${risk ? "text-accent-600" : "text-ink-950"}`}>
        {value}
      </p>
    </div>
  );
}
