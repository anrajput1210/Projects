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
    tmdb_upcoming_movies,
    watchmode_search,
    watchmode_sources,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "US")

# ---- Performance knobs ----
AVAILABILITY_LOOKUPS_PER_REQUEST = 5
TRAILER_LOOKUPS_PER_REQUEST = 6
WATCHMODE_SLEEP_BETWEEN_CALLS = 0.15

# caches
_WATCHMODE_ID_CACHE: Dict[str, Optional[int]] = {}
_WATCHMODE_SOURCES_CACHE: Dict[Tuple[str, str], List[Dict]] = {}
_TRAILER_CACHE: Dict[Tuple[int, str], Optional[str]] = {}


def _normalize_content_type(ct: str) -> str:
    ct = (ct or "").strip().lower()
    if ct in ("movies", "movie"):
        return "movie"
    if ct in ("series", "tv", "show", "shows"):
        return "series"
    return ct


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
    """
    Returns a readable availability string like:
    'Netflix, Amazon Prime, Hulu'
    or '' if unknown.
    """
    sources = _watchmode_sources_cached(title, region)
    names = []
    for s in sources:
        nm = s.get("name") or s.get("source")
        if nm:
            names.append(nm)
    # de-dupe keep order
    names = list(dict.fromkeys(names))
    # Keep a short list
    names = names[:6]
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


def _genre_overlap(item: Dict, intent_genres: List[int]) -> float:
    item_genres = item.get("genre_ids") or []
    if not intent_genres:
        return 0.35
    return len(set(item_genres).intersection(set(intent_genres))) / max(len(set(intent_genres)), 1)


def _score_100(item: Dict, intent_genres: List[int], intent_lang: Optional[str], similar_bonus: float = 0.0) -> int:
    """
    Score out of 100.
    """
    rating = _rating(item)          # 0..10
    pop = _popularity(item)         # varies a lot
    overlap = _genre_overlap(item, intent_genres)  # 0..1
    lang_match = 1.0 if (intent_lang and item.get("original_language") == intent_lang) else 0.0

    # Normalize popularity roughly into 0..1
    pop_norm = min(pop / 200.0, 1.0)

    # Weighted components -> 0..1
    base = (
        0.50 * (rating / 10.0) +
        0.25 * overlap +
        0.20 * pop_norm +
        0.05 * lang_match
    )

    # Similar bonus used when item comes from "similar to X"
    base = min(base + similar_bonus, 1.0)

    return int(round(base * 100))


def recommend_ai(
    user_text: str,
    content_type: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 10,
) -> List[Dict]:
    intent = parse_intent(user_text)

    ct = _normalize_content_type(content_type or intent.content_type or "movie")
    lang = (language or intent.language or None)
    lim = intent.limit or limit
    genre_ids = intent.genres or []

    # 1) Discover
    candidates: List[Dict] = []
    for page in (1, 2, 3, 4, 5):
        if ct == "movie":
            candidates += tmdb_discover_movie(genres=genre_ids or None, page=page, language=lang).get("results", [])
        else:
            candidates += tmdb_discover_tv(genres=genre_ids or None, page=page, language=lang).get("results", [])

    # 2) Fallback search
    if not candidates and user_text.strip():
        if ct == "movie":
            candidates = tmdb_search_movie(user_text.strip(), page=1).get("results", [])
        else:
            candidates = tmdb_search_tv(user_text.strip(), page=1).get("results", [])
        if lang:
            candidates = [c for c in candidates if c.get("original_language") == lang]

    # 3) Similar expansion
    similar_ids = set()
    if intent.seed_title:
        if ct == "movie":
            seed_results = tmdb_search_movie(intent.seed_title, page=1).get("results", [])
            seed_id = seed_results[0].get("id") if seed_results else None
            media_type = "movie"
        else:
            seed_results = tmdb_search_tv(intent.seed_title, page=1).get("results", [])
            seed_id = seed_results[0].get("id") if seed_results else None
            media_type = "tv"

        if seed_id:
            sim = []
            for page in (1, 2):
                sim += tmdb_similar(seed_id, media_type, page=page).get("results", [])
            if lang:
                sim = [c for c in sim if c.get("original_language") == lang]
            for s in sim:
                if s.get("id"):
                    similar_ids.add(s["id"])
            candidates = sim + candidates

    # 4) Dedup
    seen = set()
    deduped = []
    for c in candidates:
        cid = c.get("id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        deduped.append(c)

    # 5) Score + enrich (availability + trailer limited)
    scored: List[Tuple[int, Dict]] = []
    trailer_calls = 0
    avail_calls = 0

    for c in deduped[: max(lim * 8, 80)]:
        title = c.get("title") if ct == "movie" else c.get("name")
        if not title:
            continue

        tmdb_id = c.get("id")
        if not tmdb_id:
            continue

        # trailer limited
        trailer = None
        if trailer_calls < TRAILER_LOOKUPS_PER_REQUEST:
            trailer = _trailer_cached(tmdb_id, "movie" if ct == "movie" else "tv")
            trailer_calls += 1

        # availability limited (safe)
        availability = ""
        if avail_calls < AVAILABILITY_LOOKUPS_PER_REQUEST:
            availability = _availability_text(title, DEFAULT_REGION)
            avail_calls += 1
            time.sleep(WATCHMODE_SLEEP_BETWEEN_CALLS)

        similar_bonus = 0.06 if tmdb_id in similar_ids else 0.0
        score = _score_100(c, genre_ids, lang, similar_bonus=similar_bonus)

        payload = {
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
            "available_on": availability,          # ✅ text line
            "score": score,                        # ✅ out of 100
            "intent": {
                "content_type": ct,
                "language": lang,
                "genres": genre_ids,
                "seed_title": intent.seed_title,
            },
        }

        scored.append((score, payload))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:lim]]


def upcoming(limit: int = 10) -> List[Dict]:
    data = tmdb_upcoming_movies(page=1)
    results = data.get("results", [])[:limit]
    out = []
    for x in results:
        tmdb_id = x.get("id")
        out.append({
            "type": "upcoming_movie",
            "title": x.get("title"),
            "release_date": x.get("release_date"),
            "tmdb_id": tmdb_id,
            "poster_url": tmdb_poster_url(x.get("poster_path"), size="w500"),
            "backdrop_url": tmdb_backdrop_url(x.get("backdrop_path"), size="w780"),
            "trailer_url": _trailer_cached(tmdb_id, "movie") if tmdb_id else None,
        })
    return out
