# Data Model

Source of truth: [`worker/app/db/schema.py`](../worker/app/db/schema.py) (Appwrite
collections, applied by `worker/scripts/provision_appwrite.py`) and
[`worker/app/schemas/domain.py`](../worker/app/schemas/domain.py) (the in-process Python
domain model detectors/reports actually operate on — collections mirror this shape onto
Appwrite for persistence, but detection logic never touches Appwrite directly).

## Multi-tenancy

There is no SQL row-level security in Appwrite, so isolation is modeled with **one
Appwrite Team per business**. Every business-scoped collection carries both:

- `business_id` — the owning `businesses` document's ID (the stable foreign key other
  records join on).
- `team_id` — the Appwrite Team ID backing that business (what Appwrite permissions and
  the repository layer's isolation checks key off of).

Every document in every business-scoped collection is created with Appwrite permissions
scoped to `team:<team_id>` only, never `any` or `users` — see `worker/app/db/repositories.py`
and `worker/tests/test_multi_tenancy.py`.

## Collections

| Collection | Purpose |
|---|---|
| `businesses` | One per tenant. Owner, Team ID, name, industry, currency, plan. |
| `datasets` | One per uploaded file. Kind (orders/invoices/contracts/…), storage pointer, processing status. |
| `dataset_columns` | Per-column profile (inferred type, null/distinct counts) from `app/profiling`. |
| `data_mappings` | Raw column name -> canonical field, with confidence/source/reason. |
| `scans` | One per analysis run. Stage/progress, totals, currency, `is_demo` flag. |
| `leak_findings` | One per detected leak. Category, impact type/amount, confidence, priority score, status. |
| `leak_evidence` | Row-level evidence backing a finding (dataset + row index + display fields). |
| `leak_calculations` | The transparent arithmetic trail (method, formula, inputs, result) behind a finding's amount. |
| `recommended_actions` | Draft next steps per finding; always requires human approval before anything external happens. |
| `reports` | Generated exports (PDF/CSV/JSON/Markdown) per scan. |
| `audit_logs` | Who did what to which object, with before/after state. |
| `usage_events` | Product analytics events (signup, scan_started, etc.) — no raw financial content logged. |
| `finding_feedback` | User verdicts (confirmed / false positive / resolved) for future detector tuning — never auto-retrains anything in this pass. |

## Storage buckets

| Bucket | Purpose |
|---|---|
| `raw_uploads` | Original uploaded files. Private (`file_security: true`), max 100MB. |
| `generated_reports` | Exported report files. Private, max 25MB. |

Neither bucket grants public read — every file access goes through an authenticated
Appwrite session or the worker's server key, never a bare public URL.

## Canonical field vocabulary

Detectors never read raw spreadsheet headers. Every dataset is mapped onto a fixed set of
canonical fields (`CanonicalField` enum in `domain.py`) — `customer_id`, `order_id`,
`invoice_id`, `total_amount`, `unit_price`, `discount_percent`, `contract_end_date`, etc.
— before any detection logic runs. This is what lets ten independent detectors share one
mapping step instead of each parsing headers themselves.

## Financial impact types

`ImpactType` in `domain.py` is deliberately not a single number:

- `POTENTIAL_LEAKAGE` — money likely already earned but not captured (unbilled work,
  invoice undercharges, excess discounts).
- `AT_RISK_REVENUE` — recurring revenue that may churn (renewals expiring/expired).
- `REVENUE_OPPORTUNITY` — money not yet earned but capturable going forward (underpriced
  products).
- `CAPITAL_TIED_UP` — non-revenue capital exposure (future: dead inventory).

`app/scoring/priority.py::total_impact_by_type` sums strictly within each type — these
numbers are never added together into one headline figure, in code or in any report.
