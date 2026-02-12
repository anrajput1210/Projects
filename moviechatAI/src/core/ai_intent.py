import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Intent:
    content_type: Optional[str] = None        # "movie" or "series"
    language: Optional[str] = None            # ISO 639-1 like "hi", "en"
    genres: List[int] = None                  # TMDB genre ids
    seed_title: Optional[str] = None          # "like sacred games"
    year_from: Optional[int] = None           # inclusive
    year_to: Optional[int] = None             # inclusive
    limit: Optional[int] = None


TMDB_GENRES: Dict[str, int] = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "anime": 16,          # treat "anime" as animation
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "sci fi": 878,
    "sci-fi": 878,
    "thriller": 53,
    "war": 10752,
}

LANG_HINTS: List[Tuple[List[str], str]] = [
    (["hindi", "bollywood", "india", "indian"], "hi"),
    (["english", "hollywood"], "en"),
    (["korean", "k-drama", "kdrama"], "ko"),
    (["japanese", "jp", "anime"], "ja"),  # anime often japanese
    (["spanish"], "es"),
    (["french"], "fr"),
    (["tamil"], "ta"),
    (["telugu"], "te"),
]

CONTENT_HINTS = {
    "movie": ["movie", "movies", "film", "films"],
    "series": ["series", "tv", "show", "shows", "web series", "episode", "episodes"],
}


def _extract_years(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Understands:
      - after 2015 / since 2015
      - before 2015 / until 2015
      - between 2015 and 2020
      - 2019 movies
    """
    t = (text or "").lower()

    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", t)]
    year_from = None
    year_to = None

    # between X and Y
    m = re.search(r"\bbetween\s+(19\d{2}|20\d{2})\s+(and|to)\s+(19\d{2}|20\d{2})\b", t)
    if m:
        a, b = int(m.group(1)), int(m.group(3))
        year_from, year_to = min(a, b), max(a, b)
        return year_from, year_to

    # after / since
    m = re.search(r"\b(after|since)\s+(19\d{2}|20\d{2})\b", t)
    if m:
        y = int(m.group(2))
        year_from = y + 1 if "after" in m.group(1) else y
        # keep year_to None
        return year_from, year_to

    # before / until
    m = re.search(r"\b(before|until)\s+(19\d{2}|20\d{2})\b", t)
    if m:
        y = int(m.group(2))
        year_to = y - 1 if "before" in m.group(1) else y
        return year_from, year_to

    # single year mentioned: treat as that year
    if len(years) == 1:
        year_from = years[0]
        year_to = years[0]

    # if user mentions 2+ years without "between", ignore (too ambiguous)
    return year_from, year_to


def parse_intent(text: str) -> Intent:
    t = (text or "").strip().lower()

    intent = Intent(genres=[])

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

    # genres (keyword -> id)
    for name, gid in TMDB_GENRES.items():
        if re.search(rf"\b{re.escape(name)}\b", t):
            intent.genres.append(gid)

    # extra fuzzy: "thrill" -> thriller
    if "thrill" in t and 53 not in intent.genres:
        intent.genres.append(53)

    # seed title: "like X" or "similar to X"
    m = re.search(r"(like|similar to)\s+(.+)$", t)
    if m:
        seed = m.group(2).strip()
        seed = re.sub(r"\b(on|from)\b.*$", "", seed).strip()
        intent.seed_title = seed if seed else None

    # years
    intent.year_from, intent.year_to = _extract_years(t)

    # limit: "top 5", "5 recommendations"
    m2 = re.search(r"\btop\s+(\d+)\b", t) or re.search(r"\b(\d+)\s+(recommendations|recs|movies|shows)\b", t)
    if m2:
        try:
            intent.limit = int(m2.group(1))
        except Exception:
            pass

    # de-dupe
    intent.genres = list(dict.fromkeys(intent.genres))
    return intent
