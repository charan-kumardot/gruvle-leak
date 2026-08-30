import { NextResponse } from "next/server";
import { extractJwt, requireOwnUserId, requireTeamMembership } from "@/lib/server/auth";
import { errorResponse } from "@/lib/server/api-error";
import { deleteAccountAndBusiness } from "@/lib/worker-api";

interface DeleteBody {
  businessId: string;
  teamId: string;
}

/**
 * Irreversible: deletes the business's data, its Team, and the caller's own
 * Appwrite account. `userId` is deliberately NOT read from the request body
 * — it's resolved from the caller's own JWT (`requireOwnUserId`), so this
 * route can only ever delete the account making the request, never anyone
 * else's, even if the body is tampered with.
 */
export async function POST(req: Request) {
  try {
    const jwt = extractJwt(req);
    const body = (await req.json()) as DeleteBody;
    if (!body.businessId || !body.teamId) {
      return NextResponse.json({ detail: "businessId and teamId are required." }, { status: 400 });
    }

    await requireTeamMembership(jwt, body.teamId);
    const userId = await requireOwnUserId(jwt);

    await deleteAccountAndBusiness(body.businessId, body.teamId, userId);
    return NextResponse.json({ deleted: true });
  } catch (err) {
    return errorResponse(err);
  }
}
