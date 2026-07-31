"""Domain lexicons for the MovieChat intent engine.

Movie search is a *closed domain*: a finite set of genres, languages, sort
modes, eras and themes. That makes it tractable without a language model —
but only if the vocabulary is explicit and the TMDB quirks are encoded here
rather than rediscovered at every call site.
"""

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Genres
# ---------------------------------------------------------------------------
# TMDB uses two disjoint genre-id namespaces. Sending a movie id to the TV
# discover endpoint silently returns zero results, so every TV query must go
# through TV_GENRE_MAP below.

MOVIE_GENRES: Dict[str, int] = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "anime": 16,
    "cartoon": 16,
    "comedy": 35,
    "comedies": 35,
    "funny": 35,
    "hilarious": 35,
    "crime": 80,
    "documentary": 99,
    "documentaries": 99,
    "docu": 99,
    "drama": 18,
    "dramas": 18,
    "family": 10751,
    "kids": 10751,
    "children": 10751,
    "fantasy": 14,
    "history": 36,
    "historical": 36,
    "horror": 27,
    "scary": 27,
    "spooky": 27,
    "music": 10402,
    "musical": 10402,
    "mystery": 9648,
    "romance": 10749,
    "romantic": 10749,
    "sci fi": 878,
    "sci-fi": 878,
    "scifi": 878,
    "science fiction": 878,
    "thriller": 53,
    "thrillers": 53,
    "war": 10752,
    "western": 37,
    "westerns": 37,
}

# Movie genre id -> nearest TV genre id. Genres with no TV counterpart map to
# None and are dropped for series queries (dropping beats returning nothing).
TV_GENRE_MAP: Dict[int, Optional[int]] = {
    28: 10759,      # Action          -> Action & Adventure
    12: 10759,      # Adventure       -> Action & Adventure
    878: 10765,     # Science Fiction -> Sci-Fi & Fantasy
    14: 10765,      # Fantasy         -> Sci-Fi & Fantasy
    10752: 10768,   # War             -> War & Politics
    53: 9648,       # Thriller        -> Mystery (closest available)
    27: 9648,       # Horror          -> Mystery (no TV horror genre)
    16: 16,         # Animation
    35: 35,         # Comedy
    80: 80,         # Crime
    99: 99,         # Documentary
    18: 18,         # Drama
    10751: 10751,   # Family
    9648: 9648,     # Mystery
    37: 37,         # Western
    36: None,       # History   -> no TV equivalent
    10402: None,    # Music     -> no TV equivalent
    10749: None,    # Romance   -> no TV equivalent
}


def to_tv_genres(movie_genre_ids: List[int]) -> List[int]:
    """Translate movie genre ids into TV genre ids, dropping unmappable ones."""
    out: List[int] = []
    for gid in movie_genre_ids:
        mapped = TV_GENRE_MAP.get(gid, gid)
        if mapped is not None and mapped not in out:
            out.append(mapped)
    return out


# ---------------------------------------------------------------------------
# Moods / vibes -> genre ids (movie namespace; translated for TV downstream)
# ---------------------------------------------------------------------------
MOOD_TERMS: Dict[str, List[int]] = {
    "feel good": [35, 10751],
    "feelgood": [35, 10751],
    "feel-good": [35, 10751],
    "wholesome": [10751, 35],
    "cozy": [10751, 35],
    "light hearted": [35],
    "lighthearted": [35],
    "mind bending": [878, 9648, 53],
    "mindbending": [878, 9648, 53],
    "mind blowing": [878, 9648],
    "thought provoking": [18, 878],
    "edge of your seat": [53],
    "edge of the seat": [53],
    "suspenseful": [53, 9648],
    "tear jerker": [18],
    "tearjerker": [18],
    "emotional": [18],
    "heartbreaking": [18],
    "sad": [18],
    "dark": [80, 53],
    "gritty": [80, 53],
    "violent": [28, 80],
    "romcom": [35, 10749],
    "rom com": [35, 10749],
    "rom-com": [35, 10749],
    "date night": [10749, 35],
    "superhero": [28, 12, 878],
    "coming of age": [18],
    "based on a true story": [18, 36],
    "true story": [18, 36],
    "binge worthy": [18, 53],
}

# ---------------------------------------------------------------------------
# Sort intents -> (TMDB sort_by, needs_vote_floor)
# ---------------------------------------------------------------------------
# TMDB's vote_average.desc is unusable without a vote-count floor: it surfaces
# obscure titles with a single 10/10 vote. needs_vote_floor forces that guard.
SORT_TERMS: List[Tuple[List[str], str, bool]] = [
    (["highest rated", "highest-rated", "best rated", "top rated", "top-rated",
      "best reviewed", "critically acclaimed", "acclaimed", "greatest",
      "must watch", "must-watch", "best"], "vote_average.desc", True),
    (["worst rated", "lowest rated", "worst"], "vote_average.asc", True),
    (["newest", "latest", "most recent", "just released", "brand new"],
     "primary_release_date.desc", False),
    (["oldest", "classic", "classics", "old school"], "primary_release_date.asc", False),
    (["most popular", "popular", "trending", "buzzing"], "popularity.desc", False),
    (["highest grossing", "biggest", "blockbuster", "blockbusters", "box office"],
     "revenue.desc", False),
]

# Minimum votes required before a title can rank on rating alone.
RATING_SORT_VOTE_FLOOR = 300

# "Newest first" has the same failure mode in a milder form: without a floor
# it returns everything uploaded to TMDB today, most of which no one has
# heard of. A modest floor keeps genuinely released, distributed titles.
RECENCY_SORT_VOTE_FLOOR = 50

