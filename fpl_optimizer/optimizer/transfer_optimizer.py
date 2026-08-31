"""ILP-based transfer suggestions: compares a user's current squad against
optimal swaps under the free-transfer / points-hit tradeoff.

Reuses the same formation/budget/max-per-team constraints as squad_builder,
plus a constraint on how many players may change (the "transfer count").

Note on prices: the no-auth FPL API doesn't expose per-player *selling*
price (which can differ from current market price after profit-taking
rules), so this module approximates a kept player's contribution to the
budget using their current market price from xp_df. Budget should be passed
as the user's actual total budget (squad value + bank) so the overall
envelope is still correct even if individual attribution is approximate.
"""
from __future__ import annotations

import pandas as pd
import pulp

from optimizer.squad_builder import (
    MAX_PER_TEAM,
    SQUAD_POSITION_LIMITS,
    select_starting_xi,
)

HIT_COST = 4.0
MAX_HITS_TO_CONSIDER = 2


def _solve_transfer_squad(
    xp_df: pd.DataFrame,
    current_ids: set[int],
    budget: float,
    max_per_team: int,
    transfers_max: int | None = None,
    transfers_exact: int | None = None,
) -> set[int] | None:
    """Solves the ILP for one transfer scenario; returns selected player_ids
    or None if infeasible. Exactly one of transfers_max/transfers_exact
    should be given.
    """
    df = xp_df.reset_index(drop=True)
    prob = pulp.LpProblem("fpl_transfer_optimizer", pulp.LpMaximize)

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

    new_players = [pid for pid in pick if pid not in current_ids]
    transfers_used = pulp.lpSum(pick[pid] for pid in new_players)
    if transfers_exact is not None:
        prob += transfers_used == transfers_exact
    elif transfers_max is not None:
        prob += transfers_used <= transfers_max

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        return None
    return {pid for pid, var in pick.items() if var.value() == 1}


def _pair_transfers(current_df: pd.DataFrame, selected_df: pd.DataFrame) -> list[dict]:
    """Pairs players dropped with players added, matched by position (since
    formation counts are fixed, each position's drop-count == add-count).
    Pairs worst-dropped with best-added within a position for a readable
    "out -> in" table.
    """
    current_ids = set(current_df["player_id"])
    selected_ids = set(selected_df["player_id"])

    pairs = []
    for position in SQUAD_POSITION_LIMITS:
        outs = current_df[
            (current_df["position"] == position) & (~current_df["player_id"].isin(selected_ids))
        ].sort_values("predicted_xp")
        ins = selected_df[
            (selected_df["position"] == position) & (~selected_df["player_id"].isin(current_ids))
        ].sort_values("predicted_xp", ascending=False)

        for (_, out_row), (_, in_row) in zip(outs.iterrows(), ins.iterrows()):
            pairs.append({
                "position": position,
                "out_name": out_row["name"],
                "out_team": out_row["team_short"],
                "out_price": out_row["price"],
                "out_xp": out_row["predicted_xp"],
                "in_name": in_row["name"],
                "in_team": in_row["team_short"],
                "in_price": in_row["price"],
                "in_xp": in_row["predicted_xp"],
                "price_change": round(in_row["price"] - out_row["price"], 1),
                "xp_gain": round(in_row["predicted_xp"] - out_row["predicted_xp"], 2),
            })
    return pairs


def _package_scenario(
    xp_df: pd.DataFrame,
    current_df: pd.DataFrame,
    selected_ids: set[int],
    free_transfers: int,
    hit_cost: float,
) -> dict:
    df = xp_df.reset_index(drop=True)
    selected_df = df[df["player_id"].isin(selected_ids)].copy()

    n_transfers = len(selected_ids - set(current_df["player_id"]))
    hits = max(0, n_transfers - free_transfers)
    penalty = hits * hit_cost

    raw_gain = round(
        selected_df["predicted_xp"].sum() - current_df["predicted_xp"].sum(), 2
    )
    net_gain = round(raw_gain - penalty, 2)

    starting_xi_df, captain_id, vice_captain_id = select_starting_xi(selected_df)

    return {
        "squad_df": selected_df,
        "starting_xi_df": starting_xi_df,
        "captain_id": captain_id,
        "vice_captain_id": vice_captain_id,
        "transfers": _pair_transfers(current_df, selected_df),
        "n_transfers": n_transfers,
        "free_transfers_used": min(n_transfers, free_transfers),
        "hits": hits,
        "penalty": penalty,
        "raw_xp_gain": raw_gain,
        "net_xp_gain": net_gain,
        "total_cost": round(selected_df["price"].sum(), 1),
    }


