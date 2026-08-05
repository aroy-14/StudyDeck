"""
StudyDeck v1 — FastAPI application entry point.
"""

import os
import data.db  # loads .env into os.environ on startup  # noqa: F401
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Routers (stubs until implemented in later tasks)
from routers import auth, decks, cards, study, ai
from services.ai_service import AIServiceError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS: int = 7

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="StudyDeck API",
    description="Backend API for the StudyDeck collaborative study platform.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in development
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "AI service unavailable. Please try again."},
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(decks.router, prefix="/decks", tags=["decks"])
app.include_router(cards.router, tags=["cards"])
app.include_router(study.router, prefix="/study", tags=["study"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
