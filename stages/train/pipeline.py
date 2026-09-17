from datetime import date

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data.features.dataset import load_dataset
from stages.train.dataset import split_xy

RANDOM_STATE = 42

BASE_NAMES = [
    "slpm", "sapm", "power_ratio", "td_def", "td_acc", "td_edge", "striking_edge",
    "age_years", "reach_cm", "is_orthodox", "is_southpaw", "is_switch",
    "win_rate", "days_since_last", "sig_str_acc", "odds_prob",
]


def build_preprocessing_pipeline():
    encode = ColumnTransformer(
        [("weight_class", OneHotEncoder(sparse_output=False, handle_unknown="ignore"), ["weight_class"])],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    return Pipeline([
        ("encode", encode),          # encoding categorical features
        ("impute", SimpleImputer(strategy="median")),  # imputing NaNs, fit on training data, reuse it on test
        ("scale", StandardScaler()),  # scaling features: mean of 0, sd of 1, again fit on training data, reuse on test
    ]).set_output(transform="pandas")


def time_group_splits(frame, n_splits=5, group_col="fight_id", date_col="date"):
    # a fight's two mirrored rows must stay on the same side of every fold
    # (group_col), and a fold's train must never contain dates after its own
    fight_order = (
        frame[[group_col, date_col]]
        .drop_duplicates(subset=group_col)
        .sort_values(date_col)[group_col]
        .to_numpy()
    )
    blocks = np.array_split(fight_order, n_splits + 1)
    for k in range(n_splits):
        train_ids = np.concatenate(blocks[: k + 1])
        test_ids = blocks[k + 1]
        train_idx = frame.index[frame[group_col].isin(train_ids)].to_numpy()
        test_idx = frame.index[frame[group_col].isin(test_ids)].to_numpy()
        yield train_idx, test_idx


def select_columns(all_columns, base_names=BASE_NAMES):
    return [
        c for c in all_columns
        if c.removeprefix("r_").removeprefix("b_").removeprefix("d_") in base_names or c.startswith("weight_class_")
    ]


def load_dev_holdout(cutoff=date(1999, 7, 16), dev_frac=0.85):
    df = load_dataset()
    df = df[df["date"] >= cutoff].reset_index(drop=True)

    cut = int(len(df) * dev_frac)
    dev_df = df.iloc[:cut].reset_index(drop=True)
    holdout_df = df.iloc[cut:]

    X_dev, y_dev, _ = split_xy(dev_df)
    X_holdout, y_holdout, _ = split_xy(holdout_df)

    all_columns = build_preprocessing_pipeline().fit_transform(X_dev).columns
    columns = select_columns(all_columns)

    return df, dev_df, holdout_df, X_dev, y_dev, X_holdout, y_holdout, all_columns, columns
