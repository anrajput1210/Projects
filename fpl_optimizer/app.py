"""Streamlit UI for the FPL Team Optimizer.

Two modes:
  - Build New Squad: pick an optimal 15-man squad from scratch under budget.
  - Optimize My Current Squad: pull a squad via FPL Team ID (or enter it
    manually) and get ranked transfer suggestions.
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from data.fetch_fpl_data import (
    build_players_dataframe,
    fetch_all_player_summaries,
    fetch_bootstrap_static,
    fetch_fixtures,
    get_next_gameweek,
    get_user_squad,
    match_player_names,
)
from models.predict_xp import predict_xp
from optimizer.squad_builder import MAX_PER_TEAM, SQUAD_POSITION_LIMITS, build_squad
from optimizer.transfer_optimizer import suggest_transfers, suggest_wildcard

st.set_page_config(page_title="FPL Team Optimizer", layout="wide")

DISPLAY_COLS = ["name", "team_short", "position", "price", "predicted_xp"]
DISPLAY_COL_LABELS = {
    "name": "Player", "team_short": "Team", "position": "Pos",
    "price": "Price (£m)", "predicted_xp": "Predicted xP",
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_pool():
    """Fetches bootstrap/fixtures/player-summaries and builds the predicted
    xP DataFrame. Cached for an hour in Streamlit's memory on top of the
    data layer's own disk cache.
    """
    bootstrap = fetch_bootstrap_static()
    fixtures = fetch_fixtures()
    summaries = fetch_all_player_summaries(bootstrap)
    players_df = build_players_dataframe(bootstrap, fixtures, summaries)
    xp_df = predict_xp(players_df)
    return bootstrap, xp_df


@st.cache_data(ttl=300, show_spinner=False)
def load_user_squad_cached(team_id: int, _bootstrap: dict):
    return get_user_squad(team_id, _bootstrap)


def render_squad_table(df: pd.DataFrame, title: str):
    st.subheader(title)
    display = df[DISPLAY_COLS].rename(columns=DISPLAY_COL_LABELS)
    st.dataframe(display, width="stretch", hide_index=True)


def render_build_result(result: dict):
    col1, col2, col3 = st.columns(3)
    col1.metric("Total cost", f"£{result['total_cost']}m")
    col2.metric("Squad predicted xP", result["squad_predicted_points"])
    captain_row = result["squad_df"][result["squad_df"]["player_id"] == result["captain_id"]].iloc[0]
    effective = result["starting_xi_predicted_points"] + captain_row["predicted_xp"]
    col3.metric("Effective GW xP (XI + captain)", round(effective, 2))

    render_squad_table(
        result["squad_df"].sort_values(["position", "predicted_xp"], ascending=[True, False]),
        "Full 15-man squad",
    )

    st.subheader("Recommended starting XI")
    xi = result["starting_xi_df"]
    formation = xi["position"].value_counts()
    formation_str = "-".join(str(formation.get(p, 0)) for p in ["DEF", "MID", "FWD"])
    st.caption(f"Formation: {formation.get('GKP', 0)}-{formation_str} (GKP-DEF-MID-FWD)")
    render_squad_table(xi, "Starting XI")

    captain = result["squad_df"][result["squad_df"]["player_id"] == result["captain_id"]].iloc[0]
    vice = result["squad_df"][result["squad_df"]["player_id"] == result["vice_captain_id"]].iloc[0]
    st.markdown(
        f"**Captain:** {captain['name']} ({captain['predicted_xp']} xP -> "
        f"{round(captain['predicted_xp'] * 2, 2)} as captain)  \n"
        f"**Vice-captain:** {vice['name']} ({vice['predicted_xp']} xP)"
    )


def render_transfer_scenario(scenario: dict | None, label: str):
    st.subheader(label)
    if scenario is None:
        st.info("Not worth it - doesn't beat a cheaper option.")
        return

    if not scenario["transfers"]:
        st.success("No changes recommended - your squad is already optimal within budget.")
    else:
        transfers_df = pd.DataFrame(scenario["transfers"])[
            ["position", "out_name", "out_team", "out_price", "out_xp",
             "in_name", "in_team", "in_price", "in_xp", "price_change", "xp_gain"]
        ].rename(columns={
            "position": "Pos", "out_name": "Out", "out_team": "Out Team",
            "out_price": "Out £m", "out_xp": "Out xP", "in_name": "In",
            "in_team": "In Team", "in_price": "In £m", "in_xp": "In xP",
            "price_change": "Price Δ", "xp_gain": "xP Gain",
        })
        st.dataframe(transfers_df, width="stretch", hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transfers", scenario["n_transfers"])
    c2.metric("Hit", f"-{scenario['penalty']:.0f} pts" if scenario["hits"] else "None")
    c3.metric("Raw xP gain", f"{scenario['raw_xp_gain']:+.2f}")
    c4.metric("Net xP gain", f"{scenario['net_xp_gain']:+.2f}")


def main():
    st.title("FPL Team Optimizer")

    with st.spinner("Loading live FPL data (players, fixtures, form)..."):
        try:
            bootstrap, xp_df = load_player_pool()
        except requests.RequestException as e:
            st.error(f"Failed to load FPL data: {e}")
            st.stop()

    target_gw = get_next_gameweek(bootstrap)
    st.sidebar.caption(f"Predicting expected points for Gameweek {target_gw}")

    mode = st.sidebar.radio("Mode", ["Build New Squad", "Optimize My Current Squad"])

    if mode == "Build New Squad":
        st.sidebar.subheader("Squad Builder Settings")
        budget = st.sidebar.number_input(
            "Budget (£m)", min_value=80.0, max_value=110.0, value=100.0, step=0.5
        )
        if st.sidebar.button("Build Optimal Squad", type="primary"):
            with st.spinner("Solving squad selection ILP..."):
                try:
                    st.session_state["build_result"] = build_squad(xp_df, budget=budget)
                except ValueError as e:
                    st.error(str(e))
                    st.session_state.pop("build_result", None)

        if "build_result" in st.session_state:
            render_build_result(st.session_state["build_result"])
        else:
            st.info("Set a budget in the sidebar and click **Build Optimal Squad** to get started.")

    else:
        st.sidebar.subheader("Your Squad")
        entry_method = st.sidebar.radio("How do you want to enter your squad?", ["FPL Team ID", "Manual entry"])

        current_squad_ids: set[int] | None = None
        squad_source_df: pd.DataFrame | None = None
        default_bank, default_free_transfers = 0.0, 1

        if entry_method == "FPL Team ID":
            team_id_str = st.sidebar.text_input("FPL Team ID", placeholder="e.g. 1234567")
            if st.sidebar.button("Fetch My Squad", type="primary"):
                if not team_id_str.strip().isdigit():
                    st.sidebar.error("Team ID must be numeric.")
                else:
                    team_id = int(team_id_str.strip())
                    with st.spinner(f"Fetching squad for Team ID {team_id}..."):
                        try:
                            st.session_state["user_squad"] = load_user_squad_cached(team_id, bootstrap)
                        except requests.HTTPError as e:
                            st.sidebar.error(
                                f"Couldn't find Team ID {team_id}. Double-check the numeric ID "
                                f"from your FPL team URL. ({e})"
                            )
                            st.session_state.pop("user_squad", None)
                        except requests.RequestException as e:
                            st.sidebar.error(f"Network error fetching your squad: {e}")
                            st.session_state.pop("user_squad", None)

            user_squad = st.session_state.get("user_squad")
            if user_squad:
                st.sidebar.success(f"Loaded: {user_squad['manager_name']} - {user_squad['team_name']}")
                current_squad_ids = set(user_squad["player_ids"])
                default_bank = user_squad["bank"]
                default_free_transfers = user_squad["free_transfers"]
                squad_source_df = xp_df[xp_df["player_id"].isin(current_squad_ids)]

        else:
            st.sidebar.caption("Paste 15 player names, one per line (surname is usually enough).")
            names_text = st.sidebar.text_area("Player names", height=200)
            if st.sidebar.button("Match Players"):
                names = [n.strip() for n in names_text.splitlines() if n.strip()]
                st.session_state["manual_matches"] = match_player_names(names, bootstrap)
                st.session_state.pop("manual_resolved_ids", None)

            matches = st.session_state.get("manual_matches")
            if matches:
                st.subheader("Confirm your squad")
                resolved_ids = []
                for name, candidates in matches.items():
                    if not candidates:
                        st.warning(f"No match found for **{name}** - it will be excluded.")
                        continue
                    options = {}
                    for c in candidates:
                        confidence = "exact" if c["match_score"] == 1.0 else f"{int(c['match_score'] * 100)}% match"
                        label = f"{c['web_name']} ({c['team_short']}, {c['position']}) - {confidence}"
                        options[label] = c["player_id"]
                    choice = st.selectbox(f"'{name}' ->", list(options.keys()), key=f"match_{name}")
                    resolved_ids.append(options[choice])
                st.session_state["manual_resolved_ids"] = resolved_ids

                if len(resolved_ids) != 15:
                    st.warning(f"You've resolved {len(resolved_ids)}/15 players. Add more names to continue.")
                else:
                    current_squad_ids = set(resolved_ids)
                    squad_source_df = xp_df[xp_df["player_id"].isin(current_squad_ids)]

        if current_squad_ids and squad_source_df is not None and len(squad_source_df) == 15:
            squad_value = round(squad_source_df["price"].sum(), 1)
            st.sidebar.subheader("Budget")
            bank = st.sidebar.number_input("Bank (£m)", min_value=0.0, value=float(default_bank), step=0.1)
            free_transfers = st.sidebar.number_input(
                "Free transfers", min_value=1, max_value=5, value=int(default_free_transfers)
            )
            budget = squad_value + bank

            st.subheader("Your current squad")
            c1, c2, c3 = st.columns(3)
            c1.metric("Squad value", f"£{squad_value}m")
            c2.metric("Bank", f"£{bank}m")
            c3.metric("Current predicted xP", round(squad_source_df["predicted_xp"].sum(), 2))
            render_squad_table(
                squad_source_df.sort_values(["position", "predicted_xp"], ascending=[True, False]),
                "Current squad",
            )

            if st.button("Suggest Transfers", type="primary"):
                with st.spinner("Solving transfer scenarios..."):
                    try:
                        st.session_state["transfer_scenarios"] = suggest_transfers(
                            xp_df, current_squad_ids, budget, int(free_transfers)
                        )
                        st.session_state["wildcard_scenario"] = suggest_wildcard(
                            xp_df, current_squad_ids, budget
                        )
                    except ValueError as e:
                        st.error(str(e))
                        st.session_state.pop("transfer_scenarios", None)
                        st.session_state.pop("wildcard_scenario", None)

            if "transfer_scenarios" in st.session_state:
                scenarios = st.session_state["transfer_scenarios"]
                render_transfer_scenario(scenarios.get("free"), "Best move within free transfers")
                for key, scenario in scenarios.items():
                    if key == "free":
                        continue
                    hits = key.replace("hit_", "")
                    render_transfer_scenario(scenario, f"Best {hits}-hit option (paid transfers)")

                st.divider()
                render_transfer_scenario(
                    st.session_state.get("wildcard_scenario"), "Wildcard / Free Hit rebuild (unlimited transfers)"
                )
        elif entry_method == "FPL Team ID" and "user_squad" not in st.session_state:
            st.info("Enter your FPL Team ID in the sidebar and click **Fetch My Squad**.")


if __name__ == "__main__":
    main()
