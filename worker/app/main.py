from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gruvle")

settings = get_settings()

app = FastAPI(
    title="Gruvle Leak Worker API",
    description="File processing, data profiling, leak detection, and report generation for Gruvle Leak.",
    version="0.1.0",
)

# Authenticated routes (/datasets, /scans, /findings) are called only by the
# Next.js server, never a browser — but /demo/* is deliberately public (no
# token, synthetic data only) so the marketing page's live demo can call it
# straight from the browser. CORS is scoped to CORS_ALLOWED_ORIGINS (the
# deployed web app's origin(s) in production) either way.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def human_readable_error_handler(request: Request, exc: Exception):
    """
    Spec section 67: errors must be human-readable, never a bare "Internal
    server error." Known, expected failure modes (bad upload, unmappable
    data) should raise a specific HTTPException with a clear detail message
    well before reaching here — this handler is the last-resort net for
    anything unexpected, and still avoids leaking a raw stack trace to the
    client while logging the full exception server-side for debugging.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Something went wrong while processing this request. This has been logged — "
                "please try again, and if it keeps happening, the data in this request may need review."
            )
        },
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "appwrite_configured": settings.appwrite_configured,
        "ai_provider_configured": settings.any_ai_provider_configured,
    }


# Routers are registered here as each API module lands.
from app.api.account import router as account_router  # noqa: E402
from app.api.datasets import router as datasets_router  # noqa: E402
from app.api.demo import router as demo_router  # noqa: E402
from app.api.integrations import router as integrations_router  # noqa: E402
from app.api.scans import finding_router, router as scans_router  # noqa: E402

app.include_router(demo_router, prefix="/demo", tags=["demo"])
app.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
app.include_router(scans_router, prefix="/scans", tags=["scans"])
app.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
app.include_router(finding_router, prefix="/findings", tags=["findings"])
app.include_router(account_router, prefix="/account", tags=["account"])
