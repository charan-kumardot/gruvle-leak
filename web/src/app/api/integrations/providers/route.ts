import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/server/api-error";
import { listIntegrationProviders } from "@/lib/worker-api";

// Public list of what's supported and what's not — no team-membership check
// needed, this is just static product metadata, not business data.
export async function GET() {
  try {
    const providers = await listIntegrationProviders();
    return NextResponse.json({ providers });
  } catch (err) {
    return errorResponse(err);
  }
}
