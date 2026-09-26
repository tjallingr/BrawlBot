from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from data.features.dataset import load_dataset
from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo
from data.storage.repositories import fights as fight_repo
from stages.train.dataset import split_xy
from stages.train.pipeline import TRAINING_CUTOFF, compute_metrics

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL = MODELS_DIR / "random_forest_v1.joblib"


def load_eval_frame(cutoff: date = TRAINING_CUTOFF) -> pd.DataFrame:
    """every fight on or after the training cutoff: never seen by the shipped model"""
    df = load_dataset()
    return df[df["date"] >= cutoff].reset_index(drop=True)


def _fighter_names(session) -> dict[int, tuple[str, str]]:
    fighters = fighter_repo.get_all(session)
    return {
        fight.id: (fighters[fight.fighter_a_id].name_raw, fighters[fight.fighter_b_id].name_raw)
        for fight, _ in fight_repo.get_all_with_dates(session)
    }


def evaluate(model_path=DEFAULT_MODEL) -> tuple[dict, pd.DataFrame]:
    eval_df = load_eval_frame()
    X, y, _ = split_xy(eval_df)

    bundle = joblib.load(model_path)
    X_transformed = bundle["pipeline"].transform(X)
    y_proba = bundle["model"].predict_proba(X_transformed[bundle["features"]])[:, 1]
    metrics = compute_metrics(y, y_proba)

    names = _fighter_names(get_session(get_engine()))
    table = eval_df.assign(red_win_proba=y_proba).drop_duplicates(subset="fight_id")
    predictions = pd.DataFrame([
        {
            "date": row.date,
            "fighter_a": names[row.fight_id][0],
            "fighter_b": names[row.fight_id][1],
            "predicted_a_win_%": round(row.red_win_proba * 100, 1),
            "actual_winner": names[row.fight_id][0] if row.red_won else names[row.fight_id][1],
        }
        for row in table.itertuples()
    ]).sort_values("date", ascending=False)

    return metrics, predictions
