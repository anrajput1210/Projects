# DJ Track Sorter

Free web app that auto-sorts a DJ's playlist by musical key (Camelot Wheel)
and BPM compatibility, and lets them export a mix-ready order back out as
Rekordbox XML or M3U.

## Status: feature-complete

- [x] Upload raw audio (MP3/WAV/FLAC), analyzed for BPM + key with librosa —
      no cap on track count, up to 5GB/track
- [x] BPM detection (`librosa.beat.beat_track`)
- [x] Key detection (chroma features + Krumhansl-Schmuckler profile
      correlation → Camelot notation)
- [x] Rekordbox XML import (uses existing `AverageBpm`/`Tonality` tags
      instead of re-analyzing)
- [x] Serato crate import (track list; flags tracks needing audio re-upload
      for analysis, since crates don't carry BPM/key)
- [x] Compatibility graph + nearest-neighbor sort — a single sort that
      weighs Camelot key compatibility and BPM closeness together, the way
      a DJ actually picks the next track
- [x] Camelot-color-coded playlist table in the UI, with per-transition mix
      scores
- [x] Export sorted playlist as Rekordbox XML or M3U

## How the analysis works

- **BPM:** `librosa.beat.beat_track` on a mono 22.05kHz load of the track.
- **Key:** average chroma vector (`librosa.feature.chroma_cqt`) correlated
  against all 12 rotations of the major and minor Krumhansl-Schmuckler
  key-profiles (a classic music-cognition key-finding method); best
  correlation wins. Returns a confidence score (0-1) alongside the key.
- **Camelot conversion:** pitch class + mode → Camelot code via a fixed
  lookup table ([backend/app/camelot.py](backend/app/camelot.py)), matching
  the standard 12×(A/B) wheel DJ software uses.
- We deliberately don't use essentia: it has poor/no prebuilt wheels on
  Windows or on free-tier Linux hosts, which would turn `pip install` into a
  slow source build or an outright failure. librosa covers both BPM and key
  with pure NumPy/SciPy, keeping the whole stack `pip install`-able for free.
- **Accuracy caveat:** this is a heuristic, not ground truth. It performs
  well on tonally clear, rhythmically steady tracks; expect occasional misses
  on ambient, atonal, or heavily-effected material — same limitation any
  automated key/BPM detector has (including the ones built into Rekordbox
  and Serato, which is exactly why we prefer their tags over re-analyzing
  when they're available).

## How sorting works

Tracks are nodes in a compatibility graph; the edge weight between any two
tracks combines:

- **Key score** (60% weight): 1.0 same key, 0.9 relative major/minor, 0.8
  adjacent Camelot number, 0.5 adjacent + mode switch, 0.1 otherwise.
- **BPM score** (40% weight): scales from 1.0 (identical) down to 0 at the
  edge of a 6% tolerance band; also credits half-time/double-time matches
  (e.g. 174 vs 87 BPM) at a reduced weight, a common real DJ move.

The sort walks this graph with a nearest-neighbor greedy heuristic: start
from the lowest-BPM track, then repeatedly jump to whichever remaining
track mixes best with the current last track — never picking on key alone
or BPM alone. It's O(n²) and not a guaranteed-optimal TSP solve, but for
realistic playlist sizes it produces a genuinely playable order, not just
tracks bucketed by identical key or a plain BPM sort that ignores harmony.

See [backend/app/compatibility.py](backend/app/compatibility.py) for the
exact scoring.

## Analysis speed

Two changes keep upload-to-result time down:

- **Bounded analysis window:** BPM and key stay effectively constant through
  most of a DJ track, so we only decode and analyze the first 60 seconds
  (`ANALYSIS_DURATION_SEC` in [analysis.py](backend/app/analysis.py))
  instead of the whole file — the track's *reported* duration still comes
  from a fast metadata read of the full file, only the analysis itself is
  truncated. Measured on a 4-minute synthetic track: 2.66s → 0.76s, a ~3.5x
  cut, and it scales further with track length (a 6-minute track sees a
  bigger win than a 3-minute one).
- **Concurrent analysis across a batch:** when multiple tracks are uploaded
  together, up to `ANALYSIS_CONCURRENCY` (default: `min(cpu_count, 4)`) are
  analyzed at once on worker threads instead of one at a time. This helps
  less than the duration cap — some of librosa's internals (numba-jitted
  code paths) hold Python's GIL, so it's not a clean N-way speedup — but it
  measurably helps (4 tracks: 5.18s sequential → 3.99s concurrent in
  testing). Override via the `ANALYSIS_CONCURRENCY` env var; lower it on a
  constrained free-tier host if uploads feel worse under load, raise it on
  a beefier machine.

## Project structure

```
DJ-track-sorter/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, all routes
│   │   ├── models.py                  # Pydantic schemas (Track, requests/responses)
│   │   ├── analysis.py                # librosa BPM + key detection
│   │   ├── camelot.py                 # Camelot Wheel conversion + key-string parsing
│   │   ├── compatibility.py           # compatibility graph + sort modes
│   │   ├── importers/
│   │   │   ├── rekordbox_xml.py
│   │   │   └── serato_crate.py
│   │   └── exporters/
│   │       ├── rekordbox_xml.py
│   │       └── m3u.py
│   ├── requirements.txt
│   ├── Dockerfile                     # for Render/Railway free-tier Docker deploy (needs ffmpeg)
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── UploadPanel.jsx
    │   │   ├── ImportPanel.jsx
    │   │   ├── TrackTable.jsx
    │   │   ├── CamelotBadge.jsx
    │   │   ├── SortControls.jsx
    │   │   └── ExportButtons.jsx
    │   ├── App.jsx                    # orchestrates upload/import/sort/export state
    │   ├── api.js                     # backend client
    │   ├── camelot.js                 # Camelot → color mapping for the UI
    │   └── main.jsx
    ├── package.json
    └── .env.example
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness check |
| POST | `/api/upload` | multipart audio files → analyzed `Track[]` |
| POST | `/api/import/rekordbox` | multipart Rekordbox XML → `Track[]` |
| POST | `/api/import/serato` | multipart `.crate` file → `Track[]` |
| POST | `/api/sort` | `{tracks}` → ordered `Track[]` + transition scores |
| POST | `/api/export/rekordbox` | `{tracks, playlist_name}` → Rekordbox XML file download |
| POST | `/api/export/m3u` | `{tracks, playlist_name}` → M3U file download |

Full interactive docs at `/docs` once the backend is running.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs once it's running. First analysis
request will be a bit slower than subsequent ones (numba JIT-compiles some
librosa internals on first use).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173 and talks to the backend at
`http://localhost:8000` by default (override with `VITE_API_BASE_URL`, see
`.env.example`).

