import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { disconnectIntegration } from "@/lib/worker-api";

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const teamId = new URL(req.url).searchParams.get("teamId");
    if (!teamId) {
      return NextResponse.json({ detail: "teamId query param is required." }, { status: 400 });
    }

    const jwt = extractJwt(req);
    await requireTeamMembership(jwt, teamId);

    await disconnectIntegration(id, teamId);
    return NextResponse.json({ deleted: true });
  } catch (err) {
    return errorResponse(err);
  }
}
