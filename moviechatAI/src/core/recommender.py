from .gemini_intent import gemini_parse_intent
from .providers import (
    tmdb_search_multi,
    tmdb_search_person,
    tmdb_person_credits,
    tmdb_search_keyword,
)
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

def _looks_like_person_query(text: str) -> bool:
    t = (text or "").lower()
    return (" movies" in t or " films" in t or " film" in t or " movies" in t) and (
        "actor" in t or "director" in t or "starring" in t or "by " in t or len(t.split()) <= 4
    )

def _dedupe_by_id(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for x in items:
        xid = x.get("id")
        if not xid or xid in seen:
            continue
        seen.add(xid)
        out.append(x)
    return out

def recommend_ai(
    user_text: str,
    content_type: Optional[str] = None,
    language: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict:
    # 1) Gemini intent (fallback to heuristic if None)
    g = gemini_parse_intent(user_text) or {}

    # choose content type: explicit override > gemini > heuristic > default
    h = parse_intent(user_text)
    ct_raw = content_type or g.get("content_type") or h.content_type or "unknown"
    ct = _normalize_content_type(ct_raw if ct_raw != "unknown" else "movie")

    lang = language or g.get("language") or h.language or None
    year_from = g.get("year_from") or h.year_from
    year_to = g.get("year_to") or h.year_to

    # genres: Gemini gives words -> ids via your ai_intent TMDB_GENRES mapping
    from .ai_intent import TMDB_GENRES as GMAP
    genre_ids = []
    for w in (g.get("genres") or []):
        w = (w or "").strip().lower()
        if w in GMAP:
            genre_ids.append(GMAP[w])
    if not genre_ids:
        genre_ids = h.genres or []
    genre_ids = list(dict.fromkeys(genre_ids))

    title_query = g.get("title_query") or h.seed_title  # treat "like X" same as title_query
    person_name = g.get("person_name")
    person_role = g.get("person_role")  # actor/director/writer
    keyword_terms = (g.get("keywords") or [])

    tmdb_page = max(int(page), 1)

    candidates: List[Dict] = []
    media_type = "movie" if ct == "movie" else "tv"

    # 2) PERSON ROUTE: "tom cruise movies" / "nolan films"
    if person_name or _looks_like_person_query(user_text):
        name = person_name or user_text.replace("movies", "").replace("films", "").strip()
        pr = tmdb_search_person(name, page=1).get("results", [])
        if pr:
            pid = pr[0].get("id")
            credits = tmdb_person_credits(pid)
            cast = credits.get("cast", [])
            crew = credits.get("crew", [])

            if person_role == "director":
                pool = [x for x in crew if x.get("job") == "Director"]
            elif person_role == "writer":
                pool = [x for x in crew if x.get("job") in ("Writer", "Screenplay", "Story")]
            else:
                pool = cast  # actor default

            # filter by movie vs series
            if ct == "movie":
                pool = [x for x in pool if x.get("media_type") == "movie"]
            else:
                pool = [x for x in pool if x.get("media_type") == "tv"]

            if lang:
                pool = [x for x in pool if x.get("original_language") == lang]

            # score by popularity + vote_average
            pool.sort(key=lambda x: ((x.get("vote_average") or 0) * 10 + (x.get("popularity") or 0)), reverse=True)
            candidates = pool

    # 3) TITLE ROUTE: "game of thrones" should match TV title and use similar
    if not candidates and title_query:
        m = tmdb_search_multi(title_query, page=1).get("results", [])
        # choose best match that fits ct if possible
        best = None
        for r in m:
            if r.get("media_type") in ("movie", "tv"):
                if ct == "movie" and r.get("media_type") == "movie":
                    best = r; break
                if ct == "series" and r.get("media_type") == "tv":
                    best = r; break
        if not best and m:
            best = m[0]

        if best and best.get("id") and best.get("media_type") in ("movie", "tv"):
            seed_media = best["media_type"]
            seed_id = best["id"]
            media_type = seed_media
            # similar results are the closest match (fixes "way off")
            sim = tmdb_similar(seed_id, seed_media, page=tmdb_page).get("results", [])
            candidates = sim

            # If user asked the title itself (not “like”), include it first
            candidates = [best] + candidates

    # 4) KEYWORD ROUTE: "heist" -> TMDB keywords -> discover with_keywords
    if not candidates and keyword_terms:
        # resolve first keyword term to TMDB keyword id
        kw_ids = []
        for term in keyword_terms[:2]:
            kw = tmdb_search_keyword(term, page=1).get("results", [])
            if kw:
                kw_ids.append(kw[0].get("id"))
        kw_ids = [k for k in kw_ids if k]

        if ct == "movie":
            candidates = tmdb_discover_movie(
                genres=genre_ids or None,
                page=tmdb_page,
                language=lang,
                year_from=year_from,
                year_to=year_to,
                with_keywords=kw_ids or None,
            ).get("results", [])
            media_type = "movie"
        else:
            candidates = tmdb_discover_tv(
                genres=genre_ids or None,
                page=tmdb_page,
                language=lang,
                year_from=year_from,
                year_to=year_to,
                with_keywords=kw_ids or None,
            ).get("results", [])
            media_type = "tv"

    # 5) DEFAULT ROUTE: discover with filters (genres/lang/year)
    if not candidates:
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

    # 6) Fallback search: ALWAYS return something close
    if not candidates and user_text.strip():
        if ct == "movie":
            candidates = tmdb_search_movie(user_text.strip(), page=tmdb_page).get("results", [])
            media_type = "movie"
        else:
            candidates = tmdb_search_tv(user_text.strip(), page=tmdb_page).get("results", [])
            media_type = "tv"

    candidates = _dedupe_by_id(candidates)

    # 7) Build page results (your existing scoring/trailer/availability)
    items: List[Dict] = []
    trailer_calls = 0
    avail_calls = 0

    for c in candidates:
        tmdb_id = c.get("id")
        if not tmdb_id:
            continue

        title = c.get("title") if media_type == "movie" else c.get("name")
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

        # use your score function (genre_ids/lang) — similar is already handled by routing
        score = _score_100(c, genre_ids, lang, similar_bonus=0.06 if title_query else 0.0)

        items.append({
            "type": "movie" if media_type == "movie" else "series",
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

    items.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "items": items,
        "page": tmdb_page,
        "page_size": page_size,
        "intent": {
            "content_type": "movie" if media_type == "movie" else "series",
            "language": lang,
            "genres": genre_ids,
            "year_from": year_from,
            "year_to": year_to,
            "title_query": title_query,
            "person_name": person_name,
            "person_role": person_role,
            "keywords": keyword_terms,
            "phase3_gemini_enabled": bool(g),
        },
    }
