"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { HeroFindingCard } from "@/components/marketing/HeroFindingCard";
import { AnimatedLogo } from "@/components/ui/AnimatedLogo";

const EASE = [0.21, 0.47, 0.32, 0.98] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.09, ease: EASE },
  }),
};

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0 text-ink-400" aria-hidden="true">
      <path
        d="M4 10.5l3.5 3.5L16 5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Ambient background — two slow-drifting soft blobs, restrained opacity */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <motion.div
          animate={{ x: [0, 30, -10, 0], y: [0, -20, 10, 0] }}
          transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-accent-100/50 blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -25, 15, 0], y: [0, 15, -15, 0] }}
          transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -right-24 top-10 h-96 w-96 rounded-full bg-ink-100/60 blur-3xl"
        />
        <div
          className="absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage:
              "linear-gradient(to right, #e6e7ea 1px, transparent 1px), linear-gradient(to bottom, #e6e7ea 1px, transparent 1px)",
            backgroundSize: "56px 56px",
            maskImage: "radial-gradient(ellipse 70% 60% at 50% 0%, black 40%, transparent 100%)",
          }}
        />
      </div>

      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 pb-20 pt-20 sm:pt-28 lg:grid-cols-[1.1fr_0.9fr] lg:gap-8">
        <div className="text-center lg:text-left">
          <div className="mb-2 flex justify-center lg:justify-start">
            <AnimatedLogo size={52} />
          </div>

          <motion.p
            custom={0}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="mb-5 inline-flex items-center rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-500"
          >
            AI revenue-leakage investigator, not another dashboard
          </motion.p>

          <motion.h1
            custom={1}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="text-balance text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl lg:text-6xl"
          >
            Find the money your business is losing.
          </motion.h1>

          <motion.p
            custom={2}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="mx-auto mt-6 max-w-xl text-balance text-base leading-relaxed text-ink-500 sm:text-lg lg:mx-0"
          >
            Upload the data you already have. Gruvle finds unbilled revenue, pricing gaps,
            invoice mismatches and renewal risk — and shows its work for every number.
          </motion.p>

          <motion.div
            custom={3}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start"
          >
            <Link href="/signup" className="w-full sm:w-auto">
              <Button size="lg" className="w-full transition-transform hover:scale-[1.03] active:scale-[0.98] sm:w-auto">
                Find my leaks
              </Button>
            </Link>
            <a href="#live-demo" className="w-full sm:w-auto">
              <Button
                variant="secondary"
                size="lg"
                className="w-full transition-transform hover:scale-[1.03] active:scale-[0.98] sm:w-auto"
              >
                Try the live demo
              </Button>
            </a>
          </motion.div>

          <motion.div
            custom={4}
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="mx-auto mt-8 flex max-w-xl flex-col items-center gap-2 text-sm text-ink-400 sm:flex-row sm:justify-center sm:gap-6 lg:mx-0 lg:justify-start"
          >
            {["No bank connection required.", "Start with CSV, Excel or PDF.", "Free to start."].map((t) => (
              <span
                key={t}
                className="inline-flex cursor-default items-center gap-1.5 rounded-full px-1.5 py-0.5 transition-colors hover:bg-ink-50 hover:text-ink-700"
              >
                <CheckIcon /> {t}
              </span>
            ))}
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.35, ease: [0.21, 0.47, 0.32, 0.98] }}
        >
          <HeroFindingCard />
        </motion.div>
      </div>
    </section>
  );
}
