import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import tensorflow as tf
from tensorflow import keras
from sklearn.calibration import calibration_curve
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, roc_auc_score

from stages.train.dataset import split_xy
from stages.train.pipeline import RANDOM_STATE, build_preprocessing_pipeline, load_dev_holdout, time_group_splits

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
EPOCHS = 200
CANDIDATE_PARAMS = [
    {"hidden": (32, 16), "lr": 1e-3},
    {"hidden": (64, 32), "lr": 1e-3},
    {"hidden": (32, 16), "lr": 5e-4},
]

df, dev_df, holdout_df, X_dev, y_dev, X_holdout, y_holdout, ALL_COLUMNS, COLUMNS = load_dev_holdout()


def _fit(X_train, y_train, hidden, lr, epochs=EPOCHS):
    tf.random.set_seed(RANDOM_STATE)
    model = keras.Sequential(
        [keras.Input(shape=(X_train.shape[1],))]
        + [keras.layers.Dense(size, activation="relu") for size in hidden]
        + [keras.layers.Dense(1, activation="sigmoid")]
    )
    model.compile(optimizer=keras.optimizers.Adam(lr), loss="binary_crossentropy")
    X_np, y_np = X_train.to_numpy(dtype="float32"), y_train.to_numpy(dtype="float32")
    model.fit(X_np, y_np, epochs=epochs, batch_size=len(X_np), verbose=0)
    return model


def _predict_proba(model, X):
    return model.predict(X.to_numpy(dtype="float32"), verbose=0).ravel()


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
            model = _fit(X_train, y_train, params["hidden"], params["lr"])
            aucs.append(roc_auc_score(y_test, _predict_proba(model, X_test)))
        mean_auc = sum(aucs) / len(aucs)
        if mean_auc > best_auc:
            best_params, best_auc = params, mean_auc

    return best_params, best_auc


def evaluate_on_holdout(pipeline, model, features):
    X_test = pipeline.transform(X_holdout).reindex(columns=pipeline.fit_transform(X_dev).columns, fill_value=0)
    y_proba = _predict_proba(model, X_test[features])
    y_pred = (y_proba >= 0.5).astype(int)

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
    features = COLUMNS
    params, dev_auc = tune_hyperparameters(features)
    print(f"using {len(features)} chosen features, best params {params}, dev CV AUC {dev_auc:.4f}")

    pipeline = build_preprocessing_pipeline()
    X_train_full = pipeline.fit_transform(X_dev)
    model = _fit(X_train_full[features], y_dev, params["hidden"], params["lr"])

    metrics = evaluate_on_holdout(pipeline, model, features)
    print(f"holdout AUC {metrics['auc']:.4f}  accuracy {metrics['accuracy']:.4f}  brier {metrics['brier']:.4f}")

    X_all, y_all, _ = split_xy(df)
    final_pipeline = build_preprocessing_pipeline()
    X_all_transformed = final_pipeline.fit_transform(X_all)
    final_model = _fit(X_all_transformed[features], y_all, params["hidden"], params["lr"])

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"pipeline": final_pipeline, "features": features}, MODELS_DIR / "nn_v1_pipeline.joblib")
    final_model.save(MODELS_DIR / "nn_v1.keras")

    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "dev_rows": len(dev_df),
        "holdout_rows": len(holdout_df),
        "shipped_model_rows": len(df),
        "features": features,
        "params": params,
        "dev_cv_auc": dev_auc,
        "holdout_metrics": metrics,
    }
    (MODELS_DIR / "nn_v1.json").write_text(json.dumps(metadata, indent=2))
