"use client";

/**
 * Client-side lookup of the signed-in user's business document.
 *
 * One business per user in this pass (spec doesn't yet require multi-business
 * per account). Looks up by `owner_user_id` in the `businesses` collection.
 * Returns `null` (not loading) once resolved with no match, so callers can
 * route to onboarding.
 */
import { useCallback, useEffect, useState } from "react";
import { Query } from "appwrite";
import { APPWRITE_DATABASE_ID, COLLECTIONS, databases } from "@/lib/appwrite";
import type { Business } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";

export function useCurrentBusiness() {
  const { user } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setBusiness(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await databases.listDocuments(APPWRITE_DATABASE_ID, COLLECTIONS.businesses, [
        Query.equal("owner_user_id", user.$id),
        Query.limit(1),
      ]);
      const doc = res.documents[0];
      // Appwrite documents carry the id as `$id`; normalize to `id` here,
      // once, so every consumer of `Business` can rely on `.id` existing —
      // casting the raw document straight to `Business` leaves `.id`
      // `undefined` at runtime even though TypeScript won't catch it.
      setBusiness(doc ? ({ ...doc, id: doc.$id } as unknown as Business) : null);
    } catch (err) {
      // Most likely cause during early development: the `businesses`
      // collection hasn't been provisioned in Appwrite yet.
      setError(err instanceof Error ? err.message : "Could not load business.");
      setBusiness(null);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { business, loading, error, refresh };
}
