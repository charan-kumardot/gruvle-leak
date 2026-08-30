import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { createScan } from "@/lib/worker-api";

interface CreateScanBody {
  businessId: string;
  teamId: string;
  createdByUserId: string;
  datasetIds: string[];
  currency?: string;
}

export async function POST(req: Request) {
  try {
    const jwt = extractJwt(req);
    const body = (await req.json()) as CreateScanBody;

    if (!body.businessId || !body.teamId || !body.datasetIds?.length) {
      return NextResponse.json(
        { detail: "businessId, teamId, and at least one datasetId are required." },
        { status: 400 }
      );
    }

    await requireTeamMembership(jwt, body.teamId);

    const summary = await createScan({
      businessId: body.businessId,
      teamId: body.teamId,
      createdByUserId: body.createdByUserId,
      datasetIds: body.datasetIds,
      currency: body.currency,
    });
    return NextResponse.json(summary);
  } catch (err) {
    return errorResponse(err);
  }
}
