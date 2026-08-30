/**
 * Server-side verification that the caller's Appwrite session actually
 * belongs to the business/team they claim to be acting as.
 *
 * The worker service trusts every request carrying WORKER_API_INTERNAL_TOKEN
 * unconditionally — that token only proves "this call came from our Next.js
 * server," not "this specific end user owns this business." That check has
 * to happen here, before we ever forward a request to the worker, or any
 * signed-in user could pass an arbitrary business_id/team_id and read or
 * write another business's data (the worker's server API key is not itself
 * constrained by Appwrite document permissions — see
 * worker/app/db/repositories.py's module docstring for the same point on
 * the other side of this boundary).
 *
 * The browser calls `account.createJWT()` (Appwrite Web SDK) right before
 * each request and sends it as `Authorization: Bearer <jwt>`. A JWT is
 * short-lived (~15 min) and scoped to one user's session. We use it to spin
 * up a request-scoped Appwrite client with no elevated privileges and ask
 * Appwrite itself "is this user a member of this team?" — Appwrite refuses
 * (401/404) if not, which is what we rely on.
 */
import "server-only";

import { Account, Client, Teams } from "appwrite";

export class UnauthorizedError extends Error {}

export function extractJwt(req: Request): string {
  const auth = req.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) {
    throw new UnauthorizedError("Missing Authorization: Bearer <jwt> header.");
  }
  return auth.slice("Bearer ".length);
}

/** Throws UnauthorizedError if the JWT's user is not a member of teamId. */
export async function requireTeamMembership(jwt: string, teamId: string): Promise<void> {
  const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT;
  const projectId = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID;
  if (!endpoint || !projectId) {
    throw new UnauthorizedError("Appwrite is not configured on the server.");
  }

  const client = new Client().setEndpoint(endpoint).setProject(projectId).setJWT(jwt);
  const teams = new Teams(client);
  try {
    await teams.get(teamId);
  } catch {
    throw new UnauthorizedError("You do not have access to this business.");
  }
}

/**
 * Resolves the REAL user id behind a JWT by asking Appwrite directly —
 * never trust a client-supplied userId for anything destructive (e.g.
 * account deletion). A JWT can't be forged to claim a different user's
 * identity, so this is the only trustworthy source of "who is this."
 */
export async function requireOwnUserId(jwt: string): Promise<string> {
  const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT;
  const projectId = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID;
  if (!endpoint || !projectId) {
    throw new UnauthorizedError("Appwrite is not configured on the server.");
  }

  const client = new Client().setEndpoint(endpoint).setProject(projectId).setJWT(jwt);
  const account = new Account(client);
  try {
    const me = await account.get();
    return me.$id;
  } catch {
    throw new UnauthorizedError("This session is no longer valid — please log in again.");
  }
}
