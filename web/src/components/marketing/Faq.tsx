"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Reveal } from "@/components/marketing/Reveal";

const FAQS = [
  {
    q: "Do I need to connect my bank account or payment processor?",
    a: "No. Gruvle works entirely from files you already have — CSV, Excel, JSON or PDF exports of your orders, invoices, contracts or inventory. No bank, ERP or CRM connection is required to get started.",
  },
  {
    q: "How do I know a finding is real and not a false positive?",
    a: "Every finding shows the exact records and the calculation behind it — the same evidence you'd have to pull together by hand. Detection is deterministic code, not an AI model guessing at numbers, and every finding is labeled with a confidence level and an explicit list of what the data doesn't tell us.",
  },
  {
    q: "Can I trust Gruvle with sensitive business data?",
    a: "Your files are private by default, isolated to your business at the database level, and never used to train any model. You can delete a file, dataset, scan, report or your account at any time.",
  },
  {
    q: "Will Gruvle send emails or change prices on its own?",
    a: "No. Gruvle drafts recommended actions — follow-up emails, renewal outreach, pricing reviews — but never sends, invoices, or changes anything without you explicitly approving it.",
  },
  {
    q: "What if my data is messy or incomplete?",
    a: "Gruvle scores data quality before analysis and tells you exactly what's missing and which checks it affects, rather than silently producing incomplete or misleading results.",
  },
  {
    q: "Is this a replacement for my accountant?",
    a: "No. Gruvle identifies potential revenue leakage from the data you provide — findings may require human review and should not be treated as accounting, tax, legal, or financial advice.",
  },
];

export function Faq() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-3xl px-6 py-20">
        <Reveal className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">FAQ</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Questions worth asking before you upload real data.
          </h2>
        </Reveal>

        <Reveal delay={0.1} className="mt-10 flex flex-col divide-y divide-ink-100 rounded-xl border border-ink-100">
          {FAQS.map((item, i) => {
            const isOpen = open === i;
            return (
              <div key={item.q}>
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-paper"
                >
                  <span className="text-sm font-medium text-ink-900">{item.q}</span>
                  <motion.span
                    animate={{ rotate: isOpen ? 45 : 0 }}
                    transition={{ duration: 0.25 }}
                    className="shrink-0 text-lg leading-none text-ink-400"
                  >
                    +
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-5 text-sm leading-relaxed text-ink-500">{item.a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </Reveal>
      </div>
    </section>
  );
}
