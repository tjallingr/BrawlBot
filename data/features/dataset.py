from collections import defaultdict
from pathlib import Path

import pandas as pd

from data.features.fight import matchup_features
from data.features.fighter import FighterHistory, fighter_features
from data.features.fighter import ROUND_STAT_COLUMNS
from data.storage.repositories import fighters as fighter_repo
from data.storage.repositories import fights as fight_repo

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "sets" / "fights.parquet"


def compile_dataset(session, min_fights: int = 0) -> pd.DataFrame:
    """
        per fight: compile features for both fighters, add two entries with corners swapped
        (input position will not carry info this way)
    """
    fighters = fighter_repo.get_all(session)
    stats_by_fight_fighter, rounds_by_fight = _summarise_round_stats(fight_repo.get_all_round_stats(session))
    histories: dict[int, FighterHistory] = defaultdict(FighterHistory)

    rows = []
    for fight, fight_date in fight_repo.get_all_with_dates(session):
        if fight.winner_id is None:  # draws and no-contests carry no label
            continue
        a_id, b_id = fight.fighter_a_id, fight.fighter_b_id
        a_history, b_history = histories[a_id], histories[b_id]

        if min(a_history.fights, b_history.fights) >= min_fights:
            a_features = fighter_features(a_history, fighters.get(a_id), fight_date)
            b_features = fighter_features(b_history, fighters.get(b_id), fight_date)
            a_won = fight.winner_id == a_id
            for red, blue, won in ((a_features, b_features, a_won), (b_features, a_features, not a_won)):
                rows.append(
                    {
                        "fight_id": fight.id,
                        "date": fight_date,
                        "weight_class": fight.weight_class,
                        **matchup_features(red, blue),
                        "red_won": int(won),
                    }
                )

        rounds = rounds_by_fight.get(fight.id, fight.round or 0)
        for fighter_id, won in ((a_id, fight.winner_id == a_id), (b_id, fight.winner_id == b_id)):
            histories[fighter_id].record(
                fight_date, won, fight.method, rounds, stats_by_fight_fighter.get((fight.id, fighter_id))
            )

    return pd.DataFrame(rows)


def _summarise_round_stats(round_stats) -> tuple[dict[tuple[int, int], dict], dict[int, int]]:
    totals: dict[tuple[int, int], dict[str, float]] = {}
    rounds: dict[int, int] = {}
    for row in round_stats:
        fight_totals = totals.setdefault((row.fight_id, row.fighter_id), dict.fromkeys(ROUND_STAT_COLUMNS, 0.0))
        for name in ROUND_STAT_COLUMNS:
            value = getattr(row, name)
            if value is not None:
                fight_totals[name] += value
        rounds[row.fight_id] = max(rounds.get(row.fight_id, 0), row.round)
    return totals, rounds


def write_dataset(frame: pd.DataFrame, path: Path = DEFAULT_DATASET_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)
