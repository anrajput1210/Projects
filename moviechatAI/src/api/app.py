from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from src.core.recommender import recommend_ai, upcoming

app = FastAPI(title="MovieChat API")


class AIRequest(BaseModel):
    text: str = Field(..., description="Natural language prompt")
    content_type: Optional[str] = Field(default=None, description="Optional override: movie|series")
    language: Optional[str] = Field(default=None, description="Optional override: en|hi|ko|ja etc")
    limit: int = Field(default=10, ge=1, le=30)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ai")
def ai(req: AIRequest):
    return recommend_ai(
        user_text=req.text,
        content_type=req.content_type,
        language=req.language,
        limit=req.limit,
    )


@app.get("/upcoming")
def get_upcoming(limit: int = 10):
    return upcoming(limit)
