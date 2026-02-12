import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from .ai_intent import parse_intent
from .providers import (
    tmdb_discover_movie,
    tmdb_discover_tv,
    tmdb_search_movie,
    tmdb_search_tv,
    tmdb_similar,
    tmdb_get_trailer_url,
    tmdb_poster_url,
    tmdb_backdrop_url,
    watchmode_search,
    watchmode_sources,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "US")

AVAILABILITY_LOOKUPS_PER_REQUEST = 5
TRAILER_LOOKUPS_PER_REQUEST = 4
WATCHMODE_SLEEP_BETWEEN_CALLS = 0.10

_WATCHMODE_ID_CACHE: Dict[str, Optional[int]] = {}
_WATCHMODE_SOURCES_CACHE: Dict[Tuple[str, str], List[Dict]] = {}
_TRAILER_CACHE: Dict[Tuple[int, str], Optional[str]] = {}


def _normalize_content_type(ct: str) -> str:
    ct = (ct or "").strip().lower()
    if ct in ("movie", "movies"):
        return "movie"
    if ct in ("series", "tv", "show", "shows"):
        return "series"
    return ct or "movie"


def _rating(item: Dict) -> float:
    try:
        return float(item.get("vote_average") or 0.0)
    except Exception:
        return 0.0


def _popularity(item: Dict) -> float:
    try:
        return float(item.get("popularity") or 0.0)
    except Exception:
        return 0.0


def _best_watchmode_id(title: str) -> Optional[int]:
    if title in _WATCHMODE_ID_CACHE:
        return _WATCHMODE_ID_CACHE[title]
    try:
        data = watchmode_search(title)
        results = data.get("title_results", [])
        wm_id = results[0].get("id") if results else None
        _WATCHMODE_ID_CACHE[title] = wm_id
        return wm_id
    except Exception:
        _WATCHMODE_ID_CACHE[title] = None
        return None


def _watchmode_sources_cached(title: str, region: str) -> List[Dict]:
    key = (title, region)
    if key in _WATCHMODE_SOURCES_CACHE:
        return _WATCHMODE_SOURCES_CACHE[key]

    wm_id = _best_watchmode_id(title)
    if wm_id is None:
        _WATCHMODE_SOURCES_CACHE[key] = []
        return []

    try:
        sources = watchmode_sources(wm_id, region=region)
    except Exception:
        sources = []

    _WATCHMODE_SOURCES_CACHE[key] = sources
    return sources


def _availability_text(title: str, region: str) -> str:
    sources = _watchmode_sources_cached(title, region)
    names = []
    for s in sources:
        nm = s.get("name") or s.get("source")
        if nm:
            names.append(nm)
    names = list(dict.fromkeys(names))[:6]
    return ", ".join(names)


def _trailer_cached(tmdb_id: int, media_type: str) -> Optional[str]:
    key = (tmdb_id, media_type)
    if key in _TRAILER_CACHE:
        return _TRAILER_CACHE[key]
    try:
        url = tmdb_get_trailer_url(tmdb_id, media_type)
    except Exception:
        url = None
    _TRAILER_CACHE[key] = url
    return url


def _score_100(item: Dict, intent_genres: List[int], intent_lang: Optional[str], similar_bonus: float = 0.0) -> int:
    rating = _rating(item)  # 0..10
    pop = _popularity(item)  # 0..big

    item_genres = item.get("genre_ids") or []
    if intent_genres:
        overlap = len(set(item_genres).intersection(set(intent_genres))) / max(len(set(intent_genres)), 1)
    else:
        overlap = 0.35

    lang_match = 1.0 if (intent_lang and item.get("original_language") == intent_lang) else 0.0
    pop_norm = min(pop / 200.0, 1.0)

    base = (
        0.50 * (rating / 10.0) +
        0.25 * overlap +
        0.20 * pop_norm +
        0.05 * lang_match
    )

    base = min(base + similar_bonus, 1.0)
    return int(round(base * 100))


