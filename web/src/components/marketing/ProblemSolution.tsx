"use client";

import { motion } from "framer-motion";
import { Reveal } from "@/components/marketing/Reveal";

const SYMPTOMS = [
  "A completed job that never got invoiced.",
  "A long-time customer quietly paying last year's price.",
  "A contract that renewed itself as a habit, not a decision.",
  "A discount meant to be one-time, three orders ago.",
];

export function ProblemSolution() {
  return (
    <section className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-5xl px-6 py-20">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">The problem</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              Revenue doesn&apos;t disappear all at once. It leaks.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              One unbilled order. One stale discount. One renewal nobody followed up on. None of
              it shows up as a single line — it just quietly lowers every number on your P&amp;L.
            </p>
            <ul className="mt-6 flex flex-col gap-1">
              {SYMPTOMS.map((s, i) => (
                <motion.li
                  key={s}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.08 }}
                  className="flex cursor-default items-start gap-2.5 rounded-lg px-2 py-2 text-sm text-ink-600 transition-colors hover:bg-paper hover:text-ink-900"
                >
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-300" />
                  {s}
                </motion.li>
              ))}
            </ul>
          </Reveal>

          <Reveal delay={0.1}>
            <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">The approach</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              You already have the data. Gruvle reads it like an investigator.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              Upload the exports you already run. Deterministic detectors do the arithmetic —
              never an AI model guessing at numbers — and every finding comes with the exact
              records behind it, verifiable in thirty seconds.
            </p>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              Nothing is stated as certain unless the data proves it: &quot;potential
              leakage,&quot; &quot;at-risk revenue&quot; — hedged language for hedged confidence,
              paired with what we don&apos;t know.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
