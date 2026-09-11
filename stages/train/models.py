import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import GradientBoostingClassifier

from sklearn.calibration import calibration_curve

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score, brier_score_loss

from data.features.dataset import load_dataset
from stages.train.dataset import split_xy
from stages.train.pipeline import RANDOM_STATE, build_preprocessing_pipeline, time_group_splits

df = load_dataset().reset_index(drop=True)
X, y, _groups = split_xy(df)

def logistic_reg(X_train, y_train, X_test, y_test):
    model = LogisticRegression(random_state=RANDOM_STATE).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "logistic regression", y_pred, y_proba

def dt(X_train, y_train, X_test, y_test):
    model = DecisionTreeClassifier(random_state=RANDOM_STATE).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "decision tree", y_pred, y_proba

def random_forest(X_train, y_train, X_test, y_test):
    model = RandomForestClassifier(random_state=RANDOM_STATE).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "random forest", y_pred, y_proba

def gb(X_train, y_train, X_test, y_test):
    model = GradientBoostingClassifier(random_state=RANDOM_STATE).fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "gradient boosting", y_pred, y_proba

def perceptron(X_train, y_train, X_test, y_test):
    columns = ["d_td_acc", "b_ctrl_time_sec_pr"]
    model = MLPClassifier(random_state=RANDOM_STATE).fit(X_train[columns], y_train)
    y_pred = model.predict(X_test[columns])
    y_proba = model.predict_proba(X_test[columns])[:, 1]
    return "perceptron", y_pred, y_proba

def nb(X_train, y_train, X_test, y_test):
    model = GaussianNB().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "naive bayes", y_pred, y_proba

def mlp(X_train, y_train, X_test, y_test):
    columns = [col for col in X_train if col.startswith("d")]
    model = MLPClassifier(hidden_layer_sizes=(100,1000,100), random_state=RANDOM_STATE).fit(X_train[columns], y_train)
    y_pred = model.predict(X_test[columns])
    y_proba = model.predict_proba(X_test[columns])[:, 1]
    return "mlp", y_pred, y_proba

MODEL_FUNCS = [logistic_reg, dt, perceptron, nb, mlp, random_forest, gb]

def cross_validate_model(model_func, n_splits=5):
    fold_rows = []
    last_fold = None
    for train_idx, test_idx in time_group_splits(df, n_splits=n_splits):
        X_train_raw, X_test_raw = X.loc[train_idx], X.loc[test_idx]
        y_train, y_test = y.loc[train_idx], y.loc[test_idx]

        pipeline = build_preprocessing_pipeline()
        X_train = pipeline.fit_transform(X_train_raw)
        X_test = pipeline.transform(X_test_raw)

        name, y_pred, y_proba = model_func(X_train, y_train, X_test, y_test)

        matrix = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = matrix.ravel().tolist()

        # calibration (Brier score): mean squared error between the predicted
        # probability and the actual 0/1 outcome. 0 is perfect, 0.25 is what
        # you get by always predicting 0.5. Unlike AUC (which only checks
        # whether winners are RANKED above losers) this checks whether the
        # probability number itself is trustworthy -- a model can rank
        # perfectly while still saying "90%" when the true rate is 60%.
        fold_rows.append({
            "auc": roc_auc_score(y_test, y_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "recall": tp / (tp + fn),
            "precision": tp / (tp + fp),
            "brier": brier_score_loss(y_test, y_proba),
        })
        last_fold = (y_test, y_proba)

    folds = pd.DataFrame(fold_rows)
    return name, folds, last_fold

if __name__ == "__main__":
    table = []
    calibration_candidates = {}
    for model_func in MODEL_FUNCS:
        name, folds, last_fold = cross_validate_model(model_func)
        calibration_candidates[name] = last_fold
        row = {"model": name}
        for col in folds.columns:
            row[f"{col}_mean"] = folds[col].mean()
            row[f"{col}_std"] = folds[col].std()
        table.append(row)

    leaderboard = pd.DataFrame(table).sort_values("auc_mean", ascending=False)
    print(leaderboard)

    best_model = leaderboard.iloc[0]["model"]
    y_test, y_proba = calibration_candidates[best_model]
    observed, predicted = calibration_curve(y_test, y_proba, n_bins=10)
    print(f"\ncalibration curve for {best_model} (most recent CV fold):")
    print(pd.DataFrame({"predicted_avg": predicted, "observed_rate": observed}))
