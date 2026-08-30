import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function MarketingNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-100 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight text-ink-950">
          Gruvle Leak
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium text-ink-500 md:flex">
          <a href="#how-it-works" className="hover:text-ink-900">
            How it works
          </a>
          <a href="#live-demo" className="hover:text-ink-900">
            Live demo
          </a>
          <a href="#pricing" className="hover:text-ink-900">
            Pricing
          </a>
          <a href="#faq" className="hover:text-ink-900">
            FAQ
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/login" className="hidden text-sm font-medium text-ink-600 hover:text-ink-950 sm:inline">
            Log in
          </Link>
          <Link href="/signup">
            <Button size="sm">Find my leaks</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
