import logging
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from src.core.recommender import recommend_ai

logger = logging.getLogger("moviechat")

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="MovieChat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Whitelisted so an arbitrary string can never reach TMDB's sort_by param.
SortBy = Literal[
    "vote_average.desc",
    "vote_average.asc",
    "primary_release_date.desc",
    "primary_release_date.asc",
    "popularity.desc",
    "revenue.desc",
]


class AIRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language prompt")
    content_type: Optional[str] = Field(default=None, description="Optional override: movie|series")
    language: Optional[str] = Field(default=None, description="Optional override: en|hi|ko|ja etc")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)
    sort_by: Optional[SortBy] = Field(
        default=None,
        description="Explicit sort; overrides any sort inferred from the text",
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ai")
def ai(req: AIRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be blank")

    try:
        return recommend_ai(
            user_text=req.text,
            content_type=req.content_type,
            language=req.language,
            page=req.page,
            page_size=req.page_size,
            sort_by=req.sort_by,
        )
    except RuntimeError as e:
        # Missing/misconfigured API key (see src/core/providers.py)
        logger.error("Configuration error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("recommend_ai failed for text=%r", req.text)
        raise HTTPException(status_code=502, detail="Upstream movie data provider failed. Please try again.")


# Mounted last so the API routes above always take precedence over the
# static file server. html=True serves web/index.html at "/".
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
else:  # pragma: no cover - only when the frontend is absent
    logger.warning("web/ directory not found at %s; serving API only", WEB_DIR)
