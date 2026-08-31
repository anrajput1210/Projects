"""Fetches and caches data from the official Fantasy Premier League API.

No authentication is required for the endpoints used here. Responses are
cached to local JSON files so repeated runs don't hammer the API.
"""
from __future__ import annotations

import difflib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import requests

BASE_URL = "https://fantasy.premierleague.com/api"
CACHE_DIR = Path(__file__).parent / "cache"
PLAYER_CACHE_DIR = CACHE_DIR / "players"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Default cache lifetimes, in seconds.
BOOTSTRAP_TTL = 60 * 60  # 1 hour - player prices/form change slowly during a GW
FIXTURES_TTL = 60 * 60 * 6  # 6 hours - fixtures rarely change
PLAYER_SUMMARY_TTL = 60 * 60  # 1 hour
ENTRY_TTL = 60 * 5  # 5 minutes - user may want fresher data on their own squad


def _ensure_cache_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PLAYER_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_cache(path: Path, ttl: int) -> dict[str, Any] | None:
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, data: dict[str, Any]) -> None:
    _ensure_cache_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _get(url: str, timeout: int = 15) -> Any:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_bootstrap_static(force_refresh: bool = False) -> dict[str, Any]:
    """Fetches the main FPL dataset: players, teams, positions, current gameweek.

    This is the single largest and most-used endpoint - basically everything
    except per-gameweek player history and fixtures lives here.
    """
    cache_path = CACHE_DIR / "bootstrap_static.json"
    if not force_refresh:
        cached = _read_cache(cache_path, BOOTSTRAP_TTL)
        if cached is not None:
            return cached

    data = _get(f"{BASE_URL}/bootstrap-static/")
    _write_cache(cache_path, data)
    return data


