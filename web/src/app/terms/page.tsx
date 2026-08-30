import { PolicyLayout } from "@/components/marketing/PolicyLayout";

export default function TermsPage() {
  return (
    <PolicyLayout title="Terms of use" updated="August 30, 2026">
      <p>
        Gruvle Leak is an early-access product. By using it, you agree to the terms below.
      </p>

      <section>
        <h2 className="text-base font-semibold text-ink-900">What Gruvle is</h2>
        <p className="mt-2">
          Gruvle Leak identifies potential revenue leakage from the business data you provide.
          Findings are generated from deterministic analysis of your data, occasionally
          assisted by AI for column mapping and plain-language explanation — never for the
          underlying calculation. Findings may require human review and should not be treated
          as accounting, tax, legal, or financial advice.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Your responsibilities</h2>
        <ul className="mt-2 flex flex-col gap-2">
          <li>You&apos;re responsible for having the right to upload the data you provide.</li>
          <li>You&apos;re responsible for reviewing findings before acting on them.</li>
          <li>Gruvle never sends customer-facing communications, issues invoices, or changes prices on your behalf — any external action requires your explicit approval.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Early access</h2>
        <p className="mt-2">
          Features, detectors, and pricing are still evolving. We&apos;ll do our best to
          communicate meaningful changes before they affect you.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Limitation of liability</h2>
        <p className="mt-2">
          Gruvle Leak is provided &quot;as is,&quot; without warranty of any kind. We are not
          liable for business decisions made on the basis of a finding without independent
          verification.
        </p>
      </section>

      <p className="text-xs text-ink-400">
        This page describes the product&apos;s actual behavior in plain language. It is not a
        substitute for formal legal counsel — if you need a reviewed agreement for your
        organization, contact us.
      </p>
    </PolicyLayout>
  );
}
