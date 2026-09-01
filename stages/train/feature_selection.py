from datetime import date

from data.features.dataset import load_dataset

from sklearn.tree import DecisionTreeClassifier



# first ill check with a simple model (dt or log reg) what the influence of each feature is. 
# pruning least useful ones immeediateeely?
# then checking interactions using grid search.
# then using domain knowledge to craft some and testing those.


# important: this wont be a simple test split anymore, ill use val test train split and split on time to mimic
# actual usage.

df = load_dataset()

# first cut off the first 3 ish years: different sports format, not that applicable on current 5min round system
df = df[df["date"] >= date(1999, 7, 16)].drop(columns=["date"])

# 80 5 15 split
frac_train = int((0.85*len(df)))
frac_val = int((0.05*len(df)))
train = df.iloc[:frac_train]
val = df.iloc[frac_train:frac_train+frac_val]
test = df.iloc[frac_train+frac_val:]

# encode

# impute

# scale (not really necessary for dt)

dt = DecisionTreeClassifier()

def test_features():
    X_train, y_train, _groups = split_xy(train)
    for feature in X_train.columns():
        dt.fit(feature, y_train)



if __name__ == "__main__":
    