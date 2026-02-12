import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Intent:
    content_type: Optional[str] = None   # "movie" or "series"
    language: Optional[str] = None       # "en", "hi", ...
    genres: List[int] = None             # TMDB genre ids
    subscriptions: List[str] = None
    seed_title: Optional[str] = None     # "like sacred games"
    strict_subs: bool = False            # if user says "only on netflix"
    limit: Optional[int] = None


TMDB_GENRES: Dict[str, int] = {
    "action": 28,
    "comedy": 35,
    "crime": 80,
    "thriller": 53,
    "animation": 16,
    "drama": 18,
    "mystery": 9648,
    "romance": 10749,
    "horror": 27,
    "sci fi": 878,
    "sci-fi": 878,
    "fantasy": 14,
    "family": 10751,
    "adventure": 12,
}

PLATFORM_ALIASES: Dict[str, str] = {
    "netflix": "Netflix",
    "prime": "Amazon Prime",
    "prime video": "Amazon Prime",
    "amazon prime": "Amazon Prime",
    "hulu": "Hulu",
    "disney": "Disney+",
    "disney+": "Disney+",
    "hotstar": "Disney+",
    "max": "HBO Max",
    "hbo": "HBO Max",
    "hbo max": "HBO Max",
    "apple tv": "AppleTV+",
    "apple tv+": "AppleTV+",
    "crunchyroll": "Crunchyroll",
    "paramount": "Paramount+",
    "paramount+": "Paramount+",
    "peacock": "Peacock",
}

LANG_HINTS: List[Tuple[List[str], str]] = [
    (["hindi", "bollywood", "india", "indian"], "hi"),
    (["english", "hollywood"], "en"),
    (["korean", "k-drama", "kdrama"], "ko"),
    (["japanese", "jp"], "ja"),
    (["spanish"], "es"),
    (["french"], "fr"),
    (["tamil"], "ta"),
    (["telugu"], "te"),
]

CONTENT_HINTS = {
    "movie": ["movie", "film", "cinema"],
    "series": ["series", "tv", "show", "shows", "web series", "episode"],
}

STRICT_HINTS = ["only on", "must be on", "available on", "streaming on only"]


def parse_intent(text: str) -> Intent:
    t = (text or "").strip().lower()

    intent = Intent(genres=[], subscriptions=[])

    # content type
    for ct, kws in CONTENT_HINTS.items():
        if any(k in t for k in kws):
            intent.content_type = ct
            break

    # language
    for kws, code in LANG_HINTS:
        if any(k in t for k in kws):
            intent.language = code
            break

    # genres
    for name, gid in TMDB_GENRES.items():
        if name in t:
            intent.genres.append(gid)

    # extra fuzzy: "thrill" -> thriller
    if "thrill" in t and 53 not in intent.genres:
        intent.genres.append(53)

    # subscriptions
    for k, v in PLATFORM_ALIASES.items():
        if re.search(rf"\b{re.escape(k)}\b", t):
            intent.subscriptions.append(v)

    # strict subs
    if any(h in t for h in STRICT_HINTS):
        intent.strict_subs = True

    # seed title: "like X" or "similar to X"
    m = re.search(r"(like|similar to)\s+(.+)$", t)
    if m:
        seed = m.group(2).strip()
        # remove platform words at end
        seed = re.sub(r"\b(on|from)\b.*$", "", seed).strip()
        intent.seed_title = seed if seed else None

    # limit: "top 5", "5 recommendations"
    m2 = re.search(r"\btop\s+(\d+)\b", t) or re.search(r"\b(\d+)\s+(recommendations|recs|movies|shows)\b", t)
    if m2:
        try:
            intent.limit = int(m2.group(1))
        except Exception:
            pass

    # clean duplicates
    intent.genres = list(dict.fromkeys(intent.genres))
    intent.subscriptions = list(dict.fromkeys(intent.subscriptions))

    return intent
