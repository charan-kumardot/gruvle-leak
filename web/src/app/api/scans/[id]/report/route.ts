import { NextResponse } from "next/server";
import { extractJwt, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { getReport } from "@/lib/worker-api";
import type { ReportFormat } from "@/lib/types";

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const url = new URL(req.url);
    const teamId = url.searchParams.get("teamId");
    const format = (url.searchParams.get("format") ?? "pdf") as ReportFormat;
    if (!teamId) {
      return NextResponse.json({ detail: "teamId query param is required." }, { status: 400 });
    }

    const jwt = extractJwt(req);
    await requireTeamMembership(jwt, teamId);

    const file = await getReport(id, teamId, format);
    return new NextResponse(file.body, {
      headers: {
        "Content-Type": file.contentType,
        "Content-Disposition": `attachment; filename="${file.filename}"`,
      },
    });
  } catch (err) {
    return errorResponse(err);
  }
}
