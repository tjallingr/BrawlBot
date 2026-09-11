import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42


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
