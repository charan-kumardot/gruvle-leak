const POINTS = [
  {
    title: "Your data stays yours",
    description:
      "Never used to train any model. Uploaded files are private by default — no public URL ever exposes them.",
  },
  {
    title: "Delete anything, anytime",
    description: "Individual files, datasets, scans, reports, or your whole account — deletion is always available.",
  },
  {
    title: "Strict business isolation",
    description:
      "Every business is its own isolated tenant at the database level. One account can never see another's data.",
  },
  {
    title: "Nothing sent without approval",
    description:
      "Gruvle drafts recommended actions — emails, checklists, outreach — but never sends or changes anything without you approving it first.",
  },
];

export function TrustSecurity() {
  return (
    <section className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">Built to be trusted with your numbers</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Private by default. Verifiable by design.
          </h2>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {POINTS.map((p) => (
            <div key={p.title} className="flex flex-col gap-2">
              <div className="h-8 w-8 rounded-full border border-ink-200 bg-paper" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-ink-900">{p.title}</h3>
              <p className="text-sm leading-relaxed text-ink-500">{p.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
