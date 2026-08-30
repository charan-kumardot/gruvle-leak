"use client";

import { motion } from "framer-motion";

/**
 * The brand mark: a ring with a gap, and a drop escaping through it —
 * "Gruvle catches what's leaking." Draws itself in once on mount (the ring
 * traces, then the drop settles into place with a soft spring and picks up
 * a slow, quiet pulse) rather than looping — a persistent nav mark that
 * animated forever would be fatiguing, so this is meant for one-time,
 * high-attention placements (the hero, an empty state, a loading moment).
 */
export function AnimatedLogo({ size = 96, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <motion.path
        d="M10.21,22.89 A9,9 0 1 1 21.79,22.89"
        stroke="#0B0C0E"
        strokeWidth="2.6"
        strokeLinecap="round"
        fill="none"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ pathLength: { duration: 1.1, ease: [0.65, 0, 0.35, 1] }, opacity: { duration: 0.3 } }}
      />
      <motion.circle
        cx="16"
        r="2.3"
        fill="#C1512E"
        initial={{ cy: 17, opacity: 0, scale: 0.4 }}
        animate={{ cy: 25, opacity: 1, scale: [0.4, 1.15, 1, 1.06, 1] }}
        transition={{
          cy: { duration: 0.6, delay: 0.85, ease: [0.34, 1.56, 0.64, 1] },
          opacity: { duration: 0.25, delay: 0.85 },
          scale: { duration: 2.6, delay: 0.85, times: [0, 0.25, 0.4, 0.7, 1], repeat: Infinity, repeatDelay: 1.4 },
        }}
        style={{ transformOrigin: "16px 25px" }}
      />
    </svg>
  );
}
