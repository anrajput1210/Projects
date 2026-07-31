import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from .ai_intent import parse_intent
from .vocabulary import (
    BILLING_PROMINENCE,
    BILLING_PROMINENCE_FLOOR,
    BILLING_PROMINENCE_UNKNOWN,
    DISCARD_CHARACTER_PATTERNS,
    MIN_CREDIT_VOTES,
    MIN_SORT_PROMINENCE,
    RATING_SORT_VOTE_FLOOR,
    RECENCY_SORT_VOTE_FLOOR,
    to_tv_genres,
)
from .providers import (
    tmdb_discover_movie,
    tmdb_discover_tv,
    tmdb_search_movie,
    tmdb_search_tv,
    tmdb_search_multi,
    tmdb_search_person,
    tmdb_search_keyword,
    tmdb_person_credits,
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

def _role_from_department(department: Optional[str]) -> str:
    d = (department or "").lower()
    if d == "directing":
        return "director"
    if d == "writing":
        return "writer"
    return "actor"


def _safe_call(fn, *args, **kwargs):
    """Run a provider call, swallowing transient network/API errors so one
    failing route can fall through to the next instead of crashing the
    whole request. Missing-API-key errors (RuntimeError) still propagate,
    since that's a configuration problem the caller needs to know about.
    """
    try:
        return fn(*args, **kwargs)
    except requests.exceptions.RequestException:
        return None


_DISCARD_CHARACTER_RE = re.compile("|".join(DISCARD_CHARACTER_PATTERNS), re.IGNORECASE)


def _is_real_role(credit: Dict) -> bool:
    """Discard only credits nobody could mean: archive footage and uncredited
    walk-ons. Everything else is kept and handled by ranking instead.

    Deliberately permissive. Filtering on billing order or a missing character
    name looks reasonable but deletes real leading roles — Under the Skin has
    Scarlett Johansson billed 0th with no character string at all.
    """
    return not _DISCARD_CHARACTER_RE.search(credit.get("character") or "")


def _billing_prominence(credit: Dict) -> float:
    """How central this person was to the film, from their billing position."""
    order = credit.get("order")
    if order is None:
        return BILLING_PROMINENCE_UNKNOWN
    for threshold, weight in BILLING_PROMINENCE:
        if order <= threshold:
            return weight
    return BILLING_PROMINENCE_FLOOR


def _credit_rank_score(credit: Dict) -> float:
    """Notability weighted by how prominent the person's role was.

    This is what keeps a bit part out of the top results without deleting it:
    Shah Rukh Khan is billed 24th in Rocketry, so its vote count is discounted
    to a fifth and it sinks below the films he actually leads — while Morgan
    Freeman's 11th-billed Lucius Fox keeps enough weight to stay near the top.
    """
    return float(credit.get("vote_count") or 0) * _billing_prominence(credit)


def _rank_person_credits(pool: List[Dict], sort_by: Optional[str]) -> List[Dict]:
    """Order a filmography the way a viewer would expect.

    Every explicit sort partitions the same way first: credits where the
    person actually featured, and that enough people have seen, lead; the
    remainder follows. Sorting the raw pool by date or rating alone lets
    walk-on parts and unreleased titles head the list.
    """
    def _date_of(c: Dict) -> str:
        return c.get("release_date") or c.get("first_air_date") or ""

    def _significant(c: Dict, vote_floor: int) -> bool:
        return ((c.get("vote_count") or 0) >= vote_floor
                and _billing_prominence(c) >= MIN_SORT_PROMINENCE)

    def _partition(vote_floor: int):
        lead, minor = [], []
        for c in pool:
            (lead if _significant(c, vote_floor) else minor).append(c)
        return lead, minor

    if sort_by in ("vote_average.desc", "vote_average.asc"):
        lead, minor = _partition(MIN_CREDIT_VOTES)
        lead.sort(key=lambda c: c.get("vote_average") or 0,
                  reverse=sort_by.endswith(".desc"))
        minor.sort(key=_credit_rank_score, reverse=True)
        return lead + minor

    if sort_by in ("primary_release_date.desc", "primary_release_date.asc",
                   "first_air_date.desc", "first_air_date.asc"):
        newest_first = sort_by.endswith(".desc")
        # A lower floor than rating sorts: recent releases have had less time
        # to accumulate votes, but the floor still keeps unreleased entries
        # with no audience at all from leading "newest first".
        lead, minor = _partition(RECENCY_SORT_VOTE_FLOOR)
        for group in (lead, minor):
            group.sort(key=lambda c: (bool(_date_of(c)), _date_of(c)) if newest_first
                       else (not _date_of(c), _date_of(c)),
                       reverse=newest_first)
        return lead + minor

    # Default: most notable roles first.
    return sorted(pool, key=_credit_rank_score, reverse=True)


def _in_year_range(item: Dict, year_from: Optional[int], year_to: Optional[int]) -> bool:
    """Year check for credit entries, which carry their own release dates."""
    date = item.get("release_date") or item.get("first_air_date") or ""
    if len(date) < 4 or not date[:4].isdigit():
        return False  # unknown date: exclude when the user asked for an era
    year = int(date[:4])
    if year_from and year < year_from:
        return False
    if year_to and year > year_to:
        return False
    return True


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
    sort_by: Optional[str] = None,
) -> Dict:
    # 1) Parse the query with the local intent engine (see ai_intent.py)
    h = parse_intent(user_text)

    # An explicit sort chosen in the UI outranks one inferred from the text.
    effective_sort = sort_by or h.sort_by
    # Rating sorts are meaningless without a vote floor: TMDB will happily
    # return titles rated 10.0 from a single vote.
    min_votes = h.min_votes
    if not min_votes:
        if effective_sort in ("vote_average.desc", "vote_average.asc"):
            min_votes = RATING_SORT_VOTE_FLOOR
        elif effective_sort == "primary_release_date.desc":
            min_votes = RECENCY_SORT_VOTE_FLOOR

    ct_raw = content_type or h.content_type or "movie"
    ct = _normalize_content_type(ct_raw)

    lang = language or h.language
    year_from = h.year_from
    year_to = h.year_to
    genre_ids = list(h.genres)
    exclude_ids = list(h.exclude_genres)
    title_query = h.seed_title
    person_name = h.person_name
    person_role = h.person_role
    resolved_as = None

    tmdb_page = max(int(page), 1)
    # An explicit "top 5" in the query overrides the caller's page size.
    if h.limit:
        page_size = min(h.limit, page_size)

    candidates: List[Dict] = []
    media_type = "movie" if ct == "movie" else "tv"
    seed_id: Optional[int] = None  # exact title match, pinned to first place

    # 2) RESIDUAL RESOLUTION — the engine leaves behind only text it could
    #    not explain. One search/multi call decides whether that text is a
    #    person, a movie or a show, instead of guessing from word count.
    if h.residual and not title_query:
        multi = (_safe_call(tmdb_search_multi, h.residual, page=1) or {}).get("results", [])
        best = next((r for r in multi if r.get("media_type") in ("movie", "tv", "person")), None)
        if best:
            if best.get("media_type") == "person":
                person_name = h.residual
                if not person_role:
                    person_role = _role_from_department(best.get("known_for_department"))
                resolved_as = "person"
            else:
                title_query = h.residual
                resolved_as = "title"

    # 3) PERSON ROUTE: "movies directed by christopher nolan"
    if person_name:
        pr = (_safe_call(tmdb_search_person, person_name, page=1) or {}).get("results", [])
        if pr:
            pid = pr[0].get("id")
            if not person_role:
                person_role = _role_from_department(pr[0].get("known_for_department"))
            credits = _safe_call(tmdb_person_credits, pid) or {}
            cast = credits.get("cast", [])
            crew = credits.get("crew", [])

            if person_role == "director":
                pool = [x for x in crew if x.get("job") == "Director"]
            elif person_role == "writer":
                pool = [x for x in crew if x.get("job") in ("Writer", "Screenplay", "Story")]
            else:
                # Actors accumulate cameos and self-appearances; keep only
                # credits where they actually played a significant part.
                pool = [x for x in cast if _is_real_role(x)]

            wanted_media = "movie" if ct == "movie" else "tv"
            pool = [x for x in pool if x.get("media_type") == wanted_media]
            if lang:
                pool = [x for x in pool if x.get("original_language") == lang]
            if year_from or year_to:
                # Credits carry their own dates; discover-style year params
                # don't apply on this route, so filter the pool directly.
                pool = [x for x in pool if _in_year_range(x, year_from, year_to)]
            if genre_ids:
                pool = [x for x in pool if set(x.get("genre_ids") or []) & set(genre_ids)]
            if exclude_ids:
                pool = [x for x in pool if not (set(x.get("genre_ids") or []) & set(exclude_ids))]

            candidates = _rank_person_credits(pool, effective_sort)

    # 4) TITLE ROUTE: an exact title, or "like <title>"
    if not candidates and title_query:
        m = (_safe_call(tmdb_search_multi, title_query, page=1) or {}).get("results", [])
        best = None
        for r in m:
            if ct == "movie" and r.get("media_type") == "movie":
                best = r
                break
            if ct == "series" and r.get("media_type") == "tv":
                best = r
                break
        if not best:
            best = next((r for r in m if r.get("media_type") in ("movie", "tv")), None)

        if best and best.get("id"):
            seed_media = best["media_type"]
            media_type = seed_media
            seed_id = best["id"]
            sim = (_safe_call(tmdb_similar, best["id"], seed_media, page=tmdb_page) or {}).get("results", [])
            # Seed the list with the matched title itself, then its neighbours.
            candidates = [best] + sim

    # 5) DISCOVER ROUTE: structured filters straight from the engine
    if not candidates:
        keyword_ids: List[int] = []
        for term in h.keywords[:2]:
            kw = (_safe_call(tmdb_search_keyword, term, page=1) or {}).get("results", [])
            if kw and kw[0].get("id"):
                keyword_ids.append(kw[0]["id"])

        shared = dict(
            page=tmdb_page,
            language=lang,
            year_from=year_from,
            year_to=year_to,
            sort_by=effective_sort,
            with_keywords=keyword_ids or None,
            min_votes=min_votes,
            min_rating=h.min_rating,
            runtime_lte=h.runtime_lte,
            runtime_gte=h.runtime_gte,
        )

        if ct == "movie":
            candidates = (_safe_call(
                tmdb_discover_movie,
                genres=genre_ids or None,
                exclude_genres=exclude_ids or None,
                **shared,
            ) or {}).get("results", [])
            media_type = "movie"
        else:
            # TMDB keeps a separate genre-id namespace for TV; sending movie
            # ids here silently returns zero results.
            candidates = (_safe_call(
                tmdb_discover_tv,
                genres=to_tv_genres(genre_ids) or None,
                exclude_genres=to_tv_genres(exclude_ids) or None,
                **shared,
            ) or {}).get("results", [])
            media_type = "tv"

    # 6) Fallback search: always return something close
    if not candidates and user_text.strip():
        probe = h.residual or user_text.strip()
        if ct == "movie":
            candidates = (_safe_call(tmdb_search_movie, probe, page=tmdb_page) or {}).get("results", [])
            media_type = "movie"
        else:
            candidates = (_safe_call(tmdb_search_tv, probe, page=tmdb_page) or {}).get("results", [])
            media_type = "tv"

    candidates = _dedupe_by_id(candidates)

    # 6) Build page results: scoring, trailer lookup, availability lookup
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
            "is_exact_match": tmdb_id == seed_id,
            "score": score,
        })

        if len(items) >= page_size:
            break

    if effective_sort:
        # A sort was explicitly requested, so the upstream ordering is the
        # answer. Re-ranking by match score here would silently undo it —
        # only the exact-title match is floated to the top. Python's sort is
        # stable, so every other position survives untouched.
        items.sort(key=lambda x: not x.get("is_exact_match"))
    else:
        # No explicit sort: rank by how well each title fits the request.
        items.sort(key=lambda x: (not x.get("is_exact_match"), -x.get("score", 0)))

    return {
        "items": items,
        "page": tmdb_page,
        "page_size": page_size,
        "intent": {
            "content_type": "movie" if media_type == "movie" else "series",
            "language": lang,
            "genres": genre_ids,
            "exclude_genres": exclude_ids,
            "keywords": h.keywords,
            "year_from": year_from,
            "year_to": year_to,
            "title_query": title_query,
            "person_name": person_name,
            "person_role": person_role,
            "sort_by": effective_sort,
            "sort_source": "manual" if sort_by else ("query" if h.sort_by else None),
            "min_rating": h.min_rating,
            "min_votes": min_votes,
            "runtime_lte": h.runtime_lte,
            "runtime_gte": h.runtime_gte,
            "limit": h.limit,
            "resolved_as": resolved_as,
            # Every vocabulary term the engine matched, for explainability.
            "matched_terms": [{"kind": k, "term": v} for k, v in h.matched_terms],
        },
    }
