import { PolicyLayout } from "@/components/marketing/PolicyLayout";

export default function SecurityPage() {
  return (
    <PolicyLayout title="Security" updated="August 30, 2026">
      <p>
        Business data is sensitive by nature. Here&apos;s how Gruvle Leak is built to protect it.
      </p>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Multi-tenant isolation</h2>
        <p className="mt-2">
          Every business is its own isolated tenant, enforced at the database permission level
          — not just in application code. A user from one business cannot read, list, or modify
          another business&apos;s datasets, scans, or findings, even by guessing an internal ID.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Private storage</h2>
        <p className="mt-2">
          Uploaded files and generated reports are stored in private buckets with no public read
          access. Every access requires an authenticated, permission-checked session.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Upload validation</h2>
        <p className="mt-2">
          Files are never trusted by extension alone — every upload is checked against its
          actual file signature before processing, with size limits enforced throughout.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Untrusted content, treated as untrusted</h2>
        <p className="mt-2">
          Text extracted from your files (including PDFs) is treated strictly as data, never as
          instructions — including in every prompt sent to an AI provider, which is explicitly
          told to disregard anything in your data that looks like a command.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-ink-900">Human approval for external actions</h2>
        <p className="mt-2">
          Gruvle never sends a customer-facing message, issues an invoice, or changes a price on
          its own. Every recommended action requires your explicit approval before anything
          leaves the app.
        </p>
      </section>

      <p>
        Found a security issue? We&apos;d appreciate a private report before any public
        disclosure — contact us directly.
      </p>
    </PolicyLayout>
  );
}
