"""Natural-language intent engine for MovieChat.

Design: a *token-consuming* parser. Each stage matches its vocabulary against
the query and masks the span it claimed, so later stages never re-read the
same words. Whatever text survives every stage is, by elimination, the part
the engine could not explain — a person or a title — which is exactly what
should be sent to TMDB's search endpoints.

This is what keeps "highest rated horror movies" from being mistaken for a
person named "highest rated horror": every word is consumed by the sort,
genre and content-type stages, leaving an empty residual.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .vocabulary import (
    CONTENT_HINTS,
    DECADES,
    KEYWORD_TERMS,
    LANG_HINTS,
    MOOD_TERMS,
    MOVIE_GENRES,
    NEGATION_CUES,
    RATING_SORT_VOTE_FLOOR,
    ROLE_TERMS,
    RUNTIME_TERMS,
    SORT_TERMS,
)

# Backwards-compatible alias: older code imported TMDB_GENRES from here.
TMDB_GENRES = MOVIE_GENRES


@dataclass
class Intent:
    content_type: Optional[str] = None          # "movie" | "series"
    language: Optional[str] = None              # ISO 639-1
    genres: List[int] = field(default_factory=list)          # movie-namespace ids
    exclude_genres: List[int] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    seed_title: Optional[str] = None            # "like X"
    person_name: Optional[str] = None
    person_role: Optional[str] = None           # actor | director | writer
    residual: Optional[str] = None              # unexplained text (person or title)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sort_by: Optional[str] = None
    min_votes: Optional[int] = None
    min_rating: Optional[float] = None
    runtime_lte: Optional[int] = None
    runtime_gte: Optional[int] = None
    limit: Optional[int] = None
    matched_terms: List[Tuple[str, str]] = field(default_factory=list)


# Conversational lead-ins stripped before parsing so words like "show" in
# "show me..." are not mistaken for a content-type hint.
_LEAD_INS = [
    "show me", "give me", "find me", "get me", "recommend me", "suggest me",
    "i want to watch", "i want", "i'm looking for", "im looking for",
    "looking for", "recommend", "suggest", "can you find", "what are",
    "what is", "tell me",
]

_FILLER = {
    "a", "an", "the", "of", "for", "please", "pls", "plz", "i", "me", "my",
    "want", "watch", "watching", "some", "any", "something", "anything",
    "good", "great", "nice", "cool", "and", "or", "with", "in", "on", "from",
    "that", "this", "is", "are", "was", "were", "be", "to", "it", "you",
    "recommendations", "recommendation", "recs", "suggestions", "suggestion",
    "released", "release", "came", "out", "made", "produced", "set",
    "please", "give", "show", "find", "get", "list", "top", "best", "about",
    "weekend", "tonight", "night", "today", "now", "then", "there", "here",
    "but", "not", "no", "dont", "don't", "like", "watchable", "stuff", "things",
}


def _mask(text: str, start: int, end: int) -> str:
    """Blank out a matched span while preserving string offsets."""
    return text[:start] + (" " * (end - start)) + text[end:]


def _is_negated(text: str, start: int) -> bool:
    """True if a negation cue appears just before the match."""
    window = text[max(0, start - 22):start]
    return any(cue in window for cue in NEGATION_CUES)


def _term_pattern(term: str) -> str:
    """Word-boundary pattern tolerant of hyphen/space variation."""
    return r"\b" + re.escape(term).replace(r"\ ", r"[\s\-]+") + r"\b"


def _extract_years(text: str) -> Tuple[Optional[int], Optional[int], List[Tuple[int, int]]]:
    """Return (year_from, year_to, spans_to_mask)."""
    spans: List[Tuple[int, int]] = []
    year_from = year_to = None

    m = re.search(r"\bbetween\s+(19\d{2}|20\d{2})\s+(?:and|to|-)\s+(19\d{2}|20\d{2})\b", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        spans.append(m.span())
        return min(a, b), max(a, b), spans

    m = re.search(r"\b(?:last|past)\s+(\d{1,2})\s+years?\b", text)
    if m:
        import datetime
        n = int(m.group(1))
        spans.append(m.span())
        return datetime.date.today().year - n, None, spans

    m = re.search(r"\b(after|since|from)\s+(19\d{2}|20\d{2})\b", text)
    if m:
        y = int(m.group(2))
        spans.append(m.span())
        return (y + 1 if m.group(1) == "after" else y), None, spans

    m = re.search(r"\b(before|until|up to|prior to)\s+(19\d{2}|20\d{2})\b", text)
    if m:
        y = int(m.group(2))
        spans.append(m.span())
        return None, (y - 1 if m.group(1) == "before" else y), spans

    years = [(int(mm.group(0)), mm.span()) for mm in re.finditer(r"\b(19\d{2}|20\d{2})\b", text)]
    if len(years) == 1:
        y, span = years[0]
        spans.append(span)
        return y, y, spans

    return year_from, year_to, spans


def parse_intent(text: str) -> Intent:
    raw = (text or "").strip()
    t = " " + re.sub(r"\s+", " ", raw.lower()) + " "

    intent = Intent()
    matched: List[Tuple[str, str]] = []

    # ---- 0) strip conversational lead-ins -------------------------------
    for lead in _LEAD_INS:
        for m in re.finditer(_term_pattern(lead), t):
            t = _mask(t, *m.span())

    # ---- 1) explicit result limit ("top 5") -----------------------------
    m = re.search(r"\b(?:top|best)\s+(\d{1,3})\b", t)
    if not m:
        m = re.search(r"\b(\d{1,3})\s+(?:movies|films|shows|series|recommendations|recs)\b", t)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 50:
            intent.limit = n
            matched.append(("limit", m.group(0).strip()))
        t = _mask(t, *m.span())

    # ---- 2) sort intent -------------------------------------------------
    for terms, sort_by, needs_floor in SORT_TERMS:
        hit = None
        for term in sorted(terms, key=len, reverse=True):
            mm = re.search(_term_pattern(term), t)
            if mm:
                hit = (term, mm)
                break
        if hit:
            term, mm = hit
            intent.sort_by = sort_by
            if needs_floor:
                intent.min_votes = RATING_SORT_VOTE_FLOOR
            matched.append(("sort", term))
            t = _mask(t, *mm.span())
            break

    # ---- 3) explicit rating floor ---------------------------------------
    m = re.search(r"\b(?:rating|rated|score)\s*(?:above|over|greater than|at least|>=?)\s*(\d(?:\.\d)?)\b", t)
    if not m:
        m = re.search(r"\b(\d(?:\.\d)?)\s*\+\s*(?:rating|rated|stars?)\b", t)
    if m:
        try:
            intent.min_rating = float(m.group(1))
            matched.append(("min_rating", m.group(0).strip()))
        except ValueError:
            pass
        t = _mask(t, *m.span())

    # ---- 4) moods (multi-word, before single-word genres) ---------------
    for term in sorted(MOOD_TERMS, key=len, reverse=True):
        mm = re.search(_term_pattern(term), t)
        if not mm:
            continue
        bucket = intent.exclude_genres if _is_negated(t, mm.start()) else intent.genres
        for gid in MOOD_TERMS[term]:
            if gid not in bucket:
                bucket.append(gid)
        matched.append(("mood", term))
        t = _mask(t, *mm.span())

    # ---- 5) genres ------------------------------------------------------
    for term in sorted(MOVIE_GENRES, key=len, reverse=True):
        mm = re.search(_term_pattern(term), t)
        if not mm:
            continue
        gid = MOVIE_GENRES[term]
        negated = _is_negated(t, mm.start())
        bucket = intent.exclude_genres if negated else intent.genres
        if gid not in bucket:
            bucket.append(gid)
        matched.append(("exclude_genre" if negated else "genre", term))
        # "anime" also implies Japanese; don't mask it away from the language pass
        if term != "anime":
            t = _mask(t, *mm.span())

    # ---- 6) thematic keywords -------------------------------------------
    for term in sorted(KEYWORD_TERMS, key=len, reverse=True):
        mm = re.search(_term_pattern(term), t)
        if mm and term not in intent.keywords:
            intent.keywords.append(term)
            matched.append(("keyword", term))
            t = _mask(t, *mm.span())

    # ---- 7) language ----------------------------------------------------
    for terms, code in LANG_HINTS:
        hit = None
        for term in sorted(terms, key=len, reverse=True):
            mm = re.search(_term_pattern(term), t)
            if mm:
                hit = (term, mm)
                break
        if hit:
            term, mm = hit
            intent.language = code
            matched.append(("language", term))
            t = _mask(t, *mm.span())
            break
    if intent.language is None and re.search(r"\banime\b", t):
        intent.language = "ja"
        matched.append(("language", "anime"))
    t = re.sub(r"\banime\b", "     ", t)

    # ---- 8) content type ------------------------------------------------
    for ctype, terms in CONTENT_HINTS.items():
        hit = None
        for term in sorted(terms, key=len, reverse=True):
            mm = re.search(_term_pattern(term), t)
            if mm:
                hit = (term, mm)
                break
        if hit:
            term, mm = hit
            intent.content_type = ctype
            matched.append(("content_type", term))
            t = _mask(t, *mm.span())
            break

    # ---- 9) decades and years -------------------------------------------
    for term in sorted(DECADES, key=len, reverse=True):
        mm = re.search(_term_pattern(term), t)
        if mm:
            intent.year_from, intent.year_to = DECADES[term]
            matched.append(("era", term))
            t = _mask(t, *mm.span())
            break
    if intent.year_from is None and intent.year_to is None:
        yf, yt, spans = _extract_years(t)
        intent.year_from, intent.year_to = yf, yt
        for s, e in spans:
            matched.append(("year", t[s:e].strip()))
            t = _mask(t, s, e)

    # ---- 10) runtime ----------------------------------------------------
    m = re.search(r"\bunder\s+(\d{1,3})\s*(?:min|mins|minutes)\b", t)
    if m:
        intent.runtime_lte = int(m.group(1))
        matched.append(("runtime", m.group(0).strip()))
        t = _mask(t, *m.span())

    # Qualitative runtime words are consumed either way, so an explicit
    # "under 100 minutes" does not leave a stray "short" in the residual.
    for terms, direction, minutes in RUNTIME_TERMS:
        mm = next((x for x in (re.search(_term_pattern(term), t) for term in terms) if x), None)
        if not mm:
            continue
        if intent.runtime_lte is None and intent.runtime_gte is None:
            if direction == "lte":
                intent.runtime_lte = minutes
            else:
                intent.runtime_gte = minutes
            matched.append(("runtime", mm.group(0).strip()))
        t = _mask(t, *mm.span())
        break

    # ---- 11) seed title ("like X") --------------------------------------
    m = re.search(r"(?<!don't )(?<!do not )(?<!not )\b(?:like|similar to|reminds me of)\b\s+(.+?)\s*$", t)
    if m:
        seed = re.sub(r"\b(?:on|from)\b.*$", "", m.group(1)).strip()
        seed = " ".join(w for w in seed.split() if w not in _FILLER)
        if seed:
            intent.seed_title = seed
            matched.append(("seed_title", seed))
        t = _mask(t, *m.span())

    # ---- 12) person role hint -------------------------------------------
    for terms, role in ROLE_TERMS:
        hit = None
        for term in sorted(terms, key=len, reverse=True):
            mm = re.search(_term_pattern(term), t)
            if mm:
                hit = (term, mm)
                break
        if hit:
            term, mm = hit
            intent.person_role = role
            matched.append(("role", term))
            t = _mask(t, *mm.span())
            break

    # ---- 13) residual ---------------------------------------------------
    # Negation cues have served their purpose (steps 4-5) and must not leak
    # into the residual, or "action but not horror" would search for "but not".
    for cue in NEGATION_CUES:
        for mm in re.finditer(_term_pattern(cue.strip()), t):
            t = _mask(t, *mm.span())

    # Strip only noisy punctuation. A \w whitelist would silently destroy
    # non-Latin scripts by dropping Unicode combining marks (मूवी -> म व).
    cleaned = re.sub(r"[<>{}\[\]()*;|\\/\"!?,+=#$%^~`]", " ", t)
    leftover = [
        w for w in cleaned.split()
        if w not in _FILLER and any(ch.isalnum() for ch in w)
    ]
    residual = " ".join(leftover).strip()
    if residual and not re.fullmatch(r"[\d\s\-.]+", residual):
        intent.residual = residual
        if intent.person_role:
            intent.person_name = residual

    intent.genres = list(dict.fromkeys(intent.genres))
    intent.exclude_genres = list(dict.fromkeys(intent.exclude_genres))
    # A genre cannot be both wanted and unwanted; explicit exclusion wins.
    intent.genres = [g for g in intent.genres if g not in intent.exclude_genres]
    intent.matched_terms = matched
    return intent
