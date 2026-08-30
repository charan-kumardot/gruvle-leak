"use client";

import { motion } from "framer-motion";
import { RevealGroup, RevealItem, Reveal } from "@/components/marketing/Reveal";

interface FeatureItem {
  category: string;
  title: string;
  description: string;
  live: boolean;
  icon: React.ReactNode;
}

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-ink-700" aria-hidden="true">
      <path d={d} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const FEATURES: FeatureItem[] = [
  {
    category: "Unbilled",
    title: "Unbilled revenue",
    description: "Completed orders with no matching invoice, matched record by record.",
    live: true,
    icon: <Icon d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />,
  },
  {
    category: "Pricing",
    title: "Pricing inconsistencies",
    description: "Customers priced well below the norm, with no discount on record.",
    live: true,
    icon: <Icon d="M3 3v18h18M7 15l4-4 3 3 5-6" />,
  },
  {
    category: "Invoice",
    title: "Invoice mismatches",
    description: "Undercharges and duplicate invoices, flagged and explained.",
    live: true,
    icon: <Icon d="M8 4h8a2 2 0 012 2v14l-3-2-2 2-2-2-2 2-2-2-3 2V6a2 2 0 012-2z" />,
  },
  {
    category: "Discount",
    title: "Discount leakage",
    description: "Discounts beyond policy, with the exact excess amount.",
    live: true,
    icon: <Icon d="M20 7L9 18l-5-5M4 4l16 16" />,
  },
  {
    category: "Renewal",
    title: "Renewal risk",
    description: "Contracts expiring soon, ranked by recurring value at risk.",
    live: true,
    icon: <Icon d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />,
  },
  {
    category: "Inventory",
    title: "Inventory exposure",
    description: "Dead stock quietly tying up capital.",
    live: false,
    icon: <Icon d="M20 7L12 3 4 7m16 0v10l-8 4m8-14L12 11m0 0L4 7m8 4v10M4 7v10l8 4" />,
  },
  {
    category: "Customer",
    title: "Customer revenue risk",
    description: "High-value accounts going quiet, before it shows up as churn.",
    live: false,
    icon: <Icon d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m5-5.13a4 4 0 100-8 4 4 0 000 8z" />,
  },
  {
    category: "Contract",
    title: "Contract term drift",
    description: "Billed amounts checked against your uploaded contracts.",
    live: false,
    icon: <Icon d="M9 12h6m-6 4h6M9 8h1m4-5H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V7l-5-5z" />,
  },
];

export function Features() {
  return (
    <section className="border-t border-ink-100">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">What Gruvle checks</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Ten ways revenue quietly gets away from you.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Five checks run today, fully deterministic and evidence-backed. The rest are on the roadmap.
          </p>
        </Reveal>

        <RevealGroup className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" stagger={0.06}>
          {FEATURES.map((f) => (
            <RevealItem key={f.category}>
              <motion.div
                whileHover={{ y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="group flex h-full flex-col gap-3 rounded-xl border border-ink-100 bg-white p-5 shadow-card transition-colors hover:border-ink-300"
              >
                <div className="flex items-center justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ink-50 transition-colors group-hover:bg-accent-50">
                    {f.icon}
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      f.live ? "bg-emerald-50 text-risk-low" : "bg-ink-100 text-ink-400"
                    }`}
                  >
                    {f.live ? "Live" : "Roadmap"}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-ink-950">{f.title}</h3>
                <p className="text-sm leading-relaxed text-ink-500">{f.description}</p>
              </motion.div>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}
