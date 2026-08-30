import { MarketingNav } from "@/components/marketing/MarketingNav";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export function PolicyLayout({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingNav />
      <main className="flex-1">
        <div className="mx-auto max-w-2xl px-6 py-16">
          <h1 className="text-3xl font-semibold tracking-tight text-ink-950">{title}</h1>
          <p className="mt-2 text-sm text-ink-400">Last updated {updated}</p>
          <div className="prose-policy mt-10 flex flex-col gap-6 text-sm leading-relaxed text-ink-600">
            {children}
          </div>
        </div>
      </main>
      <MarketingFooter />
    </div>
  );
}
