# 🎬 MovieChat

Ask for films and series in plain English — *"highest rated korean thriller series from the 2010s but not romance"* — and get ranked results with posters, trailers and streaming availability.

The language understanding runs **entirely locally**. There is no LLM, no AI API key, and no per-query cost.

---

## Quick start

You need **Python 3.9+** and two free API keys (2 minutes to get, links below).

```bash
# 1. Clone and enter the project
git clone https://github.com/anrajput1210/Projects.git
cd Projects/moviechatAI

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Add your API keys (see below), then start it
uvicorn src.api.app:app --reload
```

Open **<http://localhost:8000>** — that's the whole app.

---

## API keys

Create a file named `.env` inside the `moviechatAI/` folder:

```ini
TMDB_API_KEY=your_tmdb_key_here
WATCHMODE_API_KEY=your_watchmode_key_here
DEFAULT_REGION=US
```

| Key | Where to get it | Needed for |
| --- | --- | --- |
| `TMDB_API_KEY` | [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) | **Required** — all film and series data |
| `WATCHMODE_API_KEY` | [api.watchmode.com](https://api.watchmode.com/) | Optional — the "streaming on…" line |
| `DEFAULT_REGION` | — | Streaming region, defaults to `US` |

> **Use the TMDB *API Key*, not the Read Access Token.** The short v3 key, not the long JWT — this project authenticates via query parameter.

`.env` is git-ignored. **Never commit it.**

---

## What you can ask for

| You type | It understands |
| --- | --- |
| `highest rated horror movies` | sort by rating, with a vote-count floor so one-vote titles can't win |
| `korean thriller series from the 2010s` | language + genre + content type + era |
| `action movies but not horror` | includes action, **excludes** horror |
| `movies directed by christopher nolan` | person + role, returns his filmography |
| `feel good movies` | mood → comedy + family |
| `series like squid game` | finds the show, then returns similar ones |
| `top 5 heist movies` | theme keyword + result limit |
| `short sci-fi under 100 minutes with rating above 8` | runtime + minimum rating |

Also supported: `newest` / `oldest` / `most popular`, decades (`90s`, `2000s`), `between 2010 and 2015`, `after 2015`, and languages from Hindi to Telugu.

Anything the engine can't explain is treated as a title or a person's name and looked up directly.

---

## Endpoints

| Route | Purpose |
| --- | --- |
| `/` | The web app |
| `POST /ai` | JSON API |
| `/docs` | Interactive API documentation |
| `/health` | Liveness check |

<details>
<summary>Example API request</summary>

```bash
curl -X POST http://localhost:8000/ai \
  -H "Content-Type: application/json" \
  -d '{"text":"highest rated horror movies","page":1,"page_size":5}'
```

| Field | Type | Notes |
| --- | --- | --- |
| `text` | string | **required** — the natural-language request |
| `page` | int | ≥ 1, default `1` |
| `page_size` | int | 1–50, default `10` |
| `content_type` | string | `movie` or `series`, overrides the text |
| `language` | string | ISO 639-1 (`en`, `hi`, `ko`…), overrides the text |
| `sort_by` | string | `vote_average.desc`, `primary_release_date.desc`, `popularity.desc`, … |

</details>

---

## Project layout

```
moviechatAI/
├── web/index.html          # the web app — single file, no build step
├── src/
│   ├── api/app.py          # FastAPI: serves the app and the JSON API
│   └── core/
│       ├── vocabulary.py   # genres, moods, sort terms, eras, TMDB quirks
│       ├── ai_intent.py    # the natural-language intent engine
│       ├── providers.py    # TMDB + Watchmode clients
│       └── recommender.py  # routing, ranking, result assembly
├── ui_streamlit.py         # optional alternate front end
├── notebooks/              # early exploration
└── requirements.txt
```

---

## How the engine works

Film search is a **closed domain** — a finite set of genres, languages, sort modes and eras. That makes it solvable without a language model, provided the domain knowledge is written down.

`ai_intent.py` is a **token-consuming parser**. Each stage matches its vocabulary against the query and *masks the words it claimed*, so later stages can never re-read them. Whatever text survives every stage is, by elimination, a person or a title — resolved with a single TMDB lookup.

That is what stops `highest rated horror movies` from being read as a person named *"highest rated horror"*: the sort, genre and type stages consume every word, leaving nothing behind.

### Three TMDB traps, handled centrally

Each of these silently returns wrong or empty results if you don't know about it:

1. **Films and series use different genre-ID namespaces.** Sending a film genre ID to `/discover/tv` returns *zero* results — not an error. `to_tv_genres()` translates them.

2. **Sorting by rating without a vote floor returns garbage** — titles rated 10.0 from a single vote. Rating sorts apply a minimum vote count; "newest" applies a smaller one plus a cap at today's date, so unreleased films don't lead.

3. **A person's credits include every cameo and talk-show appearance.** The tempting fix — dropping credits by billing order or missing character name — deletes real leading roles: Morgan Freeman is billed *11th* as Lucius Fox in *Batman Begins*, and Scarlett Johansson is billed *0th* in *Under the Skin* with no character name at all. So nothing is deleted; credits are **ranked** by notability × billing prominence, which sinks a walk-on part without ever losing a film someone actually led.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `TMDB_API_KEY not found` | Create `.env` in `moviechatAI/` (not the repo root) |
| `401` from TMDB | You used the Read Access Token — use the short v3 **API Key** |
| Streaming line always "unknown" | `WATCHMODE_API_KEY` missing, or its free monthly quota is spent |
| Port 8000 already in use | `uvicorn src.api.app:app --reload --port 8001` |
| `uvicorn: command not found` | Activate the virtual environment first (step 3) |

---

## Optional: the Streamlit front end

An earlier Streamlit interface is kept in the repo. Start the backend first, then:

```bash
MOVIECHAT_API_URL=http://localhost:8000 streamlit run ui_streamlit.py
```

---

Data from [TMDB](https://www.themoviedb.org/) and [Watchmode](https://www.watchmode.com/). This product uses the TMDB API but is not endorsed or certified by TMDB.
