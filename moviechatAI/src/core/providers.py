import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
WATCHMODE_BASE = "https://api.watchmode.com/v1"


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


def tmdb_discover_movie(
    genres: Optional[List[int]] = None,
    page: int = 1,
    language: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "api_key": _tmdb_key(),
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }
    if genres:
        params["with_genres"] = ",".join(map(str, genres))
    if language:
        params["with_original_language"] = language

    # ✅ date filters for movies
    if year_from:
        params["primary_release_date.gte"] = f"{year_from}-01-01"
    if year_to:
        params["primary_release_date.lte"] = f"{year_to}-12-31"

    r = requests.get(f"{TMDB_BASE}/discover/movie", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_discover_tv(
    genres: Optional[List[int]] = None,
    page: int = 1,
    language: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "api_key": _tmdb_key(),
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }
    if genres:
        params["with_genres"] = ",".join(map(str, genres))
    if language:
        params["with_original_language"] = language

    # ✅ date filters for TV
    if year_from:
        params["first_air_date.gte"] = f"{year_from}-01-01"
    if year_to:
        params["first_air_date.lte"] = f"{year_to}-12-31"

    r = requests.get(f"{TMDB_BASE}/discover/tv", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_movie(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = requests.get(f"{TMDB_BASE}/search/movie", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_tv(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = requests.get(f"{TMDB_BASE}/search/tv", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_similar(tmdb_id: int, media_type: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "page": page}
    r = requests.get(f"{TMDB_BASE}/{media_type}/{tmdb_id}/similar", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_get_trailer_url(tmdb_id: int, media_type: str) -> Optional[str]:
    params = {"api_key": _tmdb_key()}
    r = requests.get(f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos", params=params, timeout=30)
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
    r = requests.get(f"{TMDB_BASE}/movie/upcoming", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def watchmode_search(title: str) -> Dict[str, Any]:
    params = {"apiKey": _watchmode_key(), "search_field": "name", "search_value": title}
    r = requests.get(f"{WATCHMODE_BASE}/search/", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def watchmode_sources(title_id: int, region: str = "US") -> List[Dict[str, Any]]:
    params = {"apiKey": _watchmode_key(), "regions": region}
    r = requests.get(f"{WATCHMODE_BASE}/title/{title_id}/sources/", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def tmdb_search_multi(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = requests.get(f"{TMDB_BASE}/search/multi", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_person(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page, "include_adult": "false"}
    r = requests.get(f"{TMDB_BASE}/search/person", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_person_credits(person_id: int) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key()}
    r = requests.get(f"{TMDB_BASE}/person/{person_id}/combined_credits", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def tmdb_search_keyword(query: str, page: int = 1) -> Dict[str, Any]:
    params = {"api_key": _tmdb_key(), "query": query, "page": page}
    r = requests.get(f"{TMDB_BASE}/search/keyword", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

