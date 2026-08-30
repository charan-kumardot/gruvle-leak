"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, motion, useMotionValue, useSpring } from "framer-motion";

/** Counts up from 0 to `value` once it scrolls into view. Purely cosmetic — the underlying value is real. */
export function AnimatedCounter({
  value,
  prefix = "",
  suffix = "",
  formatter,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  formatter?: (n: number) => string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { duration: 1200, bounce: 0 });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (inView) motionValue.set(value);
  }, [inView, value, motionValue]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (v) => {
      const rounded = Math.round(v);
      setDisplay(formatter ? formatter(rounded) : rounded.toLocaleString("en-IN"));
    });
    return unsubscribe;
  }, [spring, formatter]);

  return (
    <motion.span ref={ref}>
      {prefix}
      {display}
      {suffix}
    </motion.span>
  );
}
