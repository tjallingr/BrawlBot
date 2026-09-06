from datetime import date
from itertools import combinations
import pandas as pd
from data.features.dataset import load_dataset

from stages.train.dataset import split_xy

from sklearn.tree import DecisionTreeClassifier

from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score


df = load_dataset()

# first cut off the first 3 ish years: different sports format, not that applicable on current 5min round system
df = df[df["date"] >= date(1999, 7, 16)]

# 80 5 15 split
frac_train = int((0.85*len(df)))
frac_val = int((0.05*len(df)))
train = df.iloc[:frac_train]
val = df.iloc[frac_train:frac_train+frac_val]
test = df.iloc[frac_train+frac_val:]

X_train, y_train, _ = split_xy(train)
X_val, y_val, _ = split_xy(val)
X_test, y_test, _ = split_xy(test)

# encode
encoder = OneHotEncoder(sparse_output=False).set_output(transform="pandas")
train_encoded = encoder.fit_transform(X_train[["weight_class"]])
val_encoded = encoder.transform(X_val[["weight_class"]])
test_encoded = encoder.transform(X_test[["weight_class"]])

X_train = pd.concat([X_train.drop(columns="weight_class"), train_encoded], axis=1)
X_test = pd.concat([X_test.drop(columns="weight_class"), test_encoded], axis=1)
X_val = pd.concat([X_val.drop(columns="weight_class"), val_encoded], axis=1)

# impute
imputer = SimpleImputer(strategy="median").set_output(transform="pandas")
X_train = imputer.fit_transform(X_train)
X_test = imputer.transform(X_test)
X_val = imputer.transform(X_val)

# scale (not really necessary for dt)
scaler = StandardScaler().set_output(transform="pandas")
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)
X_val = scaler.transform(X_val)

dt = DecisionTreeClassifier()

def test_features():
    table = []
    for feature in X_train.columns:
        dt.fit(X_train[[feature]], y_train)
        y_pred = dt.predict(X_test[[feature]])
        y_proba = dt.predict_proba(X_test[[feature]])[:, 1]

        matrix = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = matrix.ravel().tolist()

        table.append({
            "feature": feature,
            "auc": roc_auc_score(y_test, y_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "recall": tp / (tp + fn),
            "precision": tp / (tp + fp),
        })
    return pd.DataFrame(table).sort_values("auc", ascending=False)


def forward_select(max_features=None):
    """
    greedy forward selection
    """
    chosen = []
    remaining = list(X_train.columns)
    table = []

    while remaining and (max_features is None or len(chosen) < max_features):
        best_feature, best_row = None, None
        for feature in remaining:
            cols = chosen + [feature]
            dt.fit(X_train[cols], y_train)
            y_pred = dt.predict(X_test[cols])
            y_proba = dt.predict_proba(X_test[cols])[:, 1]

            matrix = confusion_matrix(y_test, y_pred)
            tn, fp, fn, tp = matrix.ravel().tolist()
            auc = roc_auc_score(y_test, y_proba)

            if best_row is None or auc > best_row["auc"]:
                best_feature = feature
                best_row = {
                    "n_features": len(cols),
                    "added": feature,
                    "auc": auc,
                    "accuracy": accuracy_score(y_test, y_pred),
                    "recall": tp / (tp + fn),
                    "precision": tp / (tp + fp),
                }

        chosen.append(best_feature)
        remaining.remove(best_feature)
        table.append(best_row)

    return chosen, pd.DataFrame(table)


def triplet_bruteforce():
    """Brute force every 3-feature combination. C(76, 3) = 70,300 fits --
    at ~69ms/fit (measured from forward_select's own run) that's roughly 80
    minutes. Feasible for size 3 only; size 4 would already be ~24 hours."""
    table = []
    for f1, f2, f3 in combinations(X_train.columns, 3):
        cols = [f1, f2, f3]
        dt.fit(X_train[cols], y_train)
        y_pred = dt.predict(X_test[cols])
        y_proba = dt.predict_proba(X_test[cols])[:, 1]

        matrix = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = matrix.ravel().tolist()

        table.append({
            "feature_1": f1,
            "feature_2": f2,
            "feature_3": f3,
            "auc": roc_auc_score(y_test, y_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "recall": tp / (tp + fn),
            "precision": tp / (tp + fp),
        })
    return pd.DataFrame(table).sort_values("auc", ascending=False)


if __name__ == "__main__":
    test_features().to_csv("stages/train/feature_scores.txt", index=False)

    chosen, history = forward_select()
    history.to_csv("stages/train/forward_selection.txt", index=False)
    print("forward selection order:", chosen)

    # triplet_bruteforce().to_csv("stages/train/triplet_scores.txt", index=False)