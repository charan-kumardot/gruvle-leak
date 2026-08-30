const SYMPTOMS = [
  "A completed job that never got invoiced.",
  "A long-time customer quietly paying last year's price.",
  "A contract that renewed itself as a habit, not a decision.",
  "A discount that was meant to be one-time, three orders ago.",
];

export function ProblemSolution() {
  return (
    <section className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-5xl px-6 py-20">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">The problem</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              Revenue doesn&apos;t usually disappear all at once.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              It leaks — one unbilled order, one stale discount, one renewal nobody followed up
              on. None of it shows up in your P&amp;L as a single line. It just quietly lowers
              every number on it.
            </p>
            <ul className="mt-6 flex flex-col gap-3">
              {SYMPTOMS.map((s) => (
                <li key={s} className="flex items-start gap-2.5 text-sm text-ink-600">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-300" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">The approach</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              You already have the data. Gruvle reads it like an investigator, not a dashboard.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              Upload the exports you already run — orders, invoices, contracts, inventory.
              Deterministic detectors do the arithmetic (never an AI model guessing at numbers),
              and every finding comes with the exact records and calculation behind it, so you
              can verify it in thirty seconds, not take our word for it.
            </p>
            <p className="mt-4 text-sm leading-relaxed text-ink-500 sm:text-base">
              Nothing is ever stated as certain unless the data proves it. You&apos;ll see
              &quot;potential leakage&quot; and &quot;at-risk revenue&quot; — hedged language for
              hedged confidence, always paired with what we don&apos;t know.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
