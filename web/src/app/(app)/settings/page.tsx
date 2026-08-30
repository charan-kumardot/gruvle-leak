"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { APPWRITE_DATABASE_ID, COLLECTIONS, databases } from "@/lib/appwrite";
import type { CurrencyCode, Industry } from "@/lib/types";

const INDUSTRIES: { value: Industry; label: string }[] = [
  { value: "saas", label: "SaaS" },
  { value: "agency", label: "Agency" },
  { value: "consulting", label: "Consulting" },
  { value: "restaurant", label: "Restaurant" },
  { value: "hospitality", label: "Hospitality" },
  { value: "retail", label: "Retail" },
  { value: "logistics", label: "Logistics" },
  { value: "service_business", label: "Service business" },
  { value: "distributor", label: "Distributor" },
  { value: "small_manufacturer", label: "Small manufacturer" },
  { value: "other", label: "Other" },
];

const CURRENCIES: CurrencyCode[] = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "CAD"];

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { business, loading, refresh } = useCurrentBusiness();

  const [industry, setIndustry] = useState<Industry>("other");
  const [currency, setCurrency] = useState<CurrencyCode>("INR");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (business) {
      setIndustry((business.industry as Industry) ?? "other");
      setCurrency(business.currency);
    }
  }, [business]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!business) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await databases.updateDocument(APPWRITE_DATABASE_ID, COLLECTIONS.businesses, business.id, {
        industry,
        currency,
      });
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Settings</h1>
        <p className="mt-1 text-sm text-ink-500">
          Manage your account and business profile.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-ink-900">Account</h2>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-ink-700">Email</span>
            <div className="rounded-lg border border-ink-100 bg-ink-50 px-3.5 py-2.5 text-sm text-ink-500">
              {user?.email ?? "—"}
            </div>
          </div>
          <div>
            <Button variant="secondary" size="sm" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-ink-900">Business profile</h2>
        </CardHeader>
        <CardBody>
          {loading ? (
            <p className="text-sm text-ink-400">Loading…</p>
          ) : !business ? (
            <p className="text-sm text-ink-400">
              No business profile found yet. Complete{" "}
              <a href="/onboarding" className="font-medium text-ink-700 underline">
                onboarding
              </a>{" "}
              to set one up.
            </p>
          ) : (
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-ink-700">Business name</span>
                <div className="rounded-lg border border-ink-100 bg-ink-50 px-3.5 py-2.5 text-sm text-ink-500">
                  {business.name}
                </div>
              </div>
              <Select
                label="Industry"
                value={industry}
                onChange={(e) => setIndustry(e.target.value as Industry)}
              >
                {INDUSTRIES.map((i) => (
                  <option key={i.value} value={i.value}>
                    {i.label}
                  </option>
                ))}
              </Select>
              <Select
                label="Currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value as CurrencyCode)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
              {error && <p className="text-sm text-accent-600">{error}</p>}
              {saved && <p className="text-sm text-risk-low">Saved.</p>}
              <div>
                <Button type="submit" size="sm" disabled={saving}>
                  {saving ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </form>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

