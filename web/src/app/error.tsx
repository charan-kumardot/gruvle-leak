"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Wordmark } from "@/components/ui/Logo";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="px-6 py-6">
        <Link href="/" className="text-lg text-ink-950">
          <Wordmark />
        </Link>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 pb-24 text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-accent-500">Something went wrong</p>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">
          That didn&apos;t work — this has been logged.
        </h1>
        <p className="max-w-sm text-sm leading-relaxed text-ink-500">
          Please try again. If it keeps happening, the underlying data or connection may need a
          closer look.
        </p>
        <div className="mt-2 flex gap-3">
          <Button variant="secondary" onClick={() => reset()}>
            Try again
          </Button>
          <Link href="/overview">
            <Button>Back to dashboard</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
