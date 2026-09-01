import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import GradientBoostingClassifier


from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score

from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

from data.features.dataset import load_dataset
from stages.train.dataset import split_xy

dataset = load_dataset()
train, test = train_test_split(dataset, test_size=0.1)

X_train, y_train, _groups = split_xy(train)
X_test, y_test, _groups_test = split_xy(test)

#encoding categorical features
encoder = OneHotEncoder(sparse_output=False).set_output(transform="pandas")
train_encoded = encoder.fit_transform(X_train[["weight_class"]])
test_encoded = encoder.transform(X_test[["weight_class"]])
X_train = pd.concat([X_train.drop(columns="weight_class"), train_encoded], axis=1)
X_test = pd.concat([X_test.drop(columns="weight_class"), test_encoded], axis=1)

# imputing NaNs
# fit on training data, reuse it on test
imputer = SimpleImputer(strategy="median").set_output(transform="pandas")
X_train = imputer.fit_transform(X_train)
X_test = imputer.transform(X_test)

scaler = MinMaxScaler().set_output(transform="pandas")
X_train_NB = scaler.fit_transform(X_train)
X_test_NB = scaler.transform(X_test)



# scaling features: mean of 0, sd of 1
# again fit on training data, reuse on test
scaler = StandardScaler().set_output(transform="pandas")
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

def logistic_reg():
    model = LogisticRegression().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "logistic regression", y_pred, y_proba

def dt():
    model = DecisionTreeClassifier().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "decision tree", y_pred, y_proba

def random_forest():
    model = RandomForestClassifier().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "random forest", y_pred, y_proba

def gb():
    model = GradientBoostingClassifier().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "gradient boosting", y_pred, y_proba

def perceptron():
    columns = ["d_td_acc", "b_ctrl_time_sec_pr"]
    X_train_2 = X_train[columns]
    X_test_2 = X_test[columns]
    model = MLPClassifier().fit(X_train_2, y_train)
    y_pred = model.predict(X_test_2)
    y_proba = model.predict_proba(X_test_2)[:, 1]
    return "perceptron", y_pred, y_proba

def nb():
    model = GaussianNB().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return "naive bayes", y_pred, y_proba

def mlp():
    columns = [col for col in X_train if col.startswith("d")]
    X_train_2 = X_train[columns]
    X_test_2 = X_test[columns]
    model = MLPClassifier(hidden_layer_sizes=(100,1000,100)).fit(X_train_2, y_train)
    y_pred = model.predict(X_test_2)
    y_proba = model.predict_proba(X_test_2)[:, 1]
    return "mlp", y_pred, y_proba

if __name__ == "__main__":
    print("eval on ", len(y_test), " examples")
    results = [
        logistic_reg(),
        dt(),
        perceptron(),
        nb(),
        mlp(),
        random_forest(),
        gb()
    ]

    table = []
    for name, y_pred, y_proba in results:
        matrix = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = matrix.ravel().tolist()

        table.append({
            "model": name,
            "auc": roc_auc_score(y_test, y_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "recall": tp / (tp + fn),
            "precision": tp / (tp + fp),
        })
    print(pd.DataFrame(table))