## Why no database, no persisted files

Per the project requirements: uploaded audio is analyzed and discarded —
nothing is written anywhere persistent. Large files spool to a temp file on
disk *during* the request (so a multi-GB upload never sits fully in RAM),
but that temp file is deleted before the response goes out. The playlist
itself only exists as React state in the browser tab you have open; refresh
the page and it's gone (see below on state).

**Where does the playlist "live" between actions?** Only in the frontend's
memory. The backend is fully stateless — every request (`/api/sort`,
`/api/export/*`) round-trips the *entire* track list as JSON; nothing is
cached or persisted server-side between calls.

This keeps the app free to run (no storage costs) and sidesteps copyright
concerns around hosting users' music. If you later want the playlist to
survive a refresh, the cheap option is `localStorage` (no backend change);
cross-device persistence would need a real database, which is a deliberate
scope change from the current no-database design.

## Deploying for free

- **Backend (Render or Railway):** deploy `backend/` via the included
  `Dockerfile`. Docker deploys are available on both platforms' free tiers.
  A Dockerfile is used specifically because MP3 decoding via
  `librosa`/`audioread` needs `ffmpeg`, which isn't in the default Python
  buildpack. Set `ALLOWED_ORIGINS` to your deployed frontend URL.
- **Frontend (Vercel or Netlify):** deploy `frontend/` as a static Vite
  build (`npm run build` → `dist/`). Set `VITE_API_BASE_URL` to your
  deployed backend URL.
- Free tiers on Render/Railway spin down on inactivity — the first request
  after idling will be slow (cold start, plus numba JIT warmup on the first
  analysis). No config changes needed to handle this, just worth knowing.
- **Large-upload caveat:** the backend streams big files to disk instead of
  RAM, but free-tier instances still have limited disk space (and Render's
  free tier disk is ephemeral) and a request-duration ceiling on the edge
  proxy. A handful of multi-GB tracks should be fine; uploading your entire
  multi-terabyte library in one request is not realistic on a free host —
  that's a hosting-tier limit, not something the app config can fix.
- **CPU, not GPU:** analysis runs on CPU via NumPy/SciPy. Free-tier hosts
  give you shared, limited CPU — expect analysis to take a few seconds per
  track, longer under concurrent load. Each file's analysis is offloaded to
  a worker thread so the server stays responsive to other requests while it
  works.

## Tech stack

- **Backend:** Python, FastAPI, librosa (BPM/key analysis)
- **Frontend:** React (Vite)
- No database, no paid APIs.

## Known limitations / honest caveats

- **Exported Rekordbox `Location` for fresh uploads:** we only know the
  filename, not the DJ's real filesystem path, so Rekordbox will show these
  as "missing" until manually relinked. Tracks imported *from* a Rekordbox
  XML keep their original path and re-export cleanly.
- **Serato crates carry no BPM/key** — that data lives in the track's own
  ID3 tags (via Serato's own analysis) or Serato's separate database, not in
  the crate file. Imported tracks are flagged `needs_analysis`; re-uploading
  the matching audio (same filename) merges the analysis in automatically.
- **Key/BPM detection is heuristic**, not guaranteed-correct — see "How the
  analysis works" above.
- **Sort order is a greedy heuristic**, not a globally optimal path — see
  "How sorting works" above.
