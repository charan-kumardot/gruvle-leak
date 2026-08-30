"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Reveal } from "@/components/marketing/Reveal";

export function FinalCta() {
  return (
    <section className="border-t border-ink-100">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-5 px-6 py-20 text-center">
        <Reveal className="flex flex-col items-center gap-5">
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
            See what your data has been hiding.
          </h2>
          <p className="max-w-md text-sm leading-relaxed text-ink-500">
            Upload one file. Get evidence-backed findings in minutes. No bank connection, no
            credit card, no commitment.
          </p>
          <Link href="/signup">
            <Button size="lg" className="transition-transform hover:scale-[1.03] active:scale-[0.98]">
              Find my leaks
            </Button>
          </Link>
        </Reveal>
      </div>
    </section>
  );
}
