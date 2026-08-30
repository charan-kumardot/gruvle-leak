# Deployment

Target: free/low-cost infrastructure for the MVP, no paid infra mandatory to run it.

## Components

| Component | Where | Notes |
|---|---|---|
| `web/` (Next.js) | Vercel | Free tier is sufficient for the MVP. Set env vars from `web/.env.example`. |
| `worker/` (FastAPI) | Render (or any host that runs a long-lived Python process) | Vercel's serverless functions are a poor fit for pandas/PyMuPDF-heavy processing and background scan jobs — a persistent Python process is simpler and matches the `RENDER token` already available for this project. |
| Database + Auth + Storage | Appwrite Cloud (or self-hosted) | One project. See `worker/scripts/provision_appwrite.py` for schema setup. |
| AI | Gemini (primary), Groq / OpenRouter (fallback), deterministic heuristic (final fallback, zero cost) | All optional — the app runs with none configured. |
| Transactional email | Resend | Reserved for account/auth emails only; never used for automated customer-facing outreach (spec: actions require human approval). |

## Environment variables

Copy `worker/.env.example` -> `worker/.env` and `web/.env.example` -> `web/.env.local` and
fill in real values. Never commit the filled-in files (already git-ignored).

Required for the app to be more than demo-mode-only:
- `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, `APPWRITE_DATABASE_ID` (worker)
- `NEXT_PUBLIC_APPWRITE_ENDPOINT`, `NEXT_PUBLIC_APPWRITE_PROJECT_ID` (web)

Optional (the app degrades gracefully without them):
- `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` — without any of these, column
  mapping and finding explanations fall back to the deterministic `HeuristicAIProvider`
  (see `worker/app/ai/heuristic_provider.py`) at zero cost and zero external calls.
- `RESEND_API_KEY` — account emails only.

## Deploying the worker (Render)

1. New Web Service, point at this repo, root directory `worker/`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set all `worker/.env` variables as Render environment variables (do not upload the `.env`
   file itself).
5. After first deploy, run `python worker/scripts/provision_appwrite.py` once (locally, or
   as a one-off Render job) pointed at the same Appwrite project to create the database
   schema and storage buckets — it's idempotent, safe to re-run.

## Deploying the web app (Vercel)

1. Import the repo, set root directory to `web/`.
2. Framework preset: Next.js.
3. Set `web/.env.example` variables as Vercel project environment variables.
4. `WORKER_API_URL` must point at the deployed Render worker's public URL.

## Appwrite

Either Appwrite Cloud (fastest to start — this project uses `https://fra.cloud.appwrite.io/v1`)
or self-hosted Appwrite. Either way, the server API key needs `databases.read`,
`databases.write`, `storage.read`, `storage.write`, `teams.read`, `teams.write`, and
`users.read` scopes for `worker/scripts/provision_appwrite.py` and the repository layer to
function.

## What's NOT required to launch

Per product spec, none of the following are MVP dependencies: Stripe/Razorpay, Shopify,
QuickBooks/Zoho, Salesforce/HubSpot, or any bank connection. Billing is architected
(`plan` field on `businesses`) but no payment processor integration is wired in this pass.
