from datetime import date
from pathlib import Path

import click
import joblib
import pandas as pd

from core.name_match import best_fighter_match
from data.features.dataset import build_fighter_histories, implied_probability
from data.features.fight import matchup_features
from data.features.fighter import fighter_features
from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL = MODELS_DIR / "random_forest_v1.joblib"


def predict_matchup(
    fighter_a: str,
    fighter_b: str,
    weight_class: str = "",
    odds_a: int | None = None,
    odds_b: int | None = None,
    model_path: Path = DEFAULT_MODEL,
) -> tuple[str, float, str, float]:
    session = get_session(get_engine())
    fighters = fighter_repo.get_all(session)
    names = fighter_repo.get_normalized_names(session)

    a_id = best_fighter_match(fighter_a, names)
    b_id = best_fighter_match(fighter_b, names)
    if a_id is None or b_id is None:
        raise ValueError(f"no fighter found matching '{fighter_a if a_id is None else fighter_b}'")

    histories = build_fighter_histories(session)
    today = date.today()
    a_features = fighter_features(histories[a_id], fighters.get(a_id), today)
    b_features = fighter_features(histories[b_id], fighters.get(b_id), today)
    a_features["odds_prob"] = implied_probability(odds_a) if odds_a is not None else None
    b_features["odds_prob"] = implied_probability(odds_b) if odds_b is not None else None

    row = {"weight_class": weight_class, **matchup_features(a_features, b_features)}
    X = pd.DataFrame([row])

    bundle = joblib.load(model_path)
    X_transformed = bundle["pipeline"].transform(X)
    proba = bundle["model"].predict_proba(X_transformed[bundle["features"]])[:, 1][0]

    return fighters[a_id].name_raw, proba, fighters[b_id].name_raw, 1 - proba


@click.command()
@click.argument("fighter_a")
@click.argument("fighter_b")
@click.option("--weight-class", default="", help="Weight class of the matchup, e.g. 'Lightweight'.")
@click.option("--odds-a", type=int, default=None, help="Fighter A's moneyline, e.g. -150 or 130.")
@click.option("--odds-b", type=int, default=None, help="Fighter B's moneyline, e.g. -150 or 130.")
@click.option("--model", "model_path", type=click.Path(path_type=Path), default=DEFAULT_MODEL)
def predict(fighter_a: str, fighter_b: str, weight_class: str, odds_a: int | None, odds_b: int | None, model_path: Path):
    try:
        name_a, proba_a, name_b, proba_b = predict_matchup(fighter_a, fighter_b, weight_class, odds_a, odds_b, model_path)
    except ValueError as error:
        raise click.ClickException(str(error))

    click.echo(f"{name_a}: {proba_a:.1%}")
    click.echo(f"{name_b}: {proba_b:.1%}")


if __name__ == "__main__":
    predict()
