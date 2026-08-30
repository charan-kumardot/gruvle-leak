"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Wordmark } from "@/components/ui/Logo";

const NAV_ITEMS = [
  { href: "/overview", label: "Overview", icon: OverviewIcon },
  { href: "/leaks", label: "Leaks", icon: LeaksIcon },
  { href: "/data", label: "Data", icon: DataIcon },
  { href: "/integrations", label: "Integrations", icon: IntegrationsIcon },
  { href: "/reports", label: "Reports", icon: ReportsIcon },
  { href: "/actions", label: "Actions", icon: ActionsIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
] as const;

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-ink-100 bg-white md:flex">
        <div className="px-6 py-6">
          <Link href="/overview" className="text-lg text-ink-950">
            <Wordmark />
          </Link>
        </div>

        <div className="px-4">
          <Link href="/data" className="block">
            <Button className="w-full justify-center">New scan</Button>
          </Link>
        </div>

        <nav className="mt-6 flex flex-1 flex-col gap-0.5 px-3">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-ink-100 text-ink-950"
                    : "text-ink-500 hover:bg-ink-50 hover:text-ink-900"
                }`}
              >
                <Icon active={active} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-ink-100 px-4 py-4">
          <button
            onClick={handleLogout}
            className="text-sm font-medium text-ink-400 hover:text-ink-800"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="flex items-center justify-between border-b border-ink-100 bg-white px-4 py-3 md:hidden">
        <Link href="/overview" className="text-base text-ink-950">
          <Wordmark />
        </Link>
        <div className="flex items-center gap-2">
          <Link href="/data">
            <Button size="sm">New scan</Button>
          </Link>
        </div>
      </header>

      {/* Mobile bottom tab bar */}
      <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-ink-100 bg-white/95 backdrop-blur md:hidden">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${
                active ? "text-ink-950" : "text-ink-400"
              }`}
            >
              <Icon active={active} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

type IconProps = { active?: boolean };

function iconClass(active?: boolean) {
  return `h-[18px] w-[18px] shrink-0 ${active ? "text-ink-950" : "text-current"}`;
}

function OverviewIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <rect x="3" y="3" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="11" y="3" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="3" y="11" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="11" y="11" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function LeaksIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <path
        d="M10 2.5c2.5 3 4.5 5.8 4.5 8.3a4.5 4.5 0 11-9 0c0-2.5 2-5.3 4.5-8.3z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DataIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <path d="M4 6l6-3 6 3-6 3-6-3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M4 10l6 3 6-3M4 14l6 3 6-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IntegrationsIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <circle cx="6" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="14" cy="14" r="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 7.5l4 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ReportsIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <rect x="4" y="2.5" width="12" height="15" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 7h6M7 10.5h6M7 14h3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ActionsIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <path d="M4 10.5l3.5 3.5L16 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SettingsIcon({ active }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={iconClass(active)} aria-hidden="true">
      <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M10 2.5v2M10 15.5v2M17.5 10h-2M4.5 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3L4.9 4.9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
