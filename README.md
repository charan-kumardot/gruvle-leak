# Gruvle Leak

**Find the money your business is losing without realizing it.**

Gruvle Leak is an AI-assisted revenue-leakage investigator for SMBs and mid-market
businesses. Upload the business data you already have — CSV, Excel, PDF invoices/contracts,
JSON — and Gruvle deterministically detects unbilled work, pricing inconsistencies, invoice
mismatches, at-risk renewals, and excess discounting, backed by inspectable evidence and a
transparent calculation for every dollar figure it shows you. No bank, ERP, or CRM
connection required.

Gruvle never claims certainty the data doesn't support. Findings are phrased as
**potential leakage**, **at-risk revenue**, or **revenue opportunity** — never as money
definitely lost — and every finding links back to the exact records and arithmetic behind it.

## Repository layout

```
web/      Next.js (App Router, TypeScript, Tailwind) — landing page, auth, dashboard,
          upload UI, leaks/reports/actions screens. Talks to Appwrite directly (client
          SDK, per-user sessions) and to worker/ over HTTP for anything data-heavy.
worker/   Python FastAPI service — file parsing (CSV/XLSX/JSON/PDF), data profiling,
          AI-assisted column mapping, the ten leak detectors, deterministic priority
          scoring, and report generation (PDF/CSV/JSON/Markdown). Holds the privileged
          Appwrite API key; the only backend allowed to write findings.
docs/     SETUP.md, ARCHITECTURE.md, SECURITY.md, DATA_MODEL.md, API.md, DEPLOYMENT.md
scripts/  One-off / operational scripts (Appwrite provisioning lives in worker/scripts/).
```

## Why two services instead of one

Detection needs pandas/openpyxl/PyMuPDF-grade data tooling and must produce numbers a
CFO can trust; that logic lives in Python, tested independently of any AI call (see
`worker/tests/`). The web app is a thin, fast Next.js frontend that never performs a
financial calculation itself — it only ever displays what the worker computed.

## Quickstart (local development)

See [docs/SETUP.md](docs/SETUP.md) for full instructions. Short version:

```bash
# Worker (Python)
cd worker
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env   # fill in Appwrite + AI provider keys, or leave blank for demo mode
uvicorn app.main:app --reload --port 8000

# Web (Next.js) — in a second terminal
cd web
npm install
cp .env.example .env.local
npm run dev
```

Visit `http://localhost:3000`. With no API keys configured at all, the worker still runs
end-to-end against a synthetic, clearly-labeled **DEMO DATA** business — try
`GET http://localhost:8000/demo/scan`.

## Product principle

See the full spec this repo implements against for the complete list of detectors,
screens, and hard rules — the two that matter most:

1. **Never fabricate a financial claim.** Every number a detector produces traces back to
   specific rows in the data you uploaded, via a `Calculation` object with a plain-language
   formula, and every finding lists what evidence it does and doesn't have.
2. **AI never does arithmetic.** Detection is 100% deterministic Python (`worker/app/detectors/`,
   `worker/app/scoring/`). AI (Gemini, with Groq/OpenRouter/heuristic fallback — see
   `worker/app/ai/`) is used only to suggest column mappings and phrase explanations around
   numbers that were already computed.

## Status

This is an active build. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what's real
today vs. planned, and each module's own docstring for what it deliberately leaves out.
