import "server-only";

import { NextResponse } from "next/server";
import { UnauthorizedError } from "@/lib/server/auth";
import { WorkerApiError } from "@/lib/worker-api";

/** Consistent, human-readable error shape for every /api route handler in this app. */
export function errorResponse(err: unknown) {
  if (err instanceof UnauthorizedError) {
    return NextResponse.json({ detail: err.message }, { status: 401 });
  }
  if (err instanceof WorkerApiError) {
    return NextResponse.json({ detail: err.message }, { status: err.status ?? 502 });
  }
  return NextResponse.json(
    { detail: err instanceof Error ? err.message : "Something went wrong." },
    { status: 500 }
  );
}
