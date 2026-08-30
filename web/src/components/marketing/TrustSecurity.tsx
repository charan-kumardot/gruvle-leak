"use client";

import { motion } from "framer-motion";
import { Reveal, RevealGroup, RevealItem } from "@/components/marketing/Reveal";

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-ink-700" aria-hidden="true">
      <path d={d} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const POINTS = [
  {
    title: "Your data stays yours",
    description: "Never used to train any model. Files are private by default — no public URL exposes them.",
    icon: <Icon d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z" />,
  },
  {
    title: "Delete anything, anytime",
    description: "Files, datasets, scans, reports, or your whole account — deletion is always available.",
    icon: <Icon d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6" />,
  },
  {
    title: "Strict business isolation",
    description: "Every business is its own isolated tenant. One account can never see another's data.",
    icon: <Icon d="M4 21V9l8-6 8 6v12M9 21v-6h6v6" />,
  },
  {
    title: "Nothing sent without approval",
    description: "Actions are drafted, never sent or changed, until you explicitly approve them.",
    icon: <Icon d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />,
  },
];

export function TrustSecurity() {
  return (
    <section className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">
            Built to be trusted with your numbers
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Private by default. Verifiable by design.
          </h2>
        </Reveal>

        <RevealGroup className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4" stagger={0.07}>
          {POINTS.map((p) => (
            <RevealItem key={p.title}>
              <motion.div whileHover={{ y: -3 }} className="flex flex-col gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-ink-200 bg-paper">
                  {p.icon}
                </div>
                <h3 className="text-sm font-semibold text-ink-900">{p.title}</h3>
                <p className="text-sm leading-relaxed text-ink-500">{p.description}</p>
              </motion.div>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}
