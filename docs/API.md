# Worker API

Base URL (local dev): `http://localhost:8000`. Called only by the Next.js server side
(`web/src/lib/worker-api.ts`, from `/api/*` route handlers), never directly from a
browser — see `docs/ARCHITECTURE.md` for the JWT-based check those route handlers perform
before forwarding anything here, and for why most reads (scans, findings) bypass this API
entirely and go straight to Appwrite from the client instead.

All authenticated routes below require an `X-Internal-Token` header matching
`WORKER_API_INTERNAL_TOKEN` (see `worker/.env.example`) — this proves the request came
from the Next.js server, not that the specific end user has access to the business/team_id
in the request; that check happens one layer up, in `web/src/lib/server/auth.ts`.

## Implemented and verified end-to-end (live, over real HTTP, against the live Appwrite project)

### `POST /datasets/upload`

Multipart form: `file`, `business_id`, `team_id`. Validates the file (magic bytes, size),
parses it (CSV/XLSX/JSON — a PDF with no detectable table is rejected with a clear
message), profiles it, gets an AI-assisted column mapping (with heuristic fallback),
stores the original file in the shared private Appwrite bucket, and persists `datasets` +
`dataset_columns` + `data_mappings` documents scoped to the business's Team. Returns the
dataset id, inferred kind, row/column counts, the full column mapping with per-column
confidence and reasoning, and a data quality score.

### `POST /scans`

JSON body: `{business_id, team_id, created_by_user_id, dataset_ids: string[], currency}`.
Re-downloads and re-parses each dataset's stored file, applies its persisted mapping,
builds a `DetectionContext`, runs every registered detector (failures in one detector
never take down the others), scores all findings together, persists `leak_findings` +
`leak_evidence` + `leak_calculations`, updates the `scans` document's totals/stage, and
returns the full `ReportSummary` (same shape `/demo/scan` returns).

### `GET /scans/:id/report?format={json|csv|markdown|pdf}`

Rebuilds the `ReportSummary` from persisted findings and renders it. Same exporters
`/demo/scan/report` uses — every format renders the identical underlying data.

### Also implemented, not currently called by the web app

`GET /scans/:id`, `GET /scans/:id/findings`, `GET /findings/:id`, and
`POST /findings/:id/status` (see `worker/app/api/scans.py`) all work and are covered by
`worker/tests/test_scan_pipeline_live.py`, but the web app reads and updates this same
data straight from Appwrite instead (see `web/src/lib/scans-client.ts`) — those documents
are already team-permissioned, so going through the worker would just add a hop. These
stay available for any future consumer (a CLI, a mobile client, a partner integration)
that doesn't hold an Appwrite session but does have the internal token.

## Demo mode

### `GET /health`

```json
{ "status": "ok", "environment": "development", "appwrite_configured": true, "ai_provider_configured": true }
```

### `GET /demo/scan`

Runs the real detector engine against the synthetic "Demo Retail Co." dataset
(`worker/app/demo/demo_data.py`) and returns a full `ReportSummary` (see
`worker/app/reports/schemas.py`): findings, evidence, calculations, impact totals,
priority-ranked top findings, data limitations. Every number in the response comes from
actually running `worker/app/detectors/` against the synthetic data — nothing here is
hand-typed JSON. Always set `is_demo: true`; the frontend must label any screen showing
this data as **DEMO DATA** and never blend it with a real scan.

### `GET /demo/scan/report?format={json|csv|markdown|pdf}`

Same underlying data as `/demo/scan`, rendered to the requested export format.

## Planned (not yet built)

```
POST   /findings/:id/feedback     body: { verdict, reason? } -> false-positive feedback capture
                                   (the `finding_feedback` collection exists in schema.py;
                                   nothing writes to it yet)
DELETE /datasets/:id              soft-delete a dataset and its derived data
```

## Error format

Every error response is `{"detail": "<human-readable message>"}` — never a bare stack
trace or a generic "Internal server error" (spec section 67). See
`app/main.py:human_readable_error_handler` for the last-resort fallback and individual
route handlers for specific, actionable messages (e.g. "Invoices dataset has no order_id
field mapped, so orders cannot be reliably matched to invoices.").
