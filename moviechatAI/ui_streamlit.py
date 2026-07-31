import os

import requests
import streamlit as st

API_URL = os.getenv("MOVIECHAT_API_URL", "https://moviechatai-backend.onrender.com").rstrip("/")

st.set_page_config(page_title="MovieChat AI", page_icon="🎬", layout="wide")

# ----------------------------------------------------------------------------
# Brand theme (dark, cinematic). Complements .streamlit/config.toml, which
# sets the base Streamlit theme colors for native widgets (buttons, sliders).
# ----------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0b0f19;
    --surface: #12172440;
    --surface-2: #1b2233;
    --border: rgba(255,255,255,0.08);
    --text-muted: #97a1b3;
    --brand-1: #8b5cf6;
    --brand-2: #ec4899;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #ef4444;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }

.stApp {
    background:
        radial-gradient(1200px 500px at 15% -10%, rgba(139,92,246,0.16), transparent 60%),
        radial-gradient(900px 500px at 100% 0%, rgba(236,72,153,0.10), transparent 55%),
        var(--bg);
}

/* Hero */
.mc-hero { padding: 0.5rem 0 0.25rem; }
.mc-hero .mc-brand {
    display: inline-flex; align-items: center; gap: 0.6rem;
    font-size: 2.3rem; font-weight: 800; letter-spacing: -0.02em;
    color: #f4f4f6;
}
.mc-hero .mc-brand .mc-logo {
    display: inline-flex; align-items: center; justify-content: center;
    width: 48px; height: 48px; border-radius: 14px; font-size: 1.5rem;
    background: linear-gradient(135deg, var(--brand-1), var(--brand-2));
    box-shadow: 0 8px 24px rgba(139,92,246,0.35);
}
.mc-hero .mc-brand .mc-gradient {
    background: linear-gradient(135deg, #ffffff, #c9c9ff);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.mc-hero .mc-tagline { color: var(--text-muted); font-size: 0.98rem; margin: 0.4rem 0 0; }
.mc-pill-row { display: flex; gap: 8px; margin: 0.9rem 0 1.4rem; flex-wrap: wrap; }
.mc-pill {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.02em;
    color: var(--text-muted); background: var(--surface-2);
    border: 1px solid var(--border); padding: 4px 12px; border-radius: 999px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1220; border-right: 1px solid var(--border);
}
.mc-sidebar-title {
    font-weight: 700; font-size: 1.0rem; letter-spacing: 0.01em;
    display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.6rem;
}

/* Buttons */
.stButton button {
    border-radius: 10px !important; font-weight: 600 !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.stButton button:hover { transform: translateY(-1px); }
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-1), var(--brand-2)) !important;
    border: none !important; box-shadow: 0 6px 18px rgba(139,92,246,0.35);
}

/* Text input */
.stTextInput input {
    border-radius: 10px !important; background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
}