def suggest_transfers(
    xp_df: pd.DataFrame,
    current_squad_ids: set[int],
    budget: float,
    free_transfers: int,
    max_per_team: int = MAX_PER_TEAM,
    hit_cost: float = HIT_COST,
    max_hits_to_consider: int = MAX_HITS_TO_CONSIDER,
) -> dict:
    """Suggests transfers for a user's current squad, ranked by scenario.

    xp_df: full player pool with predicted_xp (from models.predict_xp).
    current_squad_ids: the user's current 15 player_ids.
    budget: total spendable value (squad value + bank) - see module
    docstring for the selling-price caveat.
    free_transfers: free transfers available this gameweek (no penalty).

    Returns {'free': {...}, 'hit_1': {...} or None, 'hit_2': {...} or None,
    ...}, each a scenario dict from _package_scenario, or None if that
    scenario isn't worth it (net gain doesn't beat the best cheaper option)
    or is infeasible.
    """
    df = xp_df.reset_index(drop=True)
    current_df = df[df["player_id"].isin(current_squad_ids)].copy()
    if len(current_df) != len(current_squad_ids):
        missing = current_squad_ids - set(current_df["player_id"])
        raise ValueError(f"Some current squad player_ids not found in xp_df: {missing}")

    scenarios: dict[str, dict | None] = {}

    free_ids = _solve_transfer_squad(
        xp_df, current_squad_ids, budget, max_per_team, transfers_max=free_transfers
    )
    if free_ids is None:
        raise ValueError(
            "No feasible squad found even using 0 transfers - check budget covers "
            "the current squad's value."
        )
    scenarios["free"] = _package_scenario(xp_df, current_df, free_ids, free_transfers, hit_cost)

    best_net_so_far = scenarios["free"]["net_xp_gain"]
    for extra in range(1, max_hits_to_consider + 1):
        n = free_transfers + extra
        hit_ids = _solve_transfer_squad(
            xp_df, current_squad_ids, budget, max_per_team, transfers_exact=n
        )
        key = f"hit_{extra}"
        if hit_ids is None:
            scenarios[key] = None
            continue
        scenario = _package_scenario(xp_df, current_df, hit_ids, free_transfers, hit_cost)
        if scenario["net_xp_gain"] > best_net_so_far:
            scenarios[key] = scenario
            best_net_so_far = scenario["net_xp_gain"]
        else:
            scenarios[key] = None  # not worth it - doesn't beat the cheaper option

    return scenarios


def suggest_wildcard(
    xp_df: pd.DataFrame,
    current_squad_ids: set[int],
    budget: float,
    max_per_team: int = MAX_PER_TEAM,
) -> dict:
    """Best full-squad rebuild with unlimited free transfers (wildcard/free
    hit), i.e. squad_builder.build_squad with no transfer-count constraint,
    packaged the same way as suggest_transfers' scenarios for a consistent
    UI (transfers list, net gain with 0 penalty, etc).
    """
    df = xp_df.reset_index(drop=True)
    current_df = df[df["player_id"].isin(current_squad_ids)].copy()

    selected_ids = _solve_transfer_squad(xp_df, current_squad_ids, budget, max_per_team)
    if selected_ids is None:
        raise ValueError("No feasible wildcard squad found under the given budget.")

    return _package_scenario(xp_df, current_df, selected_ids, free_transfers=99, hit_cost=0.0)


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from data.fetch_fpl_data import (
        build_players_dataframe,
        fetch_all_player_summaries,
        fetch_bootstrap_static,
        fetch_fixtures,
        get_user_squad,
    )
    from models.predict_xp import predict_xp

    bootstrap = fetch_bootstrap_static()
    fixtures = fetch_fixtures()
    summaries = fetch_all_player_summaries(bootstrap)
    players_df = build_players_dataframe(bootstrap, fixtures, summaries)
    xp_df = predict_xp(players_df)

    user_squad = get_user_squad(1, bootstrap)
    current_ids = set(user_squad["player_ids"])
    budget = user_squad["squad_value"] + user_squad["bank"]
    free_transfers = user_squad["free_transfers"]

    print(f"Current squad value: £{user_squad['squad_value']}m, bank: £{user_squad['bank']}m, "
          f"total budget: £{budget}m")
    print(f"Free transfers available: {free_transfers}")

    current_df = xp_df[xp_df["player_id"].isin(current_ids)]
    print(f"Current squad predicted xP: {round(current_df['predicted_xp'].sum(), 2)}")

    print("\n=== Solving transfer scenarios ===")
    scenarios = suggest_transfers(xp_df, current_ids, budget, free_transfers)

    for key, scenario in scenarios.items():
        label = "Best move within free transfers" if key == "free" else f"Best {key.replace('_', ' ')} (paid)"
        print(f"\n--- {label} ---")
        if scenario is None:
            print("  Not worth it - doesn't beat the cheaper option.")
            continue
        if not scenario["transfers"]:
            print("  No transfers recommended (squad is already optimal within budget).")
        for t in scenario["transfers"]:
            print(f"  [{t['position']}] {t['out_name']} ({t['out_team']}, £{t['out_price']}m, "
                  f"{t['out_xp']} xP) -> {t['in_name']} ({t['in_team']}, £{t['in_price']}m, "
                  f"{t['in_xp']} xP) | price {t['price_change']:+.1f}m, xP gain {t['xp_gain']:+.2f}")
        print(f"  Transfers used: {scenario['n_transfers']}, hits: {scenario['hits']} "
              f"(-{scenario['penalty']} pts)")
        print(f"  Raw xP gain: {scenario['raw_xp_gain']:+.2f}, Net xP gain after penalty: "
              f"{scenario['net_xp_gain']:+.2f}")

    print("\n=== Wildcard rebuild (unlimited transfers, no penalty) ===")
    wildcard = suggest_wildcard(xp_df, current_ids, budget)
    print(f"  Transfers used: {wildcard['n_transfers']}")
    print(f"  Raw xP gain vs current squad: {wildcard['raw_xp_gain']:+.2f}")
    print(f"  New squad total cost: £{wildcard['total_cost']}m")

    # Sanity/constraint checks on the 'free' scenario
    free_scenario = scenarios["free"]
    pos_counts = free_scenario["squad_df"]["position"].value_counts().to_dict()
    assert pos_counts == SQUAD_POSITION_LIMITS, f"FORMATION VIOLATED: {pos_counts}"
    assert free_scenario["total_cost"] <= budget + 1e-6, "BUDGET VIOLATED"
    team_counts = free_scenario["squad_df"]["team"].value_counts()
    assert (team_counts <= MAX_PER_TEAM).all(), f"MAX-PER-TEAM VIOLATED: {team_counts.to_dict()}"
    print("\n[OK] transfer scenario respects budget, formation, and max-3-per-team constraints.")
