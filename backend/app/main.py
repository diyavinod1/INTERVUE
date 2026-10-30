"""
Intervue backend entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import interviews, resume, voice
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import init_db

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up environment=%s database=%s", settings.environment, _redacted_db_url())
    try:
        init_db()
        logger.info("database_initialized_successfully")
    except Exception as e:
        logger.error("database_init_failed error=%s -- continuing startup", e)
    yield
    logger.info("shutting_down")



def _redacted_db_url() -> str:
    from app.db.database import db_url
    url = db_url
    if "@" in url:
        scheme_and_creds, host_part = url.rsplit("@", 1)
        scheme = scheme_and_creds.split("://")[0]
        return f"{scheme}://***:***@{host_part}"
    return url


app = FastAPI(
    title="Intervue API",
    description="Adaptive, conversational, voice-enabled AI interview platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# Parse frontend URLs: support comma-separated origins, strip trailing slashes
configured_origins = [o.strip().rstrip("/") for o in settings.frontend_url.split(",") if o.strip()]
if not configured_origins:
    configured_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


app.include_router(interviews.router)
app.include_router(resume.router)
app.include_router(voice.router)


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/config")
def public_config():
    """
    The ONLY endpoint that exposes configuration to the frontend, and it
    hand-picks strictly non-secret fields (PRD Sec. 38) - never API keys,
    never the Supabase service role key.
    """
    return {
        "max_resume_size_mb": settings.max_resume_size_mb,
        "min_questions": settings.min_questions,
        "max_questions": settings.max_questions,
        "voice_fallback_enabled": settings.enable_voice_fallback,
    }
