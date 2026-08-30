interface FeatureItem {
  category: string;
  title: string;
  description: string;
  live: boolean;
}

const FEATURES: FeatureItem[] = [
  {
    category: "Unbilled",
    title: "Unbilled revenue",
    description: "Completed orders and delivered work with no matching invoice, matched record by record.",
    live: true,
  },
  {
    category: "Pricing",
    title: "Pricing inconsistencies",
    description: "Customers priced well below the norm for a product, with no discount on record explaining why.",
    live: true,
  },
  {
    category: "Invoice",
    title: "Invoice mismatches",
    description: "Invoices that undercharge their matching order, and duplicate invoice records worth a second look.",
    live: true,
  },
  {
    category: "Discount",
    title: "Discount leakage",
    description: "Discounts beyond your policy ceiling, surfaced with the exact records and the excess amount.",
    live: true,
  },
  {
    category: "Renewal",
    title: "Renewal risk",
    description: "Contracts expiring soon or already past their end date, ranked by recurring value at risk.",
    live: true,
  },
  {
    category: "Inventory",
    title: "Inventory exposure",
    description: "Dead and slow-moving stock tying up capital that could be freed or repriced.",
    live: false,
  },
  {
    category: "Customer",
    title: "Customer revenue risk",
    description: "High-value accounts going quiet, before they show up as churn.",
    live: false,
  },
  {
    category: "Contract",
    title: "Contract term drift",
    description: "Billed amounts compared against the terms in your uploaded contracts.",
    live: false,
  },
];

export function Features() {
  return (
    <section className="border-t border-ink-100">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">What Gruvle checks</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Ten ways revenue quietly gets away from you.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Five checks run today, fully deterministic and evidence-backed. The rest are on the
            roadmap — every category already appears in your reports, clearly labeled either way.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div
              key={f.category}
              className="flex flex-col gap-2 rounded-xl border border-ink-100 bg-white p-5 shadow-card"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink-400">{f.category}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    f.live ? "bg-emerald-50 text-risk-low" : "bg-ink-100 text-ink-400"
                  }`}
                >
                  {f.live ? "Live" : "Roadmap"}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-ink-950">{f.title}</h3>
              <p className="text-sm leading-relaxed text-ink-500">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
