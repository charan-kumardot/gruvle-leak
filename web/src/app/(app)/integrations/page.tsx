"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { useCurrentBusiness } from "@/lib/use-current-business";
import { useAuth } from "@/lib/auth-context";
import {
  ApiClientError,
  connectIntegration,
  disconnectIntegration,
  listIntegrationConnections,
  listIntegrationProviders,
  syncIntegration,
  type IntegrationConnection,
  type IntegrationProvider,
} from "@/lib/api-client";

const PROVIDER_COPY: Record<string, { description: string; notAvailableReason?: string }> = {
  shopify: {
    description: "Pull orders straight from your Shopify store — no exports, stays up to date whenever you sync.",
  },
  hubspot: {
    description: "Pull deals from HubSpot as revenue records.",
    notAvailableReason: "Coming soon — HubSpot Private Apps use a simple API key, same connection pattern as Shopify.",
  },
  quickbooks: {
    description: "Pull invoices and payments from QuickBooks.",
    notAvailableReason: "Coming soon — requires a registered Intuit developer app and Intuit's app review process.",
  },
  zoho: {
    description: "Pull invoices from Zoho Books.",
    notAvailableReason: "Coming soon — Zoho supports self-generated OAuth credentials, similar to Shopify's model.",
  },
  salesforce: {
    description: "Pull opportunities from Salesforce as revenue records.",
    notAvailableReason: "Coming soon — requires a Salesforce Connected App, which a business admin can create in their own org.",
  },
};

export default function IntegrationsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { business, loading: businessLoading } = useCurrentBusiness();
  const [providers, setProviders] = useState<IntegrationProvider[] | null>(null);
  const [connections, setConnections] = useState<IntegrationConnection[] | null>(null);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refreshConnections() {
    if (!business) return;
    const list = await listIntegrationConnections(business.id, business.team_id);
    setConnections(list);
  }

  useEffect(() => {
    listIntegrationProviders().then(setProviders).catch(() => setProviders([]));
  }, []);

  useEffect(() => {
    if (business) refreshConnections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [business]);

  async function handleSync(connectionId: string) {
    if (!business) return;
    setBusyId(connectionId);
    setError(null);
    try {
      const result = await syncIntegration(connectionId, business.id, business.team_id);
      await refreshConnections();
      router.push(`/data?syncedDataset=${encodeURIComponent(result.dataset_id)}`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Sync failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDisconnect(connectionId: string) {
    if (!business) return;
    setBusyId(connectionId);
    setError(null);
    try {
      await disconnectIntegration(connectionId, business.team_id);
      await refreshConnections();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Could not disconnect.");
    } finally {
      setBusyId(null);
    }
  }

  if (businessLoading || providers === null) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-500" />
        Loading…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Integrations</h1>
        <p className="mt-1 text-sm text-ink-500">
          Connect a live data source instead of exporting files by hand. Synced data flows through the
          exact same detectors and evidence trail as an uploaded file.
        </p>
      </div>

      {error && <p className="text-sm text-accent-600">{error}</p>}
      {!business && (
        <p className="text-sm text-ink-400">
          Finish{" "}
          <a href="/onboarding" className="font-medium text-ink-700 underline">
            onboarding
          </a>{" "}
          before connecting a data source.
        </p>
      )}

      {connections && connections.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-ink-900">Connected</h2>
          <div className="mt-3 flex flex-col gap-3">
            {connections.map((c) => (
              <Card key={c.id}>
                <CardBody className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-ink-950">{c.display_name}</p>
                      <Badge tone={c.status === "connected" ? "low" : c.status === "error" ? "high" : "neutral"}>
                        {c.status}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-ink-400">
                      {c.last_synced_at ? `Last synced ${new Date(c.last_synced_at).toLocaleString()}` : "Never synced"}
                      {c.last_error && c.status === "error" ? ` — ${c.last_error}` : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" disabled={busyId === c.id} onClick={() => handleDisconnect(c.id)}>
                      Disconnect
                    </Button>
                    <Button size="sm" disabled={busyId === c.id} onClick={() => handleSync(c.id)}>
                      {busyId === c.id ? "Syncing…" : "Sync now"}
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold text-ink-900">Available</h2>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {providers.map((p) => {
            const copy = PROVIDER_COPY[p.key] ?? { description: "" };
            return (
              <Card key={p.key}>
                <CardBody className="flex flex-col gap-3 pt-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-ink-950">{p.label}</h3>
                    {!p.available && <Badge tone="neutral">Coming soon</Badge>}
                  </div>
                  <p className="text-sm leading-relaxed text-ink-500">
                    {p.available ? copy.description : copy.notAvailableReason ?? copy.description}
                  </p>
                  {p.available && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="mt-1 w-full"
                      onClick={() => setConnectingProvider(p.key)}
                      disabled={!business}
                    >
                      Connect
                    </Button>
                  )}
                </CardBody>
              </Card>
            );
          })}
        </div>
      </div>

      {connectingProvider === "shopify" && business && user && (
        <ShopifyConnectDialog
          businessId={business.id}
          teamId={business.team_id}
          userId={user.$id}
          onClose={() => setConnectingProvider(null)}
          onConnected={async () => {
            setConnectingProvider(null);
            await refreshConnections();
          }}
        />
      )}
    </div>
  );
}

function ShopifyConnectDialog({
  businessId,
  teamId,
  userId,
  onClose,
  onConnected,
}: {
  businessId: string;
  teamId: string;
  userId: string;
  onClose: () => void;
  onConnected: () => void;
}) {
  const [shopDomain, setShopDomain] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await connectIntegration(businessId, teamId, userId, "shopify", {
        shop_domain: shopDomain.trim(),
        access_token: accessToken.trim(),
      });
      onConnected();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Could not connect to Shopify.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink-950/40 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <h2 className="text-base font-semibold text-ink-900">Connect Shopify</h2>
          <p className="mt-1 text-xs text-ink-400">
            Uses a private Custom App token — nothing to review or approve, generated in your own
            Shopify admin in about a minute.
          </p>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Shop domain"
              placeholder="my-store.myshopify.com"
              value={shopDomain}
              onChange={(e) => setShopDomain(e.target.value)}
              required
            />
            <Input
              label="Admin API access token"
              placeholder="shpat_..."
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              required
            />
            <details className="rounded-lg bg-paper px-3.5 py-2.5 text-xs text-ink-500">
              <summary className="cursor-pointer font-medium text-ink-700">How do I get this?</summary>
              <ol className="mt-2 flex list-decimal flex-col gap-1 pl-4">
                <li>In your Shopify admin: Settings → Apps and sales channels → Develop apps</li>
                <li>Create an app, name it anything (e.g. &quot;Gruvle Leak&quot;)</li>
                <li>Configure Admin API scopes: enable read_orders, read_products, read_customers</li>
                <li>Install the app, then reveal and copy the Admin API access token</li>
              </ol>
            </details>

            {error && <p className="text-sm text-accent-600">{error}</p>}

            <div className="mt-1 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Connecting…" : "Connect"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
