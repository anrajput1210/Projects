"""ILP-based squad builder: picks an optimal 15-man FPL squad from scratch.

Maximizes total predicted xP across all 15 players subject to budget,
formation, and per-team constraints, then derives the best valid starting XI
and captain/vice-captain from that squad.
"""
from __future__ import annotations

import pandas as pd
import pulp

SQUAD_POSITION_LIMITS = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
SQUAD_SIZE = 15
MAX_PER_TEAM = 3

# (min, max) players allowed per position in a valid starting XI.
STARTING_XI_POSITION_RANGE = {
    "GKP": (1, 1),
    "DEF": (3, 5),
    "MID": (2, 5),
    "FWD": (1, 3),
}
STARTING_XI_SIZE = 11


def build_squad(
    xp_df: pd.DataFrame,
    budget: float = 100.0,
    max_per_team: int = MAX_PER_TEAM,
    locked_ids: set[int] | None = None,
    excluded_ids: set[int] | None = None,
) -> dict:
    """Solves an ILP to pick the 15-man squad maximizing total predicted xP.

    xp_df must have columns: player_id, name, team, team_short, position,
    price, predicted_xp (as produced by models.predict_xp.predict_xp).

    locked_ids: player_ids that must be included (e.g. players the user
    wants to keep). excluded_ids: player_ids that must not be included
    (e.g. players already ruled out). Both are used by the transfer
    optimizer to constrain rebuilds around an existing squad.

    Returns a dict: squad_df, starting_xi_df, captain_id, vice_captain_id,
    total_cost, squad_predicted_points, starting_xi_predicted_points.
    Raises ValueError if no feasible squad exists under the constraints.
    """
    locked_ids = locked_ids or set()
    excluded_ids = excluded_ids or set()

    df = xp_df.reset_index(drop=True)
    prob = pulp.LpProblem("fpl_squad_builder", pulp.LpMaximize)

    pick = {
        row.player_id: pulp.LpVariable(f"pick_{row.player_id}", cat="Binary")
        for row in df.itertuples()
    }

    prob += pulp.lpSum(pick[row.player_id] * row.predicted_xp for row in df.itertuples())

    prob += pulp.lpSum(pick[row.player_id] * row.price for row in df.itertuples()) <= budget

    for position, count in SQUAD_POSITION_LIMITS.items():
        ids_in_pos = df.loc[df["position"] == position, "player_id"]
        prob += pulp.lpSum(pick[pid] for pid in ids_in_pos) == count

    for team, group in df.groupby("team"):
        prob += pulp.lpSum(pick[pid] for pid in group["player_id"]) <= max_per_team

    for pid in locked_ids:
        if pid in pick:
            prob += pick[pid] == 1
    for pid in excluded_ids:
        if pid in pick:
            prob += pick[pid] == 0

    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)

    if pulp.LpStatus[prob.status] != "Optimal":
        raise ValueError(
            f"No feasible squad found under given constraints "
            f"(budget={budget}, max_per_team={max_per_team}); "
            f"solver status: {pulp.LpStatus[prob.status]}"
        )

    selected_ids = {pid for pid, var in pick.items() if var.value() == 1}
    squad_df = df[df["player_id"].isin(selected_ids)].copy()

    starting_xi_df, captain_id, vice_captain_id = select_starting_xi(squad_df)

    return {
        "squad_df": squad_df,
        "starting_xi_df": starting_xi_df,
        "captain_id": captain_id,
        "vice_captain_id": vice_captain_id,
        "total_cost": round(squad_df["price"].sum(), 1),
        "squad_predicted_points": round(squad_df["predicted_xp"].sum(), 2),
        "starting_xi_predicted_points": round(starting_xi_df["predicted_xp"].sum(), 2),
    }


