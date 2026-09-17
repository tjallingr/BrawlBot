from datetime import date
from pathlib import Path

import click
import joblib
import pandas as pd

from core.name_match import best_fighter_match
from data.features.dataset import build_fighter_histories
from data.features.fight import matchup_features
from data.features.fighter import fighter_features
from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL = MODELS_DIR / "random_forest_v1.joblib"


@click.command()
@click.argument("fighter_a")
@click.argument("fighter_b")
@click.option("--weight-class", default="", help="Weight class of the matchup, e.g. 'Lightweight'.")
@click.option("--model", "model_path", type=click.Path(path_type=Path), default=DEFAULT_MODEL)
def predict(fighter_a: str, fighter_b: str, weight_class: str, model_path: Path):
    session = get_session(get_engine())
    fighters = fighter_repo.get_all(session)
    names = fighter_repo.get_normalized_names(session)

    a_id = best_fighter_match(fighter_a, names)
    b_id = best_fighter_match(fighter_b, names)
    if a_id is None or b_id is None:
        raise click.ClickException(f"no fighter found matching '{fighter_a if a_id is None else fighter_b}'")

    histories = build_fighter_histories(session)
    today = date.today()
    a_features = fighter_features(histories[a_id], fighters.get(a_id), today)
    b_features = fighter_features(histories[b_id], fighters.get(b_id), today)
    a_features["odds_prob"] = None
    b_features["odds_prob"] = None

    row = {"weight_class": weight_class, **matchup_features(a_features, b_features)}
    X = pd.DataFrame([row])

    bundle = joblib.load(model_path)
    X_transformed = bundle["pipeline"].transform(X)
    proba = bundle["model"].predict_proba(X_transformed[bundle["features"]])[:, 1][0]

    click.echo(f"{fighters[a_id].name_raw}: {proba:.1%}")
    click.echo(f"{fighters[b_id].name_raw}: {1 - proba:.1%}")


if __name__ == "__main__":
    predict()