# ---------------------------------------------------------------------------
# Thematic keywords -> resolved to TMDB keyword ids at query time
# ---------------------------------------------------------------------------
KEYWORD_TERMS: List[str] = [
    "heist", "zombie", "time travel", "revenge", "vampire", "werewolf",
    "apocalypse", "post apocalyptic", "dystopia", "serial killer", "courtroom",
    "whodunit", "spy", "espionage", "robot", "alien", "dinosaur", "pirate",
    "samurai", "martial arts", "kung fu", "boxing", "survival", "haunted house",
    "ghost", "witch", "demon", "exorcism", "cult", "conspiracy", "prison",
    "escape", "submarine", "space", "mars", "virus", "pandemic", "hacker",
    "mafia", "gangster", "cartel", "assassin", "treasure", "road trip",
    "wedding", "heist crew", "found footage", "body swap", "artificial intelligence",
]

# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
LANG_HINTS: List[Tuple[List[str], str]] = [
    (["hindi", "bollywood"], "hi"),
    (["english", "hollywood"], "en"),
    (["korean", "k-drama", "kdrama"], "ko"),
    (["japanese", "anime"], "ja"),
    (["spanish"], "es"),
    (["french"], "fr"),
    (["german"], "de"),
    (["italian"], "it"),
    (["chinese", "mandarin"], "zh"),
    (["tamil"], "ta"),
    (["telugu"], "te"),
    (["malayalam"], "ml"),
    (["punjabi"], "pa"),
    (["bengali"], "bn"),
    (["marathi"], "mr"),
]

# ---------------------------------------------------------------------------
# Content type
# ---------------------------------------------------------------------------
CONTENT_HINTS: Dict[str, List[str]] = {
    "series": ["series", "tv show", "tv shows", "tv", "show", "shows",
               "web series", "episodes", "season", "seasons", "sitcom",
               "k-drama", "kdrama", "miniseries", "anime series"],
    "movie": ["movies", "movie", "films", "film", "cinema", "flick", "flicks"],
}

# ---------------------------------------------------------------------------
# Person roles
# ---------------------------------------------------------------------------
ROLE_TERMS: List[Tuple[List[str], str]] = [
    (["directed by", "director", "from the director of"], "director"),
    (["written by", "writer", "screenwriter"], "writer"),
    # "with" is deliberately excluded — too generic ("movies with rating above 8")
    (["starring", "actor", "actress", "featuring"], "actor"),
]

# ---------------------------------------------------------------------------
# Negation cues — text after these excludes rather than includes
# ---------------------------------------------------------------------------
NEGATION_CUES: List[str] = [
    "but not", "except", "excluding", "without", "no ", "not ",
    "don't like", "dont like", "do not like", "avoid", "hate",
]

# ---------------------------------------------------------------------------
# Person-credit quality filters
# ---------------------------------------------------------------------------
# TMDB returns every credit a person has, from starring roles to one-scene
# cameos. The instinct is to delete the cameos, but that is a trap: billing
# order is unreliable (Morgan Freeman is billed 11th as Lucius Fox in Batman
# Begins) and character names are often missing entirely (Scarlett Johansson
# is billed 0th in Under the Skin with no character string). Deleting on
# those signals destroys real leading roles.
#
# So almost nothing is deleted. Credits are RANKED by notability x billing
# prominence, which pushes a bit part in a well-reviewed film far down the
# list without ever losing a film the person actually led.

# Billing position -> how prominent the role is. Deliberately gentle: even
# the lowest tier stays in the list, it just needs far more notability to
# surface.
BILLING_PROMINENCE = (
    (2, 1.00),    # top billing
    (5, 0.85),    # main cast
    (10, 0.65),   # significant supporting
    (20, 0.40),   # minor supporting
)
BILLING_PROMINENCE_FLOOR = 0.20      # beyond the tiers above
BILLING_PROMINENCE_UNKNOWN = 0.50    # no `order` field at all

# The only credits worth removing outright: ones nobody ever means.
DISCARD_CHARACTER_PATTERNS = (
    r"\barchive footage\b",
    r"\buncredited\b",
)

# Vote floor for rating-based sorts, so a film with a handful of votes cannot
# top the list on average score alone.
MIN_CREDIT_VOTES = 300

# Minimum prominence for a credit to compete in an explicit rating sort.
MIN_SORT_PROMINENCE = 0.40

# ---------------------------------------------------------------------------
# Era shortcuts
# ---------------------------------------------------------------------------
DECADES: Dict[str, Tuple[int, int]] = {
    "20s": (2020, 2029),
    "2020s": (2020, 2029),
    "10s": (2010, 2019),
    "2010s": (2010, 2019),
    "00s": (2000, 2009),
    "2000s": (2000, 2009),
    "noughties": (2000, 2009),
    "90s": (1990, 1999),
    "1990s": (1990, 1999),
    "nineties": (1990, 1999),
    "80s": (1980, 1989),
    "1980s": (1980, 1989),
    "eighties": (1980, 1989),
    "70s": (1970, 1979),
    "1970s": (1970, 1979),
    "seventies": (1970, 1979),
    "60s": (1960, 1969),
    "1960s": (1960, 1969),
    "sixties": (1960, 1969),
    "50s": (1950, 1959),
    "1950s": (1950, 1959),
}

# ---------------------------------------------------------------------------
# Runtime shortcuts (minutes)
# ---------------------------------------------------------------------------
RUNTIME_TERMS: List[Tuple[List[str], str, int]] = [
    (["short", "quick", "under 90 minutes"], "lte", 90),
    (["long", "epic", "lengthy"], "gte", 150),
]
