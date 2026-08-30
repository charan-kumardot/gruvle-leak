import type { HTMLAttributes } from "react";
import type { Confidence, FindingStatus } from "@/lib/types";

type Tone = "neutral" | "high" | "medium" | "low" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-ink-100 text-ink-600",
  high: "bg-accent-50 text-risk-high border border-accent-200",
  medium: "bg-amber-50 text-risk-medium border border-amber-200",
  low: "bg-emerald-50 text-risk-low border border-emerald-200",
  accent: "bg-accent-50 text-accent-600 border border-accent-200",
};

export function Badge({
  tone = "neutral",
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`}
      {...props}
    />
  );
}

const confidenceTone: Record<Confidence, Tone> = {
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <Badge tone={confidenceTone[confidence]}>{confidence} confidence</Badge>;
}

const statusLabel: Record<FindingStatus, string> = {
  NEW: "New",
  REVIEWING: "Reviewing",
  CONFIRMED: "Confirmed",
  DISMISSED: "Dismissed",
  RESOLVED: "Resolved",
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  const tone: Tone = status === "CONFIRMED" ? "accent" : status === "RESOLVED" ? "low" : "neutral";
  return <Badge tone={tone}>{statusLabel[status]}</Badge>;
}
