/**
 * Browser-side Appwrite client singleton.
 *
 * This client is configured with only the PUBLIC endpoint + project id and
 * is used for end-user session auth (email/password), and for reading /
 * writing documents scoped to the signed-in user's own Team (per-business
 * multi-tenancy, see worker/app/db/schema.py).
 *
 * It must NEVER receive an Appwrite API key. The server API key lives only
 * in the Python worker's own .env and is never referenced from this app.
 */
import { Account, Client, Databases, Storage, Teams } from "appwrite";

const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT;
const projectId = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID;

if (!endpoint || !projectId) {
  // Fail loudly in dev rather than silently making requests to a blank
  // endpoint — this is almost always a missing .env.local entry.
  console.warn(
    "[appwrite] NEXT_PUBLIC_APPWRITE_ENDPOINT or NEXT_PUBLIC_APPWRITE_PROJECT_ID is not set. " +
      "Auth and data calls will fail until .env.local is configured."
  );
}

const client = new Client();

if (endpoint && projectId) {
  client.setEndpoint(endpoint).setProject(projectId);
}

export const appwriteClient = client;
export const account = new Account(client);
export const databases = new Databases(client);
export const storage = new Storage(client);
export const teams = new Teams(client);

export const APPWRITE_DATABASE_ID =
  process.env.NEXT_PUBLIC_APPWRITE_DATABASE_ID ?? "gruvle_leak";

// Collection ids, mirrored from worker/app/db/schema.py — kept in one place
// so a rename on the worker side only needs to change this file.
export const COLLECTIONS = {
  businesses: "businesses",
  datasets: "datasets",
  scans: "scans",
  leakFindings: "leak_findings",
  leakEvidence: "leak_evidence",
  leakCalculations: "leak_calculations",
  reports: "reports",
} as const;
