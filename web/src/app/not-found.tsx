import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Wordmark } from "@/components/ui/Logo";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="px-6 py-6">
        <Link href="/" className="text-lg text-ink-950">
          <Wordmark />
        </Link>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 pb-24 text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-ink-400">404</p>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">
          This page went looking for money and got lost.
        </h1>
        <p className="max-w-sm text-sm leading-relaxed text-ink-500">
          The page you&apos;re looking for doesn&apos;t exist or may have moved.
        </p>
        <Link href="/" className="mt-2">
          <Button>Back to home</Button>
        </Link>
      </main>
    </div>
  );
}
