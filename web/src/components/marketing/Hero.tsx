import Link from "next/link";
import { Button } from "@/components/ui/Button";

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0 text-ink-400" aria-hidden="true">
      <path
        d="M4 10.5l3.5 3.5L16 5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Hero() {
  return (
    <section className="mx-auto max-w-4xl px-6 pb-16 pt-20 text-center sm:pt-28">
      <p className="mb-5 inline-flex items-center rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-500">
        AI revenue-leakage investigator, not another dashboard
      </p>
      <h1 className="text-balance text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl md:text-6xl">
        Find the money your business is losing.
      </h1>
      <p className="mx-auto mt-6 max-w-2xl text-balance text-base leading-relaxed text-ink-500 sm:text-lg">
        Gruvle analyzes your business data to uncover unbilled revenue, pricing inconsistencies,
        missed renewals, invoice mismatches, inventory leakage and other hidden revenue risks —
        with the evidence and calculation behind every number.
      </p>

      <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <Link href="/signup" className="w-full sm:w-auto">
          <Button size="lg" className="w-full sm:w-auto">
            Find my leaks
          </Button>
        </Link>
        <a href="#live-demo" className="w-full sm:w-auto">
          <Button variant="secondary" size="lg" className="w-full sm:w-auto">
            Try the live demo
          </Button>
        </a>
      </div>

      <div className="mx-auto mt-8 flex max-w-xl flex-col items-center gap-2 text-sm text-ink-400 sm:flex-row sm:justify-center sm:gap-6">
        <span className="inline-flex items-center gap-1.5">
          <CheckIcon /> No bank connection required.
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CheckIcon /> Start with CSV, Excel or PDF.
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CheckIcon /> Free to start.
        </span>
      </div>
    </section>
  );
}
