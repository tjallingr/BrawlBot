from pathlib import Path

import pandas as pd

from data.features.dataset import DEFAULT_DATASET_PATH, load_dataset

TARGET_COLUMN = "red_won"
GROUP_COLUMN = "fight_id"
NON_FEATURE_COLUMNS = (GROUP_COLUMN, TARGET_COLUMN)


def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    X = frame.drop(columns=list(NON_FEATURE_COLUMNS))
    y = frame[TARGET_COLUMN]
    groups = frame[GROUP_COLUMN]
    return X, y, groups


def load_xy(path: Path = DEFAULT_DATASET_PATH) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    return split_xy(load_dataset(path))
