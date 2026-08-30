"use client";

/**
 * Client-side reads/writes of scan and finding data, straight against
 * Appwrite via the Web SDK. These documents already carry team-scoped
 * permissions (Permission.read/update(Role.team(team_id)) — see
 * worker/app/db/repositories.py), so Appwrite itself enforces that a user
 * can only see their own business's scans and findings; there's no need to
 * proxy these through the worker or re-implement that check here.
 *
 * Only operations that need the Python worker's logic (parsing a file,
 * running detection, rendering a report export) go through `worker-api.ts`
 * via the /api/* route handlers instead — see lib/worker-api.ts's header.
 */
import { Query } from "appwrite";
import { APPWRITE_DATABASE_ID, COLLECTIONS, databases } from "@/lib/appwrite";
import type { Finding, FindingStatus, Scan } from "@/lib/types";

function normalizeScan(doc: Record<string, unknown>): Scan {
  return { ...doc, id: doc.$id as string } as unknown as Scan;
}

function normalizeFinding(doc: Record<string, unknown>): Finding {
  return { ...doc, id: doc.$id as string } as unknown as Finding;
}

/** Most recent scans for a business, newest first. */
export async function listScans(teamId: string, limit = 20): Promise<Scan[]> {
  const res = await databases.listDocuments(APPWRITE_DATABASE_ID, COLLECTIONS.scans, [
    Query.equal("team_id", teamId),
    Query.orderDesc("$createdAt"),
    Query.limit(limit),
  ]);
  return res.documents.map(normalizeScan);
}

export async function getScan(scanId: string): Promise<Scan> {
  const doc = await databases.getDocument(APPWRITE_DATABASE_ID, COLLECTIONS.scans, scanId);
  return normalizeScan(doc as unknown as Record<string, unknown>);
}

/** All findings for one scan, without evidence/calculation (list view). */
export async function listFindings(scanId: string): Promise<Finding[]> {
  const res = await databases.listDocuments(APPWRITE_DATABASE_ID, COLLECTIONS.leakFindings, [
    Query.equal("scan_id", scanId),
    Query.orderDesc("priority_score"),
    Query.limit(200),
  ]);
  return res.documents.map(normalizeFinding);
}

/** One finding with its evidence and calculation joined in (detail view). */
export async function getFindingWithDetail(findingId: string): Promise<Finding> {
  const doc = await databases.getDocument(APPWRITE_DATABASE_ID, COLLECTIONS.leakFindings, findingId);
  const finding = normalizeFinding(doc as unknown as Record<string, unknown>);

  const [evidenceRes, calcRes] = await Promise.all([
    databases.listDocuments(APPWRITE_DATABASE_ID, COLLECTIONS.leakEvidence, [
      Query.equal("finding_id", findingId),
      Query.limit(50),
    ]),
    databases.listDocuments(APPWRITE_DATABASE_ID, COLLECTIONS.leakCalculations, [
      Query.equal("finding_id", findingId),
      Query.limit(1),
    ]),
  ]);

  finding.evidence = evidenceRes.documents.map((e) => ({
    id: e.$id,
    dataset_id: e.dataset_id,
    row_index: e.row_index,
    display_fields: JSON.parse(e.display_fields_json || "{}"),
  }));

  const calcDoc = calcRes.documents[0];
  finding.calculation = calcDoc
    ? {
        method: calcDoc.method,
        formula: calcDoc.formula,
        inputs: calcDoc.inputs_json ? JSON.parse(calcDoc.inputs_json) : undefined,
        result: calcDoc.result,
      }
    : null;

  return finding;
}

/** Confirm / dismiss / resolve a finding — the update permission Appwrite grants team members. */
export async function updateFindingStatus(
  findingId: string,
  status: FindingStatus,
  note?: string
): Promise<Finding> {
  const data: Record<string, unknown> = { status };
  if (note && status === "DISMISSED") data.dismissal_reason = note;
  if (note && status === "RESOLVED") data.resolution_notes = note;

  const doc = await databases.updateDocument(APPWRITE_DATABASE_ID, COLLECTIONS.leakFindings, findingId, data);
  return normalizeFinding(doc as unknown as Record<string, unknown>);
}