def fetch_fixtures(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetches all fixtures for the season, including FDR (difficulty ratings)."""
    cache_path = CACHE_DIR / "fixtures.json"
    if not force_refresh:
        cached = _read_cache(cache_path, FIXTURES_TTL)
        if cached is not None:
            return cached["fixtures"]

    data = _get(f"{BASE_URL}/fixtures/")
    _write_cache(cache_path, {"fixtures": data})
    return data


def fetch_player_summary(player_id: int, force_refresh: bool = False) -> dict[str, Any]:
    """Fetches one player's per-gameweek history + upcoming fixtures.

    Cached per-player since bootstrap-static doesn't include GW-by-GW detail.
    """
    cache_path = PLAYER_CACHE_DIR / f"{player_id}.json"
    if not force_refresh:
        cached = _read_cache(cache_path, PLAYER_SUMMARY_TTL)
        if cached is not None:
            return cached

    data = _get(f"{BASE_URL}/element-summary/{player_id}/")
    _write_cache(cache_path, data)
    return data


def fetch_entry_picks(team_id: int, gameweek: int) -> dict[str, Any]:
    """Fetches a manager's squad picks for a given gameweek. Not disk-cached.

    Raises requests.HTTPError (404) if the team_id or gameweek is invalid.
    """
    return _get(f"{BASE_URL}/entry/{team_id}/event/{gameweek}/picks/")


def fetch_entry_history(team_id: int) -> dict[str, Any]:
    """Fetches a manager's season history: bank, transfers, chips used, etc.

    Raises requests.HTTPError (404) if the team_id is invalid.
    """
    return _get(f"{BASE_URL}/entry/{team_id}/history/")


def fetch_entry_info(team_id: int) -> dict[str, Any]:
    """Fetches basic manager/entry info (team name, manager name, etc.)."""
    return _get(f"{BASE_URL}/entry/{team_id}/")


def get_current_gameweek(bootstrap: dict[str, Any] | None = None) -> int:
    """Returns the current (or next, if between gameweeks) gameweek id."""
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()
    events = bootstrap["events"]
    for event in events:
        if event["is_current"]:
            return event["id"]
    for event in events:
        if event["is_next"]:
            return event["id"]
    # Season hasn't started or has ended - fall back to the last event.
    return events[-1]["id"]


def get_next_gameweek(bootstrap: dict[str, Any] | None = None) -> int:
    """Returns the id of the next gameweek to be played (the prediction target).

    This is what the optimizer should build/transfer for - if the current
    gameweek has already finished, that's the *next* event, not the current one.
    """
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()
    events = bootstrap["events"]
    for event in events:
        if event["is_next"]:
            return event["id"]
    for event in events:
        if event["is_current"] and not event["finished"]:
            return event["id"]
    return events[-1]["id"]


def fetch_all_player_summaries(
    bootstrap: dict[str, Any] | None = None,
    max_workers: int = 10,
    force_refresh: bool = False,
) -> dict[int, dict[str, Any]]:
    """Fetches element-summary (per-GW history) for every player, in parallel.

    With disk caching this is slow on a cold cache (600+ requests) but near
    instant on repeat runs within PLAYER_SUMMARY_TTL.
    """
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()
    player_ids = [el["id"] for el in bootstrap["elements"]]

    summaries: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(fetch_player_summary, pid, force_refresh): pid
            for pid in player_ids
        }
        for future in as_completed(future_to_id):
            pid = future_to_id[future]
            try:
                summaries[pid] = future.result()
            except requests.HTTPError:
                summaries[pid] = {"history": [], "fixtures": []}
    return summaries


_POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _weighted_recent_form(history: list[dict[str, Any]], n: int = 5) -> float:
    """Recency-weighted average points over the last n gameweeks played.

    Most-recent gameweek gets the highest weight. With fewer than n games
    played (e.g. start of season) it just averages what's available.
    """
    recent = history[-n:]
    if not recent:
        return 0.0
    weights = list(range(1, len(recent) + 1))  # e.g. [1,2,3,4,5] - newest heaviest
    total_weight = sum(weights)
    return sum(gw["total_points"] * w for gw, w in zip(recent, weights)) / total_weight


def _avg_minutes(history: list[dict[str, Any]], n: int = 5) -> float:
    recent = history[-n:]
    if not recent:
        return 0.0
    return sum(gw["minutes"] for gw in recent) / len(recent)


def get_team_next_fixtures(
    team_id: int,
    fixtures: list[dict[str, Any]],
    from_event: int,
    n: int = 3,
) -> list[dict[str, Any]]:
    """Returns the next n unplayed fixtures for a team from from_event onward.

    Each entry: {event, opponent_team, is_home, difficulty}.
    """
    team_fixtures = [
        f for f in fixtures
        if f["event"] is not None
        and f["event"] >= from_event
        and not f["finished"]
        and (f["team_h"] == team_id or f["team_a"] == team_id)
    ]
    team_fixtures.sort(key=lambda f: f["event"])

    result = []
    for f in team_fixtures[:n]:
        is_home = f["team_h"] == team_id
        result.append({
            "event": f["event"],
            "opponent_team": f["team_a"] if is_home else f["team_h"],
            "is_home": is_home,
            "difficulty": f["team_h_difficulty"] if is_home else f["team_a_difficulty"],
        })
    return result


def build_players_dataframe(
    bootstrap: dict[str, Any] | None = None,
    fixtures: list[dict[str, Any]] | None = None,
    summaries: dict[int, dict[str, Any]] | None = None,
    next_n_fixtures: int = 3,
) -> pd.DataFrame:
    """Builds one row per player with recent form, season stats, price,
    position, team, and upcoming fixture difficulty - the base dataset the
    xP prediction model consumes.
    """
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()
    if fixtures is None:
        fixtures = fetch_fixtures()
    if summaries is None:
        summaries = fetch_all_player_summaries(bootstrap)

    team_names = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
    target_gw = get_next_gameweek(bootstrap)

    rows = []
    for el in bootstrap["elements"]:
        pid = el["id"]
        history = summaries.get(pid, {}).get("history", [])
        next_fixtures = get_team_next_fixtures(
            el["team"], fixtures, from_event=target_gw, n=next_n_fixtures
        )

        row = {
            "player_id": pid,
            "web_name": el["web_name"],
            "full_name": f"{el['first_name']} {el['second_name']}",
            "team": el["team"],
            "team_short": team_names.get(el["team"], "UNK"),
            "position": _POSITION_MAP.get(el["element_type"], "UNK"),
            "price": el["now_cost"] / 10.0,
            "status": el["status"],  # 'a'=available, 'i'=injured, 'd'=doubtful, 's'=suspended
            "chance_of_playing_next_round": el["chance_of_playing_next_round"],
            "total_points": el["total_points"],
            "points_per_game": float(el["points_per_game"] or 0.0),
            "form": float(el["form"] or 0.0),
            "minutes": el["minutes"],
            "goals_scored": el["goals_scored"],
            "assists": el["assists"],
            "clean_sheets": el["clean_sheets"],
            "bonus": el["bonus"],
            "ict_index": float(el["ict_index"] or 0.0),
            "selected_by_percent": float(el["selected_by_percent"] or 0.0),
            "weighted_form_5gw": _weighted_recent_form(history, n=5),
            "avg_minutes_5gw": _avg_minutes(history, n=5),
            "games_played": len(history),
            "next_fixtures": next_fixtures,
            "next_fixture_difficulty_avg": (
                sum(f["difficulty"] for f in next_fixtures) / len(next_fixtures)
                if next_fixtures else None
            ),
        }
        rows.append(row)

    return pd.DataFrame(rows)


MAX_FREE_TRANSFERS = 5


def estimate_free_transfers(entry_history: dict[str, Any], target_gameweek: int) -> int:
    """Approximates free transfers available going into target_gameweek.

    The FPL API doesn't expose "free transfers remaining" directly, so this
    replays the season: start with 1 FT (from GW2 onward - GW1's squad
    selection isn't a transfer), gain +1 for each gameweek with 0 transfers
    made (capped at MAX_FREE_TRANSFERS), and lose 1 per transfer made
    (floored at... it can't go below 0, extra transfers beyond what's
    banked are simply paid transfers costing -4 each, tracked separately
    by the API as event_transfers_cost).

    This is an approximation - it doesn't know about wildcard/free-hit
    chip usage suppressing the transfer-cost mechanic, so callers should
    also check for an active chip separately via entry_history["chips"].
    """
    if target_gameweek <= 1:
        return 1

    free_transfers = 1
    for gw in entry_history.get("current", []):
        if gw["event"] >= target_gameweek:
            break
        if gw["event"] == 1:
            continue  # GW1 squad selection doesn't consume/grant a transfer
        transfers_made = gw["event_transfers"]
        if transfers_made == 0:
            free_transfers = min(free_transfers + 1, MAX_FREE_TRANSFERS)
        else:
            free_transfers = max(free_transfers - transfers_made, 0)
            free_transfers = min(free_transfers + 1, MAX_FREE_TRANSFERS)
    return free_transfers


def get_user_squad(team_id: int, bootstrap: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetches a manager's current 15-man squad, bank balance, free transfers,
    and chip usage via their FPL Team ID.

    Raises requests.HTTPError (404) if the team_id doesn't exist.
    """
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()

    current_gw = get_current_gameweek(bootstrap)
    target_gw = get_next_gameweek(bootstrap)

    entry_info = fetch_entry_info(team_id)
    entry_history = fetch_entry_history(team_id)
    picks_data = fetch_entry_picks(team_id, current_gw)

    picks = [
        {
            "player_id": p["element"],
            "squad_position": p["position"],
            "multiplier": p["multiplier"],
            "is_captain": p["is_captain"],
            "is_vice_captain": p["is_vice_captain"],
        }
        for p in picks_data["picks"]
    ]

    active_chips = {c["name"] for c in entry_history.get("chips", [])
                     if c.get("event") == current_gw}

    return {
        "team_id": team_id,
        "manager_name": f"{entry_info.get('player_first_name', '')} "
                         f"{entry_info.get('player_last_name', '')}".strip(),
        "team_name": entry_info.get("name", ""),
        "picks": picks,
        "player_ids": [p["player_id"] for p in picks],
        "bank": picks_data["entry_history"]["bank"] / 10.0,
        "squad_value": picks_data["entry_history"]["value"] / 10.0,
        "current_gameweek": current_gw,
        "target_gameweek": target_gw,
        "free_transfers": estimate_free_transfers(entry_history, target_gw),
        "active_chip_this_gw": picks_data.get("active_chip"),
        "chips_used": [c["name"] for c in entry_history.get("chips", [])],
    }


def match_player_names(
    names: list[str],
    bootstrap: dict[str, Any] | None = None,
    cutoff: float = 0.6,
) -> dict[str, list[dict[str, Any]]]:
    """Fuzzy-matches free-text player names to FPL player IDs, for manual
    squad entry when a user doesn't have (or doesn't want to use) a Team ID.

    Matches against both web_name (e.g. "Salah") and full name (e.g.
    "Mohamed Salah"). Returns {input_name: [candidate matches]}, best first;
    an empty list means no match was found above the cutoff, and callers
    (e.g. the Streamlit UI) should prompt the user to disambiguate manually.
    """
    if bootstrap is None:
        bootstrap = fetch_bootstrap_static()

    team_names = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
    candidates = []
    lookup_names = []
    for el in bootstrap["elements"]:
        full_name = f"{el['first_name']} {el['second_name']}"
        candidates.append({
            "player_id": el["id"],
            "web_name": el["web_name"],
            "full_name": full_name,
            "team_short": team_names.get(el["team"], "UNK"),
            "position": _POSITION_MAP.get(el["element_type"], "UNK"),
            "total_points": el["total_points"],
        })
        lookup_names.append(el["web_name"].lower())
        lookup_names.append(full_name.lower())

    # Multiple players can share a web_name (e.g. two "Palmer"s), so each
    # lowercased name maps to a *list* of candidates, ranked by total_points
    # so the more prominent/relevant player surfaces first on a tie.
    name_to_candidates: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        for key in (c["web_name"].lower(), c["full_name"].lower()):
            name_to_candidates.setdefault(key, []).append(c)
    for cands in name_to_candidates.values():
        cands.sort(key=lambda c: c["total_points"], reverse=True)

    results: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        query = name.strip().lower()
        exact = name_to_candidates.get(query)
        if exact:
            results[name] = [{**c, "match_score": 1.0} for c in exact]
            continue

        close = difflib.get_close_matches(query, lookup_names, n=5, cutoff=cutoff)
        seen_ids = set()
        matches = []
        for match in close:
            score = difflib.SequenceMatcher(None, query, match).ratio()
            for candidate in name_to_candidates.get(match, []):
                if candidate["player_id"] not in seen_ids:
                    seen_ids.add(candidate["player_id"])
                    matches.append({**candidate, "match_score": round(score, 2)})
        results[name] = matches

    return results


if __name__ == "__main__":
    # Quick smoke test: fetch and print basic stats about the pulled data.
    print("Fetching bootstrap-static ...")
    bootstrap = fetch_bootstrap_static()
    print(f"  players: {len(bootstrap['elements'])}")
    print(f"  teams:   {len(bootstrap['teams'])}")
    current_gw = get_current_gameweek(bootstrap)
    print(f"  current gameweek: {current_gw}")

    print("Fetching fixtures ...")
    fixtures = fetch_fixtures()
    print(f"  fixtures: {len(fixtures)}")

    sample_player = bootstrap["elements"][0]
    print(f"Fetching element-summary for player {sample_player['id']} "
          f"({sample_player['web_name']}) ...")
    summary = fetch_player_summary(sample_player["id"])
    print(f"  history entries: {len(summary['history'])}")
    print(f"  fixtures entries: {len(summary['fixtures'])}")

    print("\nFetching user squad for team_id=1 ...")
    squad = get_user_squad(1, bootstrap)
    print(f"  manager: {squad['manager_name']} ({squad['team_name']})")
    print(f"  bank: £{squad['bank']}m, squad value: £{squad['squad_value']}m")
    print(f"  free transfers (est.): {squad['free_transfers']}")
    print(f"  target gameweek: {squad['target_gameweek']}")
    print(f"  picks: {len(squad['picks'])} players, "
          f"captain id={[p['player_id'] for p in squad['picks'] if p['is_captain']]}")

    print("\nFuzzy-matching manual player names ...")
    matches = match_player_names(["Salah", "Haaland", "Palmer", "Not A Real Playerxyz"], bootstrap)
    for name, cands in matches.items():
        if cands:
            best = cands[0]
            print(f"  '{name}' -> {best['web_name']} ({best['team_short']}, {best['position']}) "
                  f"score={best['match_score']} [{len(cands)} candidate(s)]")
        else:
            print(f"  '{name}' -> NO MATCH")

    print(f"Target gameweek for predictions: {get_next_gameweek(bootstrap)}")

    print("Fetching all player summaries (parallel, cached) ...")
    t0 = time.time()
    summaries = fetch_all_player_summaries(bootstrap)
    print(f"  fetched {len(summaries)} summaries in {time.time() - t0:.1f}s")

    print("Building players DataFrame ...")
    df = build_players_dataframe(bootstrap, fixtures, summaries)
    print(f"  shape: {df.shape}")
    print(df[[
        "web_name", "team_short", "position", "price", "form",
        "weighted_form_5gw", "avg_minutes_5gw", "next_fixture_difficulty_avg",
    ]].sort_values("form", ascending=False).head(10).to_string(index=False))
