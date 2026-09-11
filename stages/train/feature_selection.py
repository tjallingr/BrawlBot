from datetime import date
import pandas as pd
from data.features.dataset import load_dataset

from stages.train.dataset import split_xy
from stages.train.pipeline import RANDOM_STATE, build_preprocessing_pipeline, time_group_splits

from sklearn.tree import DecisionTreeClassifier

from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score


df = load_dataset()

# first cut off the first 3 ish years: different sports format, not that applicable on current 5min round system
df = df[df["date"] >= date(1999, 7, 16)].reset_index(drop=True)

X, y, _ = split_xy(df)

# fixed column list so every fold has the same columns to select by name:
# an early fold's train window has not seen every weight class yet (eg the
# women's divisions only start in 2013), so its own one-hot output would
# otherwise be missing those columns entirely rather than zero-filled
ALL_COLUMNS = build_preprocessing_pipeline().fit_transform(X).columns

folds = []
for train_idx, test_idx in time_group_splits(df, n_splits=5):
    X_train_raw, X_test_raw = X.loc[train_idx], X.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]

    pipeline = build_preprocessing_pipeline()
    X_train = pipeline.fit_transform(X_train_raw).reindex(columns=ALL_COLUMNS, fill_value=0)
    X_test = pipeline.transform(X_test_raw).reindex(columns=ALL_COLUMNS, fill_value=0)

    folds.append((X_train, y_train, X_test, y_test))

dt = DecisionTreeClassifier(random_state=RANDOM_STATE)

def score_columns(columns):
    rows = []
    for X_train, y_train, X_test, y_test in folds:
        dt.fit(X_train[columns], y_train)
        y_pred = dt.predict(X_test[columns])
        y_proba = dt.predict_proba(X_test[columns])[:, 1]

        matrix = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = matrix.ravel().tolist()

        rows.append({
            "auc": roc_auc_score(y_test, y_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "recall": tp / (tp + fn),
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
        })
    return pd.DataFrame(rows).mean().to_dict()

def test_features():
    table = []
    for feature in ALL_COLUMNS:
        table.append({"feature": feature, **score_columns([feature])})
    return pd.DataFrame(table).sort_values("auc", ascending=False)


def forward_select(max_features=None):
    """
    greedy forward selection
    """
    chosen = []
    remaining = list(ALL_COLUMNS)
    table = []

    while remaining and (max_features is None or len(chosen) < max_features):
        best_feature, best_row = None, None
        for feature in remaining:
            cols = chosen + [feature]
            scores = score_columns(cols)

            if best_row is None or scores["auc"] > best_row["auc"]:
                best_feature = feature
                best_row = {"n_features": len(cols), "added": feature, **scores}

        chosen.append(best_feature)
        remaining.remove(best_feature)
        table.append(best_row)

    return chosen, pd.DataFrame(table)


if __name__ == "__main__":
    test_features().to_csv("stages/train/feature_scores.txt", index=False)

    chosen, history = forward_select()
    history.to_csv("stages/train/forward_selection.txt", index=False)
    print("forward selection order:", chosen)
