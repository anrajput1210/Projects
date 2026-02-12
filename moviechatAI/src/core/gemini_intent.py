import json
import os
from typing import Any, Dict, Optional

# You said you already have Gemini code; this uses the common google-genai client.
# pip install google-genai
from google import genai


INTENT_JSON_SPEC = {
    "type": "object",
    "properties": {
        "content_type": {"type": "string", "enum": ["movie", "series", "unknown"]},
        "title_query": {"type": ["string", "null"]},
        "person_name": {"type": ["string", "null"]},
        "person_role": {"type": ["string", "null"], "enum": ["actor", "director", "writer", None]},
        "genres": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "year_from": {"type": ["integer", "null"]},
        "year_to": {"type": ["integer", "null"]},
    },
    "required": ["content_type", "title_query", "person_name", "person_role", "genres", "keywords", "year_from", "year_to"],
    "additionalProperties": False,
}


def gemini_parse_intent(user_text: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)

    system = (
        "You are an intent parser for a movie/TV recommender.\n"
        "Extract structured filters.\n"
        "Rules:\n"
        "- If user mentions a specific title (e.g., Game of Thrones), set title_query.\n"
        "- If user asks for actor/director movies (e.g., 'tom cruise movies', 'nolan films'), set person_name and person_role.\n"
        "- If user says series/tv/show -> content_type='series'. movie/film -> 'movie'. else 'unknown'.\n"
        "- Years: 'after 2015' => year_from=2016. 'since 2015' => 2015. 'before 2015' => year_to=2014.\n"
        "- genres: words like comedy, crime, thriller, adventure, animation.\n"
        "- keywords: thematic terms like heist, revenge, courtroom, whodunit.\n"
        "Return ONLY valid JSON matching the schema."
    )

    prompt = f"{system}\n\nUSER: {user_text}\nJSON:"

    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
        },
    )

    try:
        data = json.loads(resp.text)
        return data
    except Exception:
        return None