def select_starting_xi(squad_df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Given a 15-man squad, picks the best valid starting XI (1 GK, 3-5 DEF,
    2-5 MID, 1-3 FWD, 11 total) maximizing total predicted xP via ILP, plus
    captain (highest xP starter) and vice-captain (second highest).

    Returns (starting_xi_df, captain_id, vice_captain_id).
    """
    if len(squad_df) != SQUAD_SIZE:
        raise ValueError(f"select_starting_xi expects a {SQUAD_SIZE}-man squad, got {len(squad_df)}")

    df = squad_df.reset_index(drop=True)
    prob = pulp.LpProblem("fpl_starting_xi", pulp.LpMaximize)

    start = {
        row.player_id: pulp.LpVariable(f"start_{row.player_id}", cat="Binary")
        for row in df.itertuples()
    }

    prob += pulp.lpSum(start[row.player_id] * row.predicted_xp for row in df.itertuples())
    prob += pulp.lpSum(start.values()) == STARTING_XI_SIZE

    for position, (lo, hi) in STARTING_XI_POSITION_RANGE.items():
        ids_in_pos = df.loc[df["position"] == position, "player_id"]
        prob += pulp.lpSum(start[pid] for pid in ids_in_pos) >= lo
        prob += pulp.lpSum(start[pid] for pid in ids_in_pos) <= hi

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        raise ValueError(
            f"No valid starting XI formation found; solver status: {pulp.LpStatus[prob.status]}"
        )

    starting_ids = {pid for pid, var in start.items() if var.value() == 1}
    starting_xi_df = df[df["player_id"].isin(starting_ids)].sort_values(
        "predicted_xp", ascending=False
    ).reset_index(drop=True)

    captain_id = int(starting_xi_df.iloc[0]["player_id"])
    vice_captain_id = int(starting_xi_df.iloc[1]["player_id"])

    return starting_xi_df, captain_id, vice_captain_id


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
    from models.predict_xp import predict_xp

    bootstrap = fetch_bootstrap_static()
    fixtures = fetch_fixtures()
    summaries = fetch_all_player_summaries(bootstrap)
    players_df = build_players_dataframe(bootstrap, fixtures, summaries)
    xp_df = predict_xp(players_df)

    result = build_squad(xp_df, budget=100.0)

    squad = result["squad_df"].sort_values(["position", "predicted_xp"], ascending=[True, False])
    print("=== Full 15-man squad ===")
    print(squad[["name", "team_short", "position", "price", "predicted_xp"]].to_string(index=False))
    print(f"\nTotal cost: £{result['total_cost']}m / £100.0m budget")
    print(f"Squad predicted points: {result['squad_predicted_points']}")

    # Constraint checks
    assert result["total_cost"] <= 100.0, "BUDGET CONSTRAINT VIOLATED"
    pos_counts = squad["position"].value_counts().to_dict()
    assert pos_counts == SQUAD_POSITION_LIMITS, f"FORMATION CONSTRAINT VIOLATED: {pos_counts}"
    team_counts = squad["team"].value_counts()
    assert (team_counts <= MAX_PER_TEAM).all(), f"MAX-PER-TEAM CONSTRAINT VIOLATED: {team_counts.to_dict()}"
    print("\n[OK] budget, formation (2-5-5-3), and max-3-per-team constraints all satisfied.")

    xi = result["starting_xi_df"]
    print("\n=== Recommended starting XI ===")
    print(xi[["name", "team_short", "position", "predicted_xp"]].to_string(index=False))
    xi_pos_counts = xi["position"].value_counts().to_dict()
    print(f"Formation: {xi_pos_counts}")
    print(f"Starting XI predicted points (before captain multiplier): {result['starting_xi_predicted_points']}")

    captain = squad[squad["player_id"] == result["captain_id"]].iloc[0]
    vice = squad[squad["player_id"] == result["vice_captain_id"]].iloc[0]
    print(f"\nCaptain: {captain['name']} ({captain['predicted_xp']} xP -> {captain['predicted_xp'] * 2} as captain)")
    print(f"Vice-captain: {vice['name']} ({vice['predicted_xp']} xP)")

    effective_points = result["starting_xi_predicted_points"] + captain["predicted_xp"]
    print(f"\nEffective predicted GW points (starting XI + captain bonus): {round(effective_points, 2)}")
