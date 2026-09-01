from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer

from data.features.dataset import load_dataset
from stages.train.dataset import split_xy

dataset = load_dataset()
train, test = train_test_split(dataset, test_size=0.2)

X_train, y_train, _groups = split_xy(train)
X_test, y_test, _groups_test = split_xy(test)

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
    print("logistic regressor")
    model = LogisticRegression().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

def dt():
    print("decision tree")
    model = DecisionTreeClassifier().fit(X_train, y_train)
    y_pred = model.predict_proba(X_test)
    accuracy = roc_auc_score(y_test, y_pred)
    print(accuracy)

def perceptron():
    print("perceptron")
    columns = ["d_td_acc", "b_ctrl_time_sec_pr"]
    X_train_2 = X_train[columns]
    X_test_2 = X_test[columns]  
    model = MLPClassifier().fit(X_train_2, y_train)
    y_pred = model.predict(X_test_2)
    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

def nb():
    print("naive bayes")
    model = GaussianNB().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

def mlp():
    print("mlp")
    columns = [col for col in X_train if col.startswith("d")]
    print(columns)
    X_train_2 = X_train[columns]
    X_test_2 = X_test[columns]  
    model = MLPClassifier(hidden_layer_sizes=(100,1000,100)).fit(X_train_2, y_train)
    y_pred = model.predict(X_test_2)
    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

if __name__ == "__main__":
    print("accuracy eval on ", len(y_test), " examples")
    # logistic_reg()
    dt()
    perceptron()
    nb()
    mlp()

