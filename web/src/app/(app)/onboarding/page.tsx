"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ID, Permission, Role } from "appwrite";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { APPWRITE_DATABASE_ID, COLLECTIONS, databases, teams } from "@/lib/appwrite";
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

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { business, loading: businessLoading } = useCurrentBusiness();

  const [industry, setIndustry] = useState<Industry>("other");
  const [currency, setCurrency] = useState<CurrencyCode>("INR");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already onboarded — skip straight to the dashboard.
  useEffect(() => {
    if (!businessLoading && business) {
      router.replace("/overview");
    }
  }, [businessLoading, business, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    setError(null);
    try {
      const businessName = user.name || "My business";
      const team = await teams.create(ID.unique(), businessName);

      await databases.createDocument(
        APPWRITE_DATABASE_ID,
        COLLECTIONS.businesses,
        ID.unique(),
        {
          owner_user_id: user.$id,
          team_id: team.$id,
          name: businessName,
          industry,
          currency,
        },
        [
          Permission.read(Role.team(team.$id)),
          Permission.update(Role.team(team.$id)),
          Permission.delete(Role.team(team.$id)),
        ]
      );

      router.push("/overview");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not finish setting up your business. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col justify-center py-8">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold tracking-tight text-ink-950">
            A couple more details
          </h1>
          <p className="mt-1.5 text-sm text-ink-500">
            This tunes what Gruvle looks for in your data. Takes a few seconds.
          </p>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-ink-700">Business name</span>
              <div className="rounded-lg border border-ink-100 bg-ink-50 px-3.5 py-2.5 text-sm text-ink-500">
                {user?.name || "—"}
              </div>
            </div>

            <Select
              label="Industry"
              name="industry"
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
              name="currency"
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

            <Button type="submit" disabled={submitting} className="mt-1">
              {submitting ? "Setting up…" : "Continue to dashboard"}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
