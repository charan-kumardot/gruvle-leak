"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} className="group relative py-1 hover:text-ink-900">
      {children}
      <span className="absolute inset-x-0 -bottom-0.5 h-px scale-x-0 bg-ink-900 transition-transform duration-200 group-hover:scale-x-100" />
    </a>
  );
}

export function MarketingNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-100 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight text-ink-950">
          Gruvle Leak
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium text-ink-500 md:flex">
          <NavLink href="#how-it-works">How it works</NavLink>
          <NavLink href="#live-demo">Live demo</NavLink>
          <NavLink href="#pricing">Pricing</NavLink>
          <NavLink href="#faq">FAQ</NavLink>
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/login" className="hidden text-sm font-medium text-ink-600 hover:text-ink-950 sm:inline">
            Log in
          </Link>
          <Link href="/signup">
            <Button size="sm" className="transition-transform hover:scale-[1.04] active:scale-[0.97]">
              Find my leaks
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