def recommend_ai(
    user_text: str,
    content_type: Optional[str] = None,
    language: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict:
    """
    Returns:
      { "items": [...], "page": page, "page_size": page_size, "intent": {...} }
    """
    intent = parse_intent(user_text)

    ct = _normalize_content_type(content_type or intent.content_type or "movie")
    lang = (language or intent.language or None)

    # year filters from intent
    year_from = intent.year_from
    year_to = intent.year_to

    # This page maps to TMDB page (simple + predictable)
    tmdb_page = max(int(page), 1)

    genre_ids = intent.genres or []

    # candidates from discover
    if ct == "movie":
        candidates = tmdb_discover_movie(
            genres=genre_ids or None,
            page=tmdb_page,
            language=lang,
            year_from=year_from,
            year_to=year_to,
        ).get("results", [])
        media_type = "movie"
    else:
        candidates = tmdb_discover_tv(
            genres=genre_ids or None,
            page=tmdb_page,
            language=lang,
            year_from=year_from,
            year_to=year_to,
        ).get("results", [])
        media_type = "tv"

    # fallback search if discover page empty
    if not candidates and user_text.strip():
        if ct == "movie":
            candidates = tmdb_search_movie(user_text.strip(), page=tmdb_page).get("results", [])
        else:
            candidates = tmdb_search_tv(user_text.strip(), page=tmdb_page).get("results", [])
        if lang:
            candidates = [c for c in candidates if c.get("original_language") == lang]

    # Similar expansion (only affects scoring + diversity)
    similar_ids = set()
    if intent.seed_title:
        if ct == "movie":
            seed_results = tmdb_search_movie(intent.seed_title, page=1).get("results", [])
            seed_id = seed_results[0].get("id") if seed_results else None
        else:
            seed_results = tmdb_search_tv(intent.seed_title, page=1).get("results", [])
            seed_id = seed_results[0].get("id") if seed_results else None

        if seed_id:
            sim = tmdb_similar(seed_id, media_type, page=tmdb_page).get("results", [])
            for s in sim:
                if s.get("id"):
                    similar_ids.add(s["id"])
            # merge similar first
            merged = []
            seen = set()
            for x in sim + candidates:
                if not x.get("id") or x["id"] in seen:
                    continue
                seen.add(x["id"])
                merged.append(x)
            candidates = merged

    # Build page results
    items: List[Dict] = []
    trailer_calls = 0
    avail_calls = 0

    for c in candidates:
        tmdb_id = c.get("id")
        if not tmdb_id:
            continue

        title = c.get("title") if ct == "movie" else c.get("name")
        if not title:
            continue

        trailer = None
        if trailer_calls < TRAILER_LOOKUPS_PER_REQUEST:
            trailer = _trailer_cached(tmdb_id, media_type)
            trailer_calls += 1

        availability = ""
        if avail_calls < AVAILABILITY_LOOKUPS_PER_REQUEST:
            availability = _availability_text(title, DEFAULT_REGION)
            avail_calls += 1
            time.sleep(WATCHMODE_SLEEP_BETWEEN_CALLS)

        similar_bonus = 0.06 if tmdb_id in similar_ids else 0.0
        score = _score_100(c, genre_ids, lang, similar_bonus)

        items.append({
            "type": "movie" if ct == "movie" else "series",
            "title": title,
            "overview": c.get("overview"),
            "rating": c.get("vote_average"),
            "popularity": c.get("popularity"),
            "language": c.get("original_language"),
            "release_date": c.get("release_date"),
            "first_air_date": c.get("first_air_date"),
            "tmdb_id": tmdb_id,
            "poster_url": tmdb_poster_url(c.get("poster_path"), size="w500"),
            "backdrop_url": tmdb_backdrop_url(c.get("backdrop_path"), size="w780"),
            "trailer_url": trailer,
            "available_on": availability,
            "score": score,
        })

        if len(items) >= page_size:
            break

    # Sort this page’s items by score
    items.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "items": items,
        "page": tmdb_page,
        "page_size": page_size,
        "intent": {
            "content_type": ct,
            "language": lang,
            "genres": genre_ids,
            "seed_title": intent.seed_title,
            "year_from": year_from,
            "year_to": year_to,
        }
    }
