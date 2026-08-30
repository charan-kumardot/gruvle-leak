import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { uploadDataset } from "@/lib/worker-api";

export async function POST(req: Request) {
  try {
    const jwt = extractJwt(req);
    const form = await req.formData();
    const businessId = String(form.get("business_id") ?? "");
    const teamId = String(form.get("team_id") ?? "");
    const file = form.get("file");

    if (!businessId || !teamId || !(file instanceof File)) {
      return NextResponse.json(
        { detail: "business_id, team_id, and file are all required." },
        { status: 400 }
      );
    }

    await requireTeamMembership(jwt, teamId);

    const result = await uploadDataset({ businessId, teamId, file, fileName: file.name });
    return NextResponse.json(result);
  } catch (err) {
    return errorResponse(err);
  }
}
