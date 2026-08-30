"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { AppNav } from "@/components/nav/AppNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  // Never render protected content while auth state is unresolved or the
  // user turns out to be unauthenticated — show a loading state instead of
  // a flash of the dashboard.
  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="flex items-center gap-2 text-sm text-ink-400">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
          Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-paper md:flex-row">
      <AppNav />
      <main className="flex-1 pb-16 md:pb-0">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
