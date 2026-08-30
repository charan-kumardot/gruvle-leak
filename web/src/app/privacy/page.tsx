import { PolicyLayout } from "@/components/marketing/PolicyLayout";

export default function PrivacyPage() {
  return (
    <PolicyLayout title="Privacy" updated="August 30, 2026">
      <p>
        Gruvle Leak analyzes business data you choose to upload — orders, invoices, contracts,
        inventory exports — to identify potential revenue leakage. This page describes how that
        data is handled.
      </p>

      <section>
        <h2 className="text-base font-semibold text-ink-900">What we store</h2>
        <p className="mt-2">
          Your account details (email, business name, industry, currency), the files you upload,
          and the findings, evidence, and reports Gruvle generates from them. Every business is
          isolated at the database level — no other account can read or write your data.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">What we don&apos;t do</h2>
        <ul className="mt-2 flex flex-col gap-2">
          <li>We never use your uploaded business data to train any AI model.</li>
          <li>We never make an uploaded file, dataset, or report publicly accessible.</li>
          <li>We never sell or share your data with third parties for marketing purposes.</li>
          <li>We minimize what we send to external AI providers, and never send raw file contents beyond what a specific mapping or explanation request needs.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Your controls</h2>
        <p className="mt-2">
          You can delete an individual file, a dataset, a scan, a report, or your entire account
          at any time from within the product. Deletion removes the underlying records; it is
          not reversible.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Third parties</h2>
        <p className="mt-2">
          We use Appwrite for authentication, database, and file storage, and, where configured,
          an AI provider (Google Gemini, Groq, or OpenRouter) to assist with column mapping and
          explaining findings — never to compute a financial figure. If no AI provider is
          configured, the product runs on a fully deterministic, zero-external-call fallback.
        </p>
      </section>

      <p className="text-xs text-ink-400">
        This page describes how Gruvle Leak actually behaves today. It is not a substitute for
        formal legal counsel — if you need a reviewed data processing agreement for your
        organization, contact us.
      </p>
    </PolicyLayout>
  );
}
