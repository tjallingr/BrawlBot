import json
from pathlib import Path

import pandas as pd

from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo
from data.storage.repositories import fights as fight_repo

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
METADATA_PATH = MODELS_DIR / "random_forest_v1.json"
HOLDOUT_REPORT_PATH = MODELS_DIR / "random_forest_v1_holdout.parquet"


def _fighter_names(session) -> dict[int, tuple[str, str]]:
    fighters = fighter_repo.get_all(session)
    return {
        fight.id: (fighters[fight.fighter_a_id].name_raw, fighters[fight.fighter_b_id].name_raw)
        for fight, _ in fight_repo.get_all_with_dates(session)
    }


def load_metrics() -> dict:
    return json.loads(METADATA_PATH.read_text())["holdout_metrics"]


def load_predictions() -> pd.DataFrame:
    """one row per holdout fight: the model's holdout-time prediction vs. the real outcome"""
    report = pd.read_parquet(HOLDOUT_REPORT_PATH).drop_duplicates(subset="fight_id")
    names = _fighter_names(get_session(get_engine()))

    return pd.DataFrame([
        {
            "date": row.date,
            "fighter_a": names[row.fight_id][0],
            "fighter_b": names[row.fight_id][1],
            "predicted_a_win_%": round(row.red_win_proba * 100, 1),
            "actual_winner": names[row.fight_id][0] if row.red_won else names[row.fight_id][1],
            "r_odds_prob": row.r_odds_prob,
            "b_odds_prob": row.b_odds_prob,
        }
        for row in report.itertuples()
    ]).sort_values("date", ascending=False)


def _payout(stake: float, market_prob: float, won: bool) -> float:
    return stake * (1 - market_prob) / market_prob if won else -stake


def simulate_betting(predictions: pd.DataFrame, flat_stake: float = 10.0, edge_stake_scale: float = 100.0) -> dict:
    """
    flat: bet flat_stake on whichever side the model favors.
    edge: bet edge_stake_scale * (model probability - market probability) on the side where that's positive,
    i.e. only where the model disagrees with the market in a profitable direction, sized by how much.
    Both treat median-across-sportsbooks implied probability as if it were the payout price directly
    (no separate vig adjustment), so real winnings would run a bit lower than this suggests.
    """
    usable = predictions.dropna(subset=["r_odds_prob", "b_odds_prob"])
    won_a = usable["actual_winner"] == usable["fighter_a"]
    model_a = usable["predicted_a_win_%"] / 100

    flat_profit, edge_profit, edge_bets = 0.0, 0.0, 0
    for model_p, market_a, market_b, won in zip(model_a, usable["r_odds_prob"], usable["b_odds_prob"], won_a):
        bet_a = model_p >= 0.5
        flat_profit += _payout(flat_stake, market_a if bet_a else market_b, won if bet_a else not won)

        edge_a, edge_b = model_p - market_a, (1 - model_p) - market_b
        if edge_a > 0:
            edge_profit += _payout(edge_stake_scale * edge_a, market_a, won)
            edge_bets += 1
        elif edge_b > 0:
            edge_profit += _payout(edge_stake_scale * edge_b, market_b, not won)
            edge_bets += 1

    return {
        "n_fights_with_odds": len(usable),
        "flat_stake": flat_stake,
        "flat_profit": round(flat_profit, 2),
        "edge_bets_placed": edge_bets,
        "edge_profit": round(edge_profit, 2),
    }
