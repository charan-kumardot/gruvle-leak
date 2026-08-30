import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { syncIntegration } from "@/lib/worker-api";

interface SyncBody {
  businessId: string;
  teamId: string;
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = (await req.json()) as SyncBody;
    if (!body.businessId || !body.teamId) {
      return NextResponse.json({ detail: "businessId and teamId are required." }, { status: 400 });
    }

    const jwt = extractJwt(req);
    await requireTeamMembership(jwt, body.teamId);

    const result = await syncIntegration(id, body.businessId, body.teamId);
    return NextResponse.json(result);
  } catch (err) {
    return errorResponse(err);
  }
}
