# Security

## Reporting

This is a pre-launch internal build; there is no public bug bounty yet. If you find a
vulnerability, contact the project owner directly rather than filing a public issue.

## Secrets

- All API keys (Appwrite, Gemini, Groq, OpenRouter, Resend) live only in `worker/.env`
  and `web/.env.local`, both git-ignored from the first commit in this repo (`.gitignore`
  excludes `**/.env` and `**/.env.local`, but explicitly allows `.env.example` files).
- The Appwrite **server API key** exists only in `worker/.env` and is used only by the
  Python worker (`worker/app/db/client.py`). The Next.js web app never holds it — it
  authenticates end users with the Appwrite **Web SDK** using per-user sessions, so a
  compromised web deployment cannot leak the privileged key.
- Never commit a filled-in `.env`/`.env.local`. Never log secret values — `worker/app/core/config.py`
  is the only place they're read into memory, and nothing downstream should print `Settings`.

## Multi-tenancy / IDOR

Every business is its own Appwrite **Team**. Every business-owned document (datasets,
scans, findings, reports, etc.) is created with permissions scoped to `team:<businessId>`
only — never `Role.any()` or `Role.users()`. See `worker/app/db/repositories.py` and
`worker/tests/test_multi_tenancy.py` for the enforcement and its test coverage: a user in
Business A must never be able to read, list, or mutate a document belonging to Business B,
whether by guessing an ID (`/scans/{id}`) or by any list endpoint.

## Upload validation

Files are never trusted by extension alone. `worker/app/parsers/validation.py` checks the
actual file signature (magic bytes) against the claimed extension/MIME type before any
parser touches the content, and enforces a maximum size. Untrusted file content (CSV/JSON
values, PDF-extracted text) is never `eval`'d, never used to build file paths, and never
treated as instructions — see the AI prompt-injection note below.

## Prompt injection

Uploaded documents are adversarial input by default. Every AI provider prompt
(`worker/app/ai/gemini_provider.py`, `worker/app/ai/openai_compatible_provider.py`)
explicitly instructs the model to treat all supplied data as content to analyze, never as
instructions to follow, and every AI response is validated against a strict Pydantic
schema before use (`app/ai/base.py: validate_or_raise`) — malformed or off-schema output is
discarded and the caller falls back to the next provider, ultimately to a zero-AI
deterministic heuristic, rather than trusting raw model text anywhere a financial figure,
a query, or a permission decision is made.

## File privacy

Uploaded originals and generated reports are stored in private Appwrite Storage buckets
(`file_security: true`, no public read permission) or, in local/demo dev without Appwrite
configured, on local disk under a path never served by any public route. Nothing uploaded
by a user is ever publicly reachable by a bare URL.

## What's intentionally NOT automated

Per product spec, Gruvle never sends a customer-facing email, creates an invoice, or
changes a price on its own. Every `recommended_actions` record requires explicit human
approval before anything leaves the app (spec sections 38–40, 92–94). This is a product
decision as much as a security one: it bounds the blast radius of any bug or prompt
injection to "a bad draft," never to "an unauthorized external action."