/* Intent / status bar */
.mc-intent {
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: 12px; padding: 10px 14px; margin: 1rem 0 1.4rem;
}
.mc-intent .mc-intent-label { color: var(--text-muted); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; margin-right: 4px; }
.mc-chip {
    font-size: 0.78rem; font-weight: 600; color: #e5e7eb;
    background: #232b40; border: 1px solid var(--border);
    padding: 3px 11px; border-radius: 999px;
}
/* Chips colour-coded by what the engine matched, so the parse is legible */
.mc-chip--genre   { background: rgba(139,92,246,0.18); border-color: rgba(139,92,246,0.45); color: #d6c7ff; }
.mc-chip--mood    { background: rgba(236,72,153,0.16); border-color: rgba(236,72,153,0.42); color: #fbc7e4; }
.mc-chip--sort    { background: rgba(245,158,11,0.16); border-color: rgba(245,158,11,0.42); color: #fcd9a0; }
.mc-chip--era     { background: rgba(59,130,246,0.16); border-color: rgba(59,130,246,0.42); color: #bcd7ff; }
.mc-chip--year    { background: rgba(59,130,246,0.16); border-color: rgba(59,130,246,0.42); color: #bcd7ff; }
.mc-chip--language{ background: rgba(34,197,94,0.15);  border-color: rgba(34,197,94,0.40); color: #b7f0cd; }
.mc-chip--keyword { background: rgba(99,102,241,0.16); border-color: rgba(99,102,241,0.42); color: #c7cbff; }
.mc-chip--exclude_genre { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.42); color: #ffc2c2; text-decoration: line-through; }
.mc-chip--role, .mc-chip--seed_title { background: rgba(148,163,184,0.16); border-color: rgba(148,163,184,0.40); color: #dbe3ee; }

.mc-exact {
    display: inline-block; font-size: 0.66rem; font-weight: 800; letter-spacing: 0.05em;
    background: linear-gradient(135deg, var(--brand-1), var(--brand-2)); color: #fff;
    padding: 2px 9px; border-radius: 999px; margin-bottom: 4px;
}

/* Result cards */
div[class*="st-key-mc-card-"] {
    background: var(--surface); border: 1px solid var(--border) !important;
    border-radius: 16px !important; padding: 4px !important;
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
div[class*="st-key-mc-card-"]:hover {
    transform: translateY(-3px);
    border-color: rgba(139,92,246,0.45) !important;
    box-shadow: 0 14px 32px rgba(0,0,0,0.35);
}
div[class*="st-key-mc-card-"] img {
    border-radius: 12px !important;
}

.mc-title { font-size: 1.15rem; font-weight: 700; margin: 0.2rem 0 0.35rem; line-height: 1.3; }
.mc-overview {
    color: var(--text-muted); font-size: 0.88rem; line-height: 1.45;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden; min-height: 3.9em; margin-bottom: 0.55rem;
}
.mc-chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 0.5rem; }
.mc-chip-row .mc-chip { background: var(--surface-2); }

.mc-score-row { display: flex; align-items: center; gap: 10px; margin: 0.3rem 0 0.6rem; }
.mc-score-track { flex: 1; height: 8px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }
.mc-score-fill { height: 100%; border-radius: 999px; }
.mc-score-fill.tier-great { background: linear-gradient(90deg, #22c55e, #4ade80); }
.mc-score-fill.tier-good  { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.mc-score-fill.tier-weak  { background: linear-gradient(90deg, #ef4444, #f87171); }
.mc-score-label { font-size: 0.78rem; font-weight: 700; white-space: nowrap; min-width: 62px; text-align: right; }

.mc-avail { font-size: 0.85rem; margin: 0.2rem 0 0.4rem; }
.mc-avail b { color: #e5e7eb; }
.mc-meta { color: var(--text-muted); font-size: 0.78rem; margin-bottom: 0.3rem; }

.mc-empty {
    text-align: center; padding: 3rem 1rem; color: var(--text-muted);
    border: 1px dashed var(--border); border-radius: 16px; background: var(--surface);
}
.mc-empty .mc-empty-icon { font-size: 2.4rem; margin-bottom: 0.6rem; }

.mc-footer { text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 1.5rem 0 0.5rem; }
</style>
""",
    unsafe_allow_html=True,
)

_DEFAULTS = {
    "results": [],
    "page": 0,
    "last_query": None,
    "last_content_type": None,
    "last_language": None,
    "intent": {},
    "error": None,
}
for _key, _val in _DEFAULTS.items():
    st.session_state.setdefault(_key, _val)

CONTENT_TYPES = {"Any": None, "Movie": "movie", "Series": "series"}
LANGUAGES = {
    "Any": None,
    "English": "en",
    "Hindi": "hi",
    "Korean": "ko",
    "Japanese": "ja",
    "Spanish": "es",
    "French": "fr",
    "Tamil": "ta",
    "Telugu": "te",
}

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="mc-sidebar-title">🎛️ Filters</div>', unsafe_allow_html=True)
    content_type = CONTENT_TYPES[st.selectbox("Type", list(CONTENT_TYPES.keys()))]
    language = LANGUAGES[st.selectbox("Language", list(LANGUAGES.keys()))]
    page_size = st.slider("Results per page", 5, 20, 10)
    st.divider()
    st.caption(f"🔌 Backend\n\n`{API_URL}`")

# ----------------------------------------------------------------------------
# Hero
# ----------------------------------------------------------------------------
st.markdown(
    """
<div class="mc-hero">
    <div class="mc-brand">
        <span class="mc-logo">🎬</span>
        <span class="mc-gradient">MovieChat AI</span>
    </div>
    <p class="mc-tagline">Describe what you're in the mood for — genre, mood, era, language, a director, or "like X" — and get ranked picks in seconds.</p>
    <div class="mc-pill-row">
        <span class="mc-pill">⚡ REAL-TIME TMDB DATA</span>
        <span class="mc-pill">📺 STREAMING AVAILABILITY</span>
        <span class="mc-pill">🧠 NATURAL-LANGUAGE ENGINE</span>
        <span class="mc-pill">🎯 SMART MATCH SCORING</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

text = st.text_input("What do you want to watch?", value="hindi comedy movies released after 2015")

col_search, col_more, col_clear = st.columns([1, 1, 1])


def fetch(page: int) -> dict:
    payload = {
        "text": text,
        "page": page,
        "page_size": page_size,
        "content_type": content_type,
        "language": language,
    }
    r = requests.post(f"{API_URL}/ai", json=payload, timeout=90)
    r.raise_for_status()
    return r.json()


def run_search(reset: bool) -> None:
    if not text.strip():
        st.session_state.error = "Please enter what you'd like to watch."
        return

    st.session_state.page = 1 if reset else st.session_state.page + 1
    if reset:
        st.session_state.results = []

    try:
        with st.spinner("Finding great picks..."):
            data = fetch(st.session_state.page)
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        st.session_state.error = f"Request failed: {detail or e}"
        return
    except requests.exceptions.RequestException as e:
        st.session_state.error = f"Could not reach the MovieChat backend: {e}"
        return

    st.session_state.error = None
    st.session_state.last_query = text
    st.session_state.last_content_type = content_type
    st.session_state.last_language = language
    st.session_state.results.extend(data.get("items", []))
    st.session_state.intent = data.get("intent", {})


filters_changed = (
    st.session_state.last_query != text
    or st.session_state.last_content_type != content_type
    or st.session_state.last_language != language
)

with col_search:
    if st.button("Search", type="primary", icon=":material/search:", width="stretch"):
        run_search(reset=True)

with col_more:
    load_more_disabled = not st.session_state.results and not filters_changed
    if st.button("Load more", icon=":material/expand_more:", disabled=load_more_disabled, width="stretch"):
        run_search(reset=filters_changed or not st.session_state.results)

with col_clear:
    if st.button("Clear", icon=":material/close:", width="stretch"):
        st.session_state.results = []
        st.session_state.page = 0
        st.session_state.last_query = None
        st.session_state.last_content_type = None
        st.session_state.last_language = None
        st.session_state.intent = {}
        st.session_state.error = None

if st.session_state.error:
    st.error(st.session_state.error, icon=":material/error:")

# ----------------------------------------------------------------------------
# Understood-intent chip bar
# ----------------------------------------------------------------------------
_SORT_LABELS = {
    "vote_average.desc": "highest rated",
    "vote_average.asc": "lowest rated",
    "primary_release_date.desc": "newest first",
    "primary_release_date.asc": "oldest first",
    "popularity.desc": "most popular",
    "revenue.desc": "highest grossing",
}
_KIND_ICONS = {
    "genre": "🎭", "mood": "✨", "sort": "↕️", "era": "📅", "year": "📅",
    "language": "🌐", "keyword": "🔖", "exclude_genre": "🚫", "role": "🎬",
    "seed_title": "🔗", "content_type": "🎞️", "limit": "#", "runtime": "⏱️",
    "min_rating": "⭐",
}

intent = st.session_state.get("intent", {})
if intent:
    chips = []
    for mt in intent.get("matched_terms", []):
        kind, term = mt.get("kind", ""), mt.get("term", "")
        icon = _KIND_ICONS.get(kind, "•")
        chips.append(f'<span class="mc-chip mc-chip--{kind}">{icon} {term}</span>')

    # Derived facts the raw terms don't state outright.
    if intent.get("person_name"):
        role = intent.get("person_role") or "person"
        chips.append(f'<span class="mc-chip mc-chip--role">🎬 {intent["person_name"]} ({role})</span>')
    if intent.get("min_votes"):
        chips.append(f'<span class="mc-chip mc-chip--sort">🛡️ min {intent["min_votes"]} votes</span>')

    # Only synthesise a sort chip when no literal sort term was matched,
    # otherwise the same thing is shown twice.
    sort_label = _SORT_LABELS.get(intent.get("sort_by") or "")
    already_shown = any(m.get("kind") == "sort" for m in intent.get("matched_terms", []))
    summary = (
        f'<span class="mc-chip mc-chip--sort">↕️ {sort_label}</span>'
        if sort_label and not already_shown else ""
    )

    if not chips:
        chips.append('<span class="mc-chip">free-text search</span>')

    st.markdown(
        f'<div class="mc-intent"><span class="mc-intent-label">Understood</span>'
        f'{summary}{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )

if not st.session_state.results and st.session_state.last_query and not st.session_state.error:
    st.markdown(
        """
<div class="mc-empty">
    <div class="mc-empty-icon">🔍</div>
    <div><b>No results found</b></div>
    <div>Try a broader description, or remove a filter.</div>
</div>
""",
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# Results grid
# ----------------------------------------------------------------------------
if st.session_state.results:
    st.caption(f"Showing {len(st.session_state.results)} result{'s' if len(st.session_state.results) != 1 else ''}")

    grid_cols = st.columns(2)
    for i, item in enumerate(st.session_state.results, 1):
        col = grid_cols[(i - 1) % 2]
        with col:
            with st.container(key=f"mc-card-{item.get('tmdb_id')}-{i}", border=True):
                inner = st.columns([1, 1.6])

                with inner[0]:
                    if item.get("poster_url"):
                        st.image(item["poster_url"], width="stretch")
                    else:
                        st.markdown(
                            '<div style="aspect-ratio:2/3;display:flex;align-items:center;'
                            'justify-content:center;background:var(--surface-2);border-radius:12px;'
                            'font-size:2rem;">🎞️</div>',
                            unsafe_allow_html=True,
                        )

                with inner[1]:
                    score = item.get("score") or 0
                    tier = "great" if score >= 70 else ("good" if score >= 45 else "weak")
                    type_icon = "🎬" if item.get("type") == "movie" else "📺"
                    date = item.get("release_date") if item.get("type") == "movie" else item.get("first_air_date")
                    avail = item.get("available_on")

                    if item.get("is_exact_match"):
                        st.markdown('<span class="mc-exact">EXACT MATCH</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="mc-title">{i}. {item.get("title")}</div>', unsafe_allow_html=True)
                    st.markdown(
                        f"""<div class="mc-chip-row">
    <span class="mc-chip">{type_icon} {(item.get('type') or '').title()}</span>
    <span class="mc-chip">🌐 {(item.get('language') or '—').upper()}</span>
    <span class="mc-chip">⭐ {item.get('rating') or '—'}/10</span>
</div>""",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="mc-overview">{item.get("overview") or "No synopsis available."}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""<div class="mc-score-row">
    <div class="mc-score-track"><div class="mc-score-fill tier-{tier}" style="width:{max(0, min(score, 100))}%"></div></div>
    <span class="mc-score-label">{score}/100</span>
</div>""",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="mc-avail">📺 Available on: <b>{avail}</b></div>'
                        if avail
                        else '<div class="mc-avail">📺 Available on: <i>Unknown</i></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f'<div class="mc-meta">Release: {date or "Unknown"}</div>', unsafe_allow_html=True)

                    trailer = item.get("trailer_url")
                    if trailer:
                        with st.expander("▶ Watch trailer"):
                            st.video(trailer)

st.markdown(
    '<div class="mc-footer">Data via TMDB &amp; Watchmode · Built with Streamlit + FastAPI</div>',
    unsafe_allow_html=True,
)
