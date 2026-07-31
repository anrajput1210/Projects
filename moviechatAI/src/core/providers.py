import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
WATCHMODE_BASE = "https://api.watchmode.com/v1"

# A shared session with connection pooling + automatic retries. Without this,
# rapid-fire calls (this app makes several per request for trailers/availability)
# can hit transient connection resets that would otherwise look like "no results".
_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retry, pool_maxsize=20))
_session.mount("http://", HTTPAdapter(max_retries=_retry, pool_maxsize=20))


def _tmdb_key() -> str:
    key = os.getenv("TMDB_API_KEY")
    if not key:
        raise RuntimeError("TMDB_API_KEY not found. Put it in moviechatAI/.env")
    return key


def _watchmode_key() -> str:
    key = os.getenv("WATCHMODE_API_KEY")
    if not key:
        raise RuntimeError("WATCHMODE_API_KEY not found. Put it in moviechatAI/.env")
    return key


def tmdb_poster_url(poster_path: Optional[str], size: str = "w500") -> Optional[str]:
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE}/{size}{poster_path}"


def tmdb_backdrop_url(backdrop_path: Optional[str], size: str = "w780") -> Optional[str]:
    if not backdrop_path:
        return None
    return f"{TMDB_IMAGE_BASE}/{size}{backdrop_path}"


# TMDB's TV discover endpoint uses different sort keys than movies.
_TV_SORT_MAP = {
    "primary_release_date.desc": "first_air_date.desc",
    "primary_release_date.asc": "first_air_date.asc",
    "revenue.desc": "popularity.desc",   # TV titles carry no revenue data
}


def _today() -> str:
    return datetime.date.today().isoformat()


def _discover_params(
    genres: Optional[List[int]],
    page: int,
    language: Optional[str],
    sort_by: Optional[str],
    exclude_genres: Optional[List[int]],
    with_keywords: Optional[List[int]],
    min_votes: Optional[int],
    min_rating: Optional[float],
    runtime_lte: Optional[int],
    runtime_gte: Optional[int],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "api_key": _tmdb_key(),
        "page": page,
        "sort_by": sort_by or "popularity.desc",
        "include_adult": "false",
    }
    if genres:
        params["with_genres"] = ",".join(map(str, genres))
    if exclude_genres:
        params["without_genres"] = ",".join(map(str, exclude_genres))
    if with_keywords:
        params["with_keywords"] = "|".join(map(str, with_keywords))
    if language:
        params["with_original_language"] = language
    if min_votes:
        params["vote_count.gte"] = min_votes
    if min_rating:
        params["vote_average.gte"] = min_rating
    if runtime_lte:
        params["with_runtime.lte"] = runtime_lte
    if runtime_gte:
        params["with_runtime.gte"] = runtime_gte
    return params


def tmdb_discover_movie(
    genres: Optional[List[int]] = None,
    page: int = 1,
    language: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sort_by: Optional[str] = None,
    exclude_genres: Optional[List[int]] = None,
    with_keywords: Optional[List[int]] = None,
    min_votes: Optional[int] = None,
    min_rating: Optional[float] = None,
    runtime_lte: Optional[int] = None,
    runtime_gte: Optional[int] = None,
) -> Dict[str, Any]:
    params = _discover_params(
        genres, page, language, sort_by, exclude_genres, with_keywords,
        min_votes, min_rating, runtime_lte, runtime_gte,
    )
    if year_from:
        params["primary_release_date.gte"] = f"{year_from}-01-01"
    if year_to:
        params["primary_release_date.lte"] = f"{year_to}-12-31"
    elif sort_by == "primary_release_date.desc":
        # "Newest first" otherwise leads with films years from release that
        # have no ratings yet (Avatar 5, 2031).
        params["primary_release_date.lte"] = _today()

    r = _session.get(f"{TMDB_BASE}/discover/movie", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_discover_tv(
    genres: Optional[List[int]] = None,
    page: int = 1,
    language: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sort_by: Optional[str] = None,
    exclude_genres: Optional[List[int]] = None,
    with_keywords: Optional[List[int]] = None,
    min_votes: Optional[int] = None,
    min_rating: Optional[float] = None,
    runtime_lte: Optional[int] = None,
    runtime_gte: Optional[int] = None,
) -> Dict[str, Any]:
    params = _discover_params(
        genres, page, language, _TV_SORT_MAP.get(sort_by or "", sort_by),
        exclude_genres, with_keywords, min_votes, min_rating,
        runtime_lte, runtime_gte,
    )
    if year_from:
        params["first_air_date.gte"] = f"{year_from}-01-01"
    if year_to:
        params["first_air_date.lte"] = f"{year_to}-12-31"
    elif params.get("sort_by") == "first_air_date.desc":
        params["first_air_date.lte"] = _today()

    r = _session.get(f"{TMDB_BASE}/discover/tv", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_movie(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = _session.get(f"{TMDB_BASE}/search/movie", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_tv(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = _session.get(f"{TMDB_BASE}/search/tv", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_similar(tmdb_id: int, media_type: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "page": page}
    r = _session.get(f"{TMDB_BASE}/{media_type}/{tmdb_id}/similar", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_get_trailer_url(tmdb_id: int, media_type: str) -> Optional[str]:
    params = {"api_key": _tmdb_key()}
    r = _session.get(f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos", params=params, timeout=30)
    r.raise_for_status()

    results = r.json().get("results", [])
    for v in results:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            key = v.get("key")
            if key:
                return f"https://www.youtube.com/watch?v={key}"
    for v in results:
        if v.get("site") == "YouTube":
            key = v.get("key")
            if key:
                return f"https://www.youtube.com/watch?v={key}"
    return None


def tmdb_upcoming_movies(page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "page": page}
    r = _session.get(f"{TMDB_BASE}/movie/upcoming", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def watchmode_search(title: str) -> Dict[str, Any]:
    params = {"apiKey": _watchmode_key(), "search_field": "name", "search_value": title}
    r = _session.get(f"{WATCHMODE_BASE}/search/", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def watchmode_sources(title_id: int, region: str = "US") -> List[Dict[str, Any]]:
    params = {"apiKey": _watchmode_key(), "regions": region}
    r = _session.get(f"{WATCHMODE_BASE}/title/{title_id}/sources/", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def tmdb_search_multi(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = _session.get(f"{TMDB_BASE}/search/multi", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_person(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = _session.get(f"{TMDB_BASE}/search/person", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_person_credits(person_id: int) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key()}
    r = _session.get(f"{TMDB_BASE}/person/{person_id}/combined_credits", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_keyword(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page}
    r = _session.get(f"{TMDB_BASE}/search/keyword", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

