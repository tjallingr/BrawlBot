import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, roc_auc_score

from data.features.dataset import load_dataset
from stages.train.dataset import split_xy
from stages.train.pipeline import RANDOM_STATE, build_preprocessing_pipeline, time_group_splits

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
TOP_N_FEATURES = 15
CANDIDATE_PARAMS = [
    {"n_estimators": 200, "max_depth": None},
    {"n_estimators": 200, "max_depth": 8},
    {"n_estimators": 500, "max_depth": 8},
]

df = load_dataset()
df = df[df["date"] >= date(1999, 7, 16)].reset_index(drop=True)

cut = int(len(df) * 0.85)
dev_df = df.iloc[:cut].reset_index(drop=True)
holdout_df = df.iloc[cut:]

X_dev, y_dev, _ = split_xy(dev_df)
X_holdout, y_holdout, _ = split_xy(holdout_df)


def select_top_features(n=TOP_N_FEATURES):
    pipeline = build_preprocessing_pipeline()
    X = pipeline.fit_transform(X_dev)
    ranker = RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE).fit(X, y_dev)
    ranked = pd.Series(ranker.feature_importances_, index=X.columns).sort_values(ascending=False)
    return list(ranked.head(n).index)


def tune_hyperparameters(features):
    all_columns = build_preprocessing_pipeline().fit_transform(X_dev).columns
    folds = []
    for train_idx, test_idx in time_group_splits(dev_df, n_splits=3):
        pipeline = build_preprocessing_pipeline()
        X_train = pipeline.fit_transform(X_dev.loc[train_idx]).reindex(columns=all_columns, fill_value=0)
        X_test = pipeline.transform(X_dev.loc[test_idx]).reindex(columns=all_columns, fill_value=0)
        folds.append((X_train[features], y_dev.loc[train_idx], X_test[features], y_dev.loc[test_idx]))

    best_params, best_auc = None, -1
    for params in CANDIDATE_PARAMS:
        aucs = []
        for X_train, y_train, X_test, y_test in folds:
            model = RandomForestClassifier(random_state=RANDOM_STATE, **params).fit(X_train, y_train)
            aucs.append(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
        mean_auc = sum(aucs) / len(aucs)
        if mean_auc > best_auc:
            best_params, best_auc = params, mean_auc

    return best_params, best_auc


def evaluate_on_holdout(pipeline, model, features):
    X_test = pipeline.transform(X_holdout).reindex(columns=pipeline.fit_transform(X_dev).columns, fill_value=0)
    y_pred = model.predict(X_test[features])
    y_proba = model.predict_proba(X_test[features])[:, 1]

    matrix = confusion_matrix(y_holdout, y_pred)
    tn, fp, fn, tp = matrix.ravel().tolist()
    observed, predicted = calibration_curve(y_holdout, y_proba, n_bins=10)

    return {
        "auc": roc_auc_score(y_holdout, y_proba),
        "accuracy": accuracy_score(y_holdout, y_pred),
        "recall": tp / (tp + fn),
        "precision": tp / (tp + fp) if (tp + fp) else 0.0,
        "brier": brier_score_loss(y_holdout, y_proba),
        "calibration": list(zip(predicted.tolist(), observed.tolist())),
    }


if __name__ == "__main__":
    features = select_top_features()
    params, dev_auc = tune_hyperparameters(features)
    print(f"selected {len(features)} features, best params {params}, dev CV AUC {dev_auc:.4f}")

    pipeline = build_preprocessing_pipeline()
    X_train_full = pipeline.fit_transform(X_dev)
    model = RandomForestClassifier(random_state=RANDOM_STATE, **params).fit(X_train_full[features], y_dev)

    metrics = evaluate_on_holdout(pipeline, model, features)
    print(f"holdout AUC {metrics['auc']:.4f}  accuracy {metrics['accuracy']:.4f}  brier {metrics['brier']:.4f}")

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"pipeline": pipeline, "model": model, "features": features}, MODELS_DIR / "random_forest_v1.joblib")

    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "dev_rows": len(dev_df),
        "holdout_rows": len(holdout_df),
        "features": features,
        "params": params,
        "dev_cv_auc": dev_auc,
        "holdout_metrics": metrics,
    }
    (MODELS_DIR / "random_forest_v1.json").write_text(json.dumps(metadata, indent=2))
