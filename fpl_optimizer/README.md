# FPL Team Optimizer

A Streamlit app that pulls live data from the official Fantasy Premier League
API, predicts expected points (xP) for every player, and either builds an
optimal 15-man squad from scratch under budget or suggests the best
transfers for your existing squad.

## How it works

- **`data/fetch_fpl_data.py`** - pulls `bootstrap-static`, `fixtures`, and
  per-player `element-summary` data from the FPL API (no auth required),
  caches everything to `data/cache/` (JSON, with TTLs), and builds a clean
  pandas DataFrame of recent form, minutes, fixture difficulty, etc. Also
  handles fetching a user's squad by Team ID and fuzzy-matching manually
  typed player names to FPL player IDs.
- **`models/predict_xp.py`** - v1 prediction model: a recency-weighted
  rolling average of the last 5 gameweeks' points, adjusted by expected
  minutes, next-fixture difficulty (FPL's FDR), home/away, and
  injury/suspension availability. It's deliberately decoupled from the
  optimizer - swap in a fancier model (e.g. XGBoost on lagged features)
  later without touching any optimizer code, as long as it still returns a
  DataFrame with a `predicted_xp` column.
- **`optimizer/squad_builder.py`** - ILP (via PuLP) that picks the 15-man
  squad maximizing total predicted xP under budget, formation (2 GK / 5 DEF
  / 5 MID / 3 FWD), and max-3-players-per-real-team constraints, then a
  second small ILP picks the best valid starting XI and captain/vice-captain.
- **`optimizer/transfer_optimizer.py`** - reuses the same constraints plus a
  transfer-count constraint to suggest the best moves within your free
  transfers, the best paid ("hit") options only if they net-beat the free
  option after the -4/-8 penalty, and a full wildcard/free-hit rebuild.
- **`app.py`** - Streamlit UI wiring it all together: sidebar mode toggle,
  Team ID or manual squad entry, budget/free-transfer controls, and
  sortable result tables.

## Setup

```bash
cd fpl_optimizer
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Usage

**Build New Squad mode:** set a budget in the sidebar and click *Build
Optimal Squad*. You'll get the full 15-man squad, a recommended starting
XI, and captain/vice-captain picks.

**Optimize My Current Squad mode:**
- Enter your numeric FPL **Team ID** (from your team's URL on the FPL
  site) and click *Fetch My Squad* - this pulls your actual picks, bank
  balance, and estimates your free transfers automatically. Or,
- Use **Manual entry** if you don't have/want to use a Team ID: paste 15
  player names (one per line), match them, resolve any ambiguous matches
  via the dropdowns, and enter your bank/free transfers by hand.

Click *Suggest Transfers* to see: the best move within your free
transfers, paid ("hit") options only if they're worth the -4/-8, and a
wildcard/free-hit rebuild for comparison.

## Known limitations (v1)

- **Prediction model is intentionally simple.** It's a weighted rolling
  average, not a trained model - early in a season (few gameweeks played)
  predictions lean heavily on limited data and can look noisy. This is by
  design for v1; `predict_xp()` is the only place a better model needs to
  plug in.
- **Selling price approximation.** The no-auth FPL API doesn't expose a
  user's actual per-player selling price (which can differ from current
  market price after FPL's profit-taking rule). The transfer optimizer
  approximates a kept player's value using their current market price, and
  uses the manager's total squad value + bank as the overall budget
  envelope, which is exact.
- **Free transfers are estimated**, not read directly - the FPL API
  doesn't expose "free transfers remaining" either, so it's reconstructed
  from transfer history under the standard rules (1 per gameweek, stacks
  up to 5). You can override the estimate in the UI.
- Injury/rotation risk uses FPL's own `chance_of_playing_next_round` plus
  average recent minutes - it won't catch news that hasn't hit the API yet.

## Project structure

```
fpl_optimizer/
├── data/
│   ├── fetch_fpl_data.py       # API calls + caching + user squad input
│   └── cache/                  # local cached JSON (gitignored)
├── models/
│   └── predict_xp.py           # expected points prediction (swappable)
├── optimizer/
│   ├── squad_builder.py        # ILP for building from scratch
│   └── transfer_optimizer.py   # ILP for transfer suggestions
├── app.py                      # Streamlit UI
├── requirements.txt
└── README.md
```
