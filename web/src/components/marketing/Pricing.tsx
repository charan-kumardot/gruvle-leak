import Link from "next/link";
import { Button } from "@/components/ui/Button";

interface Tier {
  name: string;
  price: string;
  priceNote?: string;
  description: string;
  features: string[];
  cta: string;
  href: string;
  highlighted?: boolean;
}

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "₹0",
    description: "Enough to see whether Gruvle finds anything worth acting on.",
    features: ["3 scans / month", "CSV, Excel, JSON, PDF uploads", "Full evidence & calculations", "1 seat"],
    cta: "Start free",
    href: "/signup",
  },
  {
    name: "Starter",
    price: "Coming soon",
    description: "For a single team getting serious about closing leaks every month.",
    features: ["More scans / month", "Larger file sizes", "Priority detector updates", "Email support"],
    cta: "Get notified",
    href: "/signup",
    highlighted: true,
  },
  {
    name: "Growth",
    price: "Coming soon",
    description: "For growing teams that want this running continuously, not just once.",
    features: ["Scheduled recurring scans", "Multiple team seats", "Exportable audit trail", "Priority support"],
    cta: "Get notified",
    href: "/signup",
  },
  {
    name: "Business",
    price: "Talk to us",
    description: "For teams that need integrations, SSO, or a tailored rollout.",
    features: ["Custom detector tuning", "SSO & advanced permissions", "Dedicated onboarding", "SLA-backed support"],
    cta: "Contact us",
    href: "/signup",
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="border-t border-ink-100">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-500">Pricing</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            Start free. Pay only once it&apos;s finding you money.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-500 sm:text-base">
            Gruvle is in early access — paid tier pricing is still being finalized based on
            what early customers actually need. The free tier is fully functional today.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`flex flex-col rounded-xl border p-6 ${
                tier.highlighted ? "border-ink-900 bg-ink-950 text-white shadow-card" : "border-ink-100 bg-white shadow-card"
              }`}
            >
              <h3 className={`text-sm font-semibold ${tier.highlighted ? "text-white" : "text-ink-900"}`}>
                {tier.name}
              </h3>
              <p className={`mt-3 text-2xl font-semibold tracking-tight ${tier.highlighted ? "text-white" : "text-ink-950"}`}>
                {tier.price}
              </p>
              <p className={`mt-3 text-sm leading-relaxed ${tier.highlighted ? "text-ink-300" : "text-ink-500"}`}>
                {tier.description}
              </p>
              <ul className="mt-5 flex flex-1 flex-col gap-2.5">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className={`flex items-start gap-2 text-sm ${tier.highlighted ? "text-ink-200" : "text-ink-600"}`}
                  >
                    <span className={`mt-1.5 h-1 w-1 shrink-0 rounded-full ${tier.highlighted ? "bg-ink-400" : "bg-ink-300"}`} />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href={tier.href} className="mt-6">
                <Button variant={tier.highlighted ? "secondary" : "primary"} className="w-full">
                  {tier.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
