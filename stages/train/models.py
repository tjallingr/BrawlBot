from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.tree import DecisionTreeClassifier
from data.features.dataset import load_dataset
from stages.train.dataset import split_xy
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


dataset = load_dataset()
train, test = train_test_split(dataset, test_size=0.2)

X_train, y_train, _groups = split_xy(train)
X_test, y_test, _groups_test = split_xy(test)

# imputing NaNs
# fit on training data, reuse it on test
imputer = SimpleImputer(strategy="median")
X_train = imputer.fit_transform(X_train)
X_test = imputer.transform(X_test)

# scaling features: mean of 0, sd of 1
# again fit on training data, reuse on test
scaler = StandardScaler()
X = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

def logistic_reg():
    model = LogisticRegression().fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

def dt():


if __name__ == "__main__":
    logistic_reg()

