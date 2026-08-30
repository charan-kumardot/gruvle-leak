const STEPS = [
  {
    step: "01",
    title: "Upload",
    description:
      "Drop in your billing, invoicing, CRM or inventory exports — CSV, Excel or PDF. No bank connection, no integrations required to start.",
  },
  {
    step: "02",
    title: "Analyze",
    description:
      "Gruvle profiles your data and runs detectors across unbilled revenue, pricing, renewals, invoices, discounts and more.",
  },
  {
    step: "03",
    title: "Evidence",
    description:
      "Every finding comes with the underlying rows, the calculation behind it, and a confidence level — so you can verify, not just trust.",
  },
  {
    step: "04",
    title: "Act",
    description:
      "Review, confirm or dismiss each finding, and turn confirmed ones into a recovery action or a report you can hand to your team.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-ink-100">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">How it works</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Four steps from raw export to a reviewed, evidence-backed finding.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <div key={s.step} className="flex flex-col gap-3">
              <span className="text-sm font-semibold tabular-nums text-accent-500">{s.step}</span>
              <h3 className="text-base font-semibold text-ink-900">{s.title}</h3>
              <p className="text-sm leading-relaxed text-ink-500">{s.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
