export interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "risk";
}

export function StatTile({ label, value, hint, tone = "default" }: StatTileProps) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</p>
      <p
        className={`mt-2 text-2xl font-semibold tabular-nums ${
          tone === "risk" ? "text-accent-600" : "text-ink-950"
        }`}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-400">{hint}</p>}
    </div>
  );
}
