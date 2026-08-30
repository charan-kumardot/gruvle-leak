import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { connectIntegration, listIntegrationConnections } from "@/lib/worker-api";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const businessId = url.searchParams.get("businessId");
    const teamId = url.searchParams.get("teamId");
    if (!businessId || !teamId) {
      return NextResponse.json({ detail: "businessId and teamId query params are required." }, { status: 400 });
    }

    const jwt = extractJwt(req);
    await requireTeamMembership(jwt, teamId);

    const connections = await listIntegrationConnections(businessId, teamId);
    return NextResponse.json({ connections });
  } catch (err) {
    return errorResponse(err);
  }
}

interface ConnectBody {
  businessId: string;
  teamId: string;
  userId: string;
  provider: string;
  credentials: Record<string, string>;
}

export async function POST(req: Request) {
  try {
    const jwt = extractJwt(req);
    const body = (await req.json()) as ConnectBody;

    if (!body.businessId || !body.teamId || !body.provider || !body.credentials) {
      return NextResponse.json(
        { detail: "businessId, teamId, provider, and credentials are all required." },
        { status: 400 }
      );
    }

    await requireTeamMembership(jwt, body.teamId);

    const connection = await connectIntegration(body);
    return NextResponse.json(connection);
  } catch (err) {
    return errorResponse(err);
  }
}
