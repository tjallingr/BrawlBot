import numpy as np
import pandas as pd

from stages.train.pipeline import build_preprocessing_pipeline, time_group_splits


def _toy_frame(n_fights=40):
    rows = []
    for i in range(n_fights):
        for corner, stat in (("a", float(i)), ("b", None)):
            rows.append({
                "fight_id": i,
                "date": pd.Timestamp("2000-01-01") + pd.Timedelta(days=i),
                "weight_class": "Heavyweight" if i % 2 == 0 else "Lightweight",
                "stat": stat,
            })
    return pd.DataFrame(rows)


def test_pipeline_leaves_no_nan_and_keeps_original_column_names():
    X = _toy_frame()[["weight_class", "stat"]]
    transformed = build_preprocessing_pipeline().fit_transform(X)
    assert not transformed.isna().any().any()
    assert "stat" in transformed.columns


def test_pipeline_transform_on_test_reuses_train_fit_without_error():
    X = _toy_frame()[["weight_class", "stat"]]
    train, test = X.iloc[:60], X.iloc[60:]
    pipeline = build_preprocessing_pipeline()
    pipeline.fit(train)
    transformed_test = pipeline.transform(test)
    assert not transformed_test.isna().any().any()


def test_time_group_splits_never_splits_a_fight_across_train_and_test():
    frame = _toy_frame()
    for train_idx, test_idx in time_group_splits(frame, n_splits=4):
        train_fights = set(frame.loc[train_idx, "fight_id"])
        test_fights = set(frame.loc[test_idx, "fight_id"])
        assert not (train_fights & test_fights)


def test_time_group_splits_never_trains_on_the_future():
    frame = _toy_frame()
    for train_idx, test_idx in time_group_splits(frame, n_splits=4):
        assert frame.loc[train_idx, "date"].max() <= frame.loc[test_idx, "date"].min()


def test_time_group_splits_first_train_plus_all_test_folds_cover_every_row_once():
    frame = _toy_frame()
    splits = list(time_group_splits(frame, n_splits=4))
    first_train = set(splits[0][0].tolist())
    all_test = set(np.concatenate([test_idx for _, test_idx in splits]).tolist())
    assert not (first_train & all_test)
    assert (first_train | all_test) == set(range(len(frame)))
