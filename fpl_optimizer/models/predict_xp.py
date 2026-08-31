"""Expected points (xP) prediction for the upcoming gameweek.

This module is intentionally decoupled from the optimizer: it only needs to
produce a DataFrame with a `predicted_xp` column. Swap `predict_xp` for a
fancier model later (e.g. XGBoost on lagged features) without touching
`optimizer/squad_builder.py` or `optimizer/transfer_optimizer.py`.
"""
from __future__ import annotations

import pandas as pd
from pandas import isna

# Fixture difficulty ranges 1 (easiest) to 5 (hardest). This maps difficulty
# to a multiplier on predicted points - 3 (average) is a no-op.
FDR_MULTIPLIER = {
    1: 1.25,
    2: 1.10,
    3: 1.00,
    4: 0.85,
    5: 0.70,
}

# Below this expected-minutes threshold a player is treated as a rotation/
# injury risk and their xP is scaled down proportionally to minutes.
FULL_MINUTES = 90.0

HOME_BONUS = 1.05
AWAY_PENALTY = 0.97


def _minutes_multiplier(avg_minutes_5gw: float, games_played: int) -> float:
    """Scales down xP for players who aren't playing full/regular minutes.

    A player averaging 90 mins gets no penalty; a bench player averaging
    10 mins gets scaled down hard. New-to-data-set players (0 games played,
    e.g. very start of season) get a neutral 0.5 rather than 0, so the model
    doesn't zero out everyone before GW1 history exists.
    """
    if games_played == 0:
        return 0.5
    return min(avg_minutes_5gw / FULL_MINUTES, 1.0)


def _fixture_multiplier(next_fixtures: list[dict]) -> float:
    """Blends FDR-based multiplier and home/away split for the very next fixture.

    Only the immediate next fixture drives home/away (captaincy-relevant);
    the multi-fixture average difficulty is folded in for rotation-adjacent
    signal via the caller averaging across next_fixtures upstream if desired.
    """
    if not next_fixtures:
        return 1.0
    next_fx = next_fixtures[0]
    fdr_mult = FDR_MULTIPLIER.get(next_fx["difficulty"], 1.0)
    home_away_mult = HOME_BONUS if next_fx["is_home"] else AWAY_PENALTY
    return fdr_mult * home_away_mult


def _availability_multiplier(status: str, chance_of_playing_next_round) -> float:
    """Down-weights injured/suspended/doubtful players.

    status: 'a' available, 'd' doubtful, 'i' injured, 's' suspended, 'u' unavailable.
    chance_of_playing_next_round is a 0-100 percent, or None/NaN (None becomes
    NaN once it passes through a pandas column) when the FPL API has no
    explicit percentage - treated as 100 when status is otherwise available.
    """
    if status == "a" and isna(chance_of_playing_next_round):
        return 1.0
    if not isna(chance_of_playing_next_round):
        return chance_of_playing_next_round / 100.0
    if status in ("i", "s", "u"):
        return 0.0
    return 0.5  # doubtful with no explicit percentage given


def predict_xp(players_df: pd.DataFrame) -> pd.DataFrame:
    """Predicts expected points for the upcoming gameweek for every player.

    v1 model: recency-weighted rolling average of points over the last 5 GWs,
    adjusted by expected-minutes, next-fixture difficulty, home/away, and
    injury/suspension availability. Returns a new DataFrame (input untouched)
    with player_id, name, team, position, price, and predicted_xp.
    """
    df = players_df.copy()

    df["minutes_mult"] = df.apply(
        lambda r: _minutes_multiplier(r["avg_minutes_5gw"], r["games_played"]), axis=1
    )
    df["fixture_mult"] = df["next_fixtures"].apply(_fixture_multiplier)
    df["availability_mult"] = df.apply(
        lambda r: _availability_multiplier(r["status"], r["chance_of_playing_next_round"]),
        axis=1,
    )

    # Base rate: weighted recent form if the player has history, else fall
    # back to season points-per-game (handles very-early-season sparsity).
    base_rate = df["weighted_form_5gw"].where(
        df["games_played"] > 0, df["points_per_game"]
    )

    df["predicted_xp"] = (
        base_rate * df["minutes_mult"] * df["fixture_mult"] * df["availability_mult"]
    ).clip(lower=0).round(2)

    return df[[
        "player_id", "web_name", "full_name", "team", "team_short", "position",
        "price", "predicted_xp", "weighted_form_5gw", "minutes_mult",
        "fixture_mult", "availability_mult", "next_fixtures",
    ]].rename(columns={"web_name": "name"})


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from data.fetch_fpl_data import (
        build_players_dataframe,
        fetch_all_player_summaries,
        fetch_bootstrap_static,
        fetch_fixtures,
    )

    bootstrap = fetch_bootstrap_static()
    fixtures = fetch_fixtures()
    summaries = fetch_all_player_summaries(bootstrap)
    players_df = build_players_dataframe(bootstrap, fixtures, summaries)

    xp_df = predict_xp(players_df)

    print("Top 15 predicted xP overall:")
    print(xp_df.sort_values("predicted_xp", ascending=False).head(15)[[
        "name", "team_short", "position", "price", "predicted_xp",
    ]].to_string(index=False))

    print("\nTop 5 predicted xP by position:")
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        subset = xp_df[xp_df["position"] == pos].sort_values(
            "predicted_xp", ascending=False
        ).head(5)
        print(f"\n{pos}:")
        print(subset[["name", "team_short", "price", "predicted_xp"]].to_string(index=False))

    # Sanity check against a few well-known, high-ownership names if present.
    known_names = ["Haaland", "Salah", "Palmer", "M.Salah"]
    sanity = xp_df[xp_df["name"].isin(known_names)]
    if not sanity.empty:
        print("\nSanity check (known premium players):")
        print(sanity[["name", "team_short", "price", "predicted_xp"]].to_string(index=False))
