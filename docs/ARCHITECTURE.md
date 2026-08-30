# Architecture

```
                         ┌────────────────────────┐
   Browser  ───────────► │  web/  (Next.js)        │
                         │  - landing, auth, UI    │
                         │  - Appwrite Web SDK      │──── per-user session ────┐
                         └───────────┬─────────────┘                          │
                                     │ HTTP (server-side only,                │
                                     │ WORKER_API_URL)                        ▼
                         ┌───────────▼─────────────┐               ┌──────────────────┐
                         │  worker/  (FastAPI)      │──────────────►│  Appwrite         │
                         │  - parse / profile /map  │  server API   │  - Auth (Teams)   │
                         │  - 10 leak detectors     │  key          │  - Database        │
                         │  - priority scoring      │               │  - Storage         │
                         │  - report generation     │               └──────────────────┘
                         └───────────┬─────────────┘
                                     │ (schema-validated, fallback-chained)
                                     ▼
                         ┌──────────────────────────┐
                         │  AI provider router       │
                         │  Gemini → Groq →           │
                         │  OpenRouter → Heuristic    │
                         └──────────────────────────┘
```

## Why this split

- **Detection must be trustworthy.** A CFO-facing tool that says "you're losing ₹X" has to
  be able to show its work and reproduce the number every time. That rules out doing
  arithmetic inside an LLM call. All ten detectors (`worker/app/detectors/`) are plain,
  synchronous, dependency-free Python functions operating on `Decimal`, unit-tested with
  hand-computed expected values (`worker/tests/detectors/`, see especially the spec-section-78
  canonical case in `test_invoice_mismatch.py`).
- **AI is scoped tightly.** `worker/app/ai/` is used for exactly two things: suggesting
  which raw column maps to which canonical field, and phrasing an explanation around a
  number a detector already computed. Every AI response is validated against a Pydantic
  schema (`app/ai/base.py`) before use; a malformed response, a timeout, or no API key at
  all all fall through to the next provider, ending at a zero-cost deterministic heuristic
  (`app/ai/heuristic_provider.py`) that never calls out to the network. The app is fully
  functional with zero AI keys configured.
- **The web app never computes a finding.** It renders whatever the worker returns. This
  keeps the trust boundary for "is this number right" in one place.

## Request flow (once upload -> scan is fully wired)

1. User uploads a file in `web/`. The file goes to the worker (`POST /datasets/upload`,
   planned), which validates it by magic bytes (never trusts the extension), stores the
   original in a private Appwrite Storage bucket, and creates a `datasets` document scoped
   to the business's Team.
2. Worker parses the file (`app/parsers/`), profiles it (`app/profiling/`), and proposes a
   column mapping (`app/mapping/`, calling the AI router with heuristic fallback).
3. Once mapping is confirmed (auto-accepted if confident, or edited by the user), rows are
   normalized into `NormalizedRecord`s keyed by canonical field (`app/mapping/normalize.py`).
4. A `DetectionContext` bundles normalized records by dataset kind (orders/invoices/
   contracts/…) and every registered detector (`app/detectors/registry.py`) runs against it
   independently — one detector raising an exception never takes down the others
   (`run_all_detectors` catches and reports `DetectorStatus.FAILED` per-detector).
5. All findings across the whole scan are scored together
   (`app/scoring/priority.py::score_detector_results` — deterministic, no AI) and
   assembled into a `ReportSummary` (`app/reports/builder.py`).
6. The web app renders findings, evidence, and calculations from that summary, and can
   request PDF/CSV/JSON/Markdown exports (`app/reports/exporters.py`) — all four render the
   exact same `ReportSummary`, so they can never disagree with each other.

## Multi-tenancy

One Appwrite Team per business. Every business-scoped document carries `team_id` and is
created with permissions scoped to `team:<team_id>` only. See `docs/DATA_MODEL.md` and
`docs/SECURITY.md`.

## What's real vs. planned right now

**Built, tested, and verified live end-to-end:** domain schema; AI provider abstraction +
router + heuristic/Gemini/Groq/OpenRouter implementations; storage abstraction (local disk
+ Appwrite); all 5 implemented detectors + 5 registered stubs; deterministic priority
scoring; report builder + 4 exporters; a live FastAPI service; Appwrite schema +
provisioning script (14 collections, 1 storage bucket, all live in the project); full
multi-tenant isolation (one Appwrite Team per business, verified by both an automated
integration test and a manual cross-tenant attack simulation — see
`worker/tests/test_multi_tenancy.py`); and the complete
`upload -> parse -> profile -> map -> scan -> detect -> score -> persist -> findings ->
report` flow, wired all the way through: Next.js upload UI -> `/api/datasets` and
`/api/scans` route handlers (which verify the caller's Appwrite JWT actually belongs to
the claimed business's Team before forwarding anything) -> the Python worker -> Appwrite
-> back to the Leaks list, finding detail (with evidence table + calculation), Overview
dashboard stats, and Reports page (PDF/CSV/Markdown/JSON export via a real browser
download). Verified with a real signed-up user, a real session, a real JWT, and a real
CSV upload over HTTP — see `worker/tests/test_scan_pipeline_live.py` for the automated
version of this same path.

Reads of already-computed data (scan list, finding list, finding detail, confirm/dismiss/
resolve) go straight from the browser to Appwrite via the Web SDK, not through the worker
— those documents are already team-permissioned in Appwrite (`Permission.read/update(Role.team(team_id))`,
applied by `worker/app/db/repositories.py` at write time), so re-proxying them through a
Route Handler would just reimplement access control Appwrite already enforces. Only the
three operations that need the Python worker's own logic — parsing/profiling/mapping a
file, running detection, and rendering a report export — go through `/api/*` (see
`web/src/lib/worker-api.ts`'s header comment).

**Planned, not yet built:** a background job queue for large files (today, upload and scan
both run synchronously within the HTTP request — fine at the 10MB/small-business scale
this MVP targets, per spec, but a real queue is the honest next step for bigger files);
admin dashboard; billing/payment integration; the remaining 5 detectors (Inventory,
Refund, Customer, Contract, Operations); full PDF-contract-to-structured-data extraction
(a PDF with no detectable table is currently rejected with a clear message at upload time
rather than silently dropped — see `worker/app/jobs/scan_pipeline.py`).
