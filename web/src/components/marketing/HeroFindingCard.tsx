"use client";

import { useEffect, useState, type MouseEvent } from "react";
import { AnimatePresence, motion, useSpring } from "framer-motion";

interface Example {
  category: string;
  title: string;
  amount: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  detail: string;
}

const EXAMPLES: Example[] = [
  {
    category: "Unbilled",
    title: "Potential unbilled revenue",
    amount: "₹84,000",
    confidence: "HIGH",
    detail: "27 completed orders · 0 matching invoices",
  },
  {
    category: "Renewal",
    title: "Contracts expiring soon",
    amount: "₹9.6L/yr",
    confidence: "MEDIUM",
    detail: "8 contracts · within 30 days",
  },
  {
    category: "Pricing",
    title: "Pricing inconsistency",
    amount: "₹52,000",
    confidence: "MEDIUM",
    detail: "SKU-BLENDER · 15% below median, no discount on file",
  },
  {
    category: "Invoice",
    title: "Invoice below matching order",
    amount: "₹2,000",
    confidence: "HIGH",
    detail: "1 order/invoice pair · direct arithmetic",
  },
];

const CONFIDENCE_STYLES: Record<Example["confidence"], string> = {
  HIGH: "bg-accent-50 text-risk-high border-accent-200",
  MEDIUM: "bg-amber-50 text-risk-medium border-amber-200",
  LOW: "bg-emerald-50 text-risk-low border-emerald-200",
};

export function HeroFindingCard() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % EXAMPLES.length), 3200);
    return () => clearInterval(id);
  }, []);

  const rotateX = useSpring(0, { stiffness: 150, damping: 20 });
  const rotateY = useSpring(0, { stiffness: 150, damping: 20 });

  function handleMouseMove(e: MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    rotateY.set((px - 0.5) * 10);
    rotateX.set((0.5 - py) * 10);
  }

  function handleMouseLeave() {
    rotateX.set(0);
    rotateY.set(0);
  }

  // `index` is always kept in [0, EXAMPLES.length) by the interval above, so this is safe.
  const current = EXAMPLES[index] as Example;

  return (
    <div className="[perspective:1200px]">
      <motion.div
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ rotateX, rotateY }}
        className="relative mx-auto w-full max-w-sm rounded-2xl border border-ink-100 bg-white p-5 shadow-card [transform-style:preserve-3d]"
      >
        <div className="flex items-center justify-between text-[11px] font-medium text-ink-400">
          <span>Example finding</span>
          <span className="flex gap-1">
            {EXAMPLES.map((_, i) => (
              <span
                key={i}
                className={`h-1 w-4 rounded-full transition-colors duration-300 ${
                  i === index ? "bg-ink-500" : "bg-ink-100"
                }`}
              />
            ))}
          </span>
        </div>

        <div className="relative mt-4 h-40 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={current.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="absolute inset-0 flex flex-col gap-2.5"
            >
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-medium text-ink-600">
                  {current.category}
                </span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${CONFIDENCE_STYLES[current.confidence]}`}
                >
                  {current.confidence.charAt(0) + current.confidence.slice(1).toLowerCase()} confidence
                </span>
              </div>
              <h3 className="text-sm font-semibold text-ink-950">{current.title}</h3>
              <p className="text-2xl font-semibold tabular-nums text-ink-950">{current.amount}</p>
              <p className="text-xs text-ink-400">{current.detail}</p>
              <div className="mt-1 flex items-center gap-1.5 text-xs font-medium text-ink-400">
                <span className="h-1.5 w-1.5 rounded-full bg-risk-low" />
                Evidence &amp; calculation attached
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
