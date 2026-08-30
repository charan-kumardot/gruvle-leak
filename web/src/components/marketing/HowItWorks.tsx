"use client";

import { motion } from "framer-motion";
import { Reveal, RevealGroup, RevealItem } from "@/components/marketing/Reveal";

const STEPS = [
  {
    step: "01",
    title: "Upload",
    description:
      "Drop in your billing, invoicing, CRM or inventory exports — CSV, Excel or PDF. No integrations required.",
  },
  {
    step: "02",
    title: "Analyze",
    description: "Gruvle profiles your data and runs detectors across unbilled revenue, pricing, renewals and more.",
  },
  {
    step: "03",
    title: "Evidence",
    description: "Every finding comes with the underlying rows and the calculation behind it — verify, don't trust.",
  },
  {
    step: "04",
    title: "Act",
    description: "Confirm or dismiss each finding, and turn confirmed ones into a recovery action or a report.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-ink-100">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">How it works</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Four steps from raw export to a reviewed, evidence-backed finding.
          </p>
        </Reveal>

        <RevealGroup className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4" stagger={0.1}>
          {STEPS.map((s, i) => (
            <RevealItem key={s.step}>
              <div className="group relative flex flex-col gap-3">
                {i < STEPS.length - 1 && (
                  <div className="absolute right-[-1rem] top-3 hidden h-px w-8 bg-ink-100 lg:block" aria-hidden="true" />
                )}
                <motion.span
                  whileHover={{ scale: 1.15 }}
                  transition={{ type: "spring", stiffness: 400, damping: 15 }}
                  className="inline-block w-fit text-sm font-semibold tabular-nums text-accent-500"
                >
                  {s.step}
                </motion.span>
                <h3 className="text-base font-semibold text-ink-900">{s.title}</h3>
                <p className="text-sm leading-relaxed text-ink-500">{s.description}</p>
              </div>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}
