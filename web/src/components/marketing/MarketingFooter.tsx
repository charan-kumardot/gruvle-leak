import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t border-ink-100 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="max-w-3xl text-xs leading-relaxed text-ink-400">
          Gruvle identifies potential revenue leakage from the data you provide. Findings may
          require human review and should not be treated as accounting, tax, legal, or
          financial advice.
        </p>
        <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-xs text-ink-400">&copy; {new Date().getFullYear()} Gruvle Leak.</span>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-400">
            <a href="#how-it-works" className="hover:text-ink-700">
              How it works
            </a>
            <a href="#pricing" className="hover:text-ink-700">
              Pricing
            </a>
            <Link href="/privacy" className="hover:text-ink-700">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-ink-700">
              Terms
            </Link>
            <Link href="/security" className="hover:text-ink-700">
              Security
            </Link>
            <Link href="/login" className="hover:text-ink-700">
              Log in
            </Link>
            <Link href="/signup" className="hover:text-ink-700">
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
