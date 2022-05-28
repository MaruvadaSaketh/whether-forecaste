# -*- coding: utf-8 -*-
"""Untitled7.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1iIU3wjC97XqsMzKrMhIBgz_5rp14-CFv
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np 
import pandas as pd 

# plotting
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
matplotlib.rcParams['figure.dpi'] = 100
sns.set(rc={'figure.figsize':(11.7,8.27)})
sns.set(style="whitegrid")
# %matplotlib inline

# ml
from sklearn.metrics import accuracy_score, recall_score, ConfusionMatrixDisplay, classification_report, auc, precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
import joblib

def print_col_type(df):
    non_num_df = df.select_dtypes(include=['object'])
    num_df = df.select_dtypes(exclude=['object'])
    '''separates non-numeric and numeric columns'''
    print("Object columns:")
    for col in non_num_df:
        print(f"{col}")
    print("")
    print("Numeric columns:")
    for col in num_df:
        print(f"{col}")

def missing_cols(df):
    '''prints out columns with its amount of missing values with its %'''
    total = 0
    for col in df.columns:
        missing_vals = df[col].isnull().sum()
        pct = df[col].isna().mean() * 100
        total += missing_vals
        if missing_vals != 0:
          print('{} => {} [{}%]'.format(col, df[col].isnull().sum(), round(pct, 2)))
    
    if total == 0:
        print("no missing values")

train_a = pd.read_csv("region_A_train.csv")
train_b = pd.read_csv("region_B_train.csv")
train_c = pd.read_csv("region_C_train.csv")
train_d = pd.read_csv("region_D_train.csv")
train_e = pd.read_csv("region_E_train.csv")

test_a = pd.read_csv("region_A_test.csv")
test_b = pd.read_csv("region_B_test.csv")
test_c = pd.read_csv("region_C_test.csv")
test_d = pd.read_csv("region_D_test.csv")
test_e = pd.read_csv("region_E_test.csv")

labels_df = pd.read_csv("solution_train.csv")

train_a.info()

train_all = pd.concat([train_a ,train_b ,train_c ,train_d ,train_e], keys=["A", "B", "C", "D", "E"])
train_all

train_all_lvls = train_all.reset_index()
train_all_lvls.rename(columns = {"level_0": "region"}, inplace=True)
train_all_lvls.drop(columns=['level_1'], inplace=True)
train_all_lvls.head()

sns.countplot(x = 'label', data = labels_df, palette="Set1");

train_all_lvls.columns[2:]

fig, axes = plt.subplots(5,2,figsize=(14, 30), dpi=100)

for i, col_name in enumerate(train_all_lvls.columns[2:]):
    if train_all_lvls[col_name].dtype == 'O':
        train_all_lvls.groupby('region')[col_name].hist(ax=axes[i%5][i//5], alpha=0.6);
        axes[i%5][i//5].legend(["A", "B", "C", "D", "E"]);
    else:
        train_all_lvls.groupby('region')[col_name].plot(ax=axes[i%5][i//5], alpha=0.7);
        axes[i%5][i//5].legend();
    axes[i%5][i//5].set_title(f'{col_name}', fontsize=13);
    plt.subplots_adjust(hspace=0.45)

missing_cols(train_all_lvls)

plt.figure(figsize=(10, 6))
sns.heatmap(train_all_lvls.isnull(), yticklabels=False, cmap='viridis', cbar=False);

train_all_lvls['min.atmos.pressure'].hist();

mean_atmos = train_all_lvls['min.atmos.pressure'].mean()
train_all_lvls.fillna(mean_atmos, inplace=True)

train_all_lvls = train_all_lvls.merge(labels_df, on="date")

train_all_lvls.select_dtypes('object').columns

le = LabelEncoder()
le.fit(train_all_lvls['label'])
le_name_map = dict(zip(le.classes_, le.transform(le.classes_)))
le_name_map

BEAUFORT = [
    (0, 0, 0.3),
    (1, 0.3, 1.6),
    (2, 1.6, 3.4),
    (3, 3.4, 5.5),
    (4, 5.5, 8),
    (5, 8, 10.8),
    (6, 10.8, 13.9),
    (7, 13.9, 17.2),
    (8, 17.2, 20.8),
    (9, 20.8, 24.5),
    (10, 24.5, 28.5),
    (11, 28.5, 33),
    (12, 33, 200),
]


def feature_eng(df):
    le = LabelEncoder()
    
    cat_cols = df.select_dtypes("object").columns[2:]

    for col in cat_cols:
        if df[col].dtype == "object":
            df[col] = le.fit_transform(df[col])
    for item in BEAUFORT:
        df.loc[
            (df["avg.wind.speed"] * 1.944 >= item[1]) & (df["avg.wind.speed"] * 1.944 < item[2]),
            "avg_beaufort_scale",
        ] = item[0]
        df.loc[
            (df["max.wind.speed"] * 1.944 >= item[1]) & (df["max.wind.speed"] * 1.944 < item[2]),
            "max_beaufort_scale",
        ] = item[0]

    df['avg_beaufort_scale'] = df['avg_beaufort_scale'].astype(int)
    df['max_beaufort_scale'] = df['max_beaufort_scale'].astype(int)

    return df

train = feature_eng(train_all_lvls)

train.head()

train = train.pivot_table(index=["date", "label"], columns="region")
train = pd.DataFrame(train.to_records())
train.head()

def replace_all(text):
    d = { "('": "", "', '": "_", "')" : "",}
    for i, j in d.items():
        text = text.replace(i, j)
    return text

# ('avg.temp', 'A') -> avg.temp_A

test_str = "('avg.temp', 'A')"
replace_all(test_str)

train.columns = list(map(replace_all, train.columns))

X, y = train.drop(["label", "date"], axis=1), train[["label"]].values.flatten()

cat_feats = X.select_dtypes(include=['int64']).columns.to_list()
cat_idx = [X.columns.get_loc(col) for col in cat_feats]
for col in cat_feats:
    X[col] = pd.Categorical(X[col])

X_train, X_eval, y_train, y_eval = train_test_split(
    X, y, test_size=0.25, random_state=0)

clf = lgb.LGBMClassifier()
clf.fit(X_train, y_train)

y_pred=clf.predict(X_eval.values)

class_names = le_name_map.keys()

titles_options = [
    ("Confusion matrix, without normalization", None),
    ("Normalized confusion matrix", "true"),
]
for title, normalize in titles_options:
    fig, ax = plt.subplots(figsize=(10, 10))

    disp = ConfusionMatrixDisplay.from_estimator(
        clf,
        X_eval,
        y_eval,
        display_labels=class_names,
        cmap=plt.cm.Blues,
        normalize=normalize,
        ax = ax
    )
    disp.ax_.set_title(title)
    disp.ax_.grid(False)

    print(title)
    print(disp.confusion_matrix)

print(classification_report(y_pred, y_eval))

feature_imp = pd.DataFrame(sorted(zip(clf.feature_importances_,X.columns)), columns=['Value','Feature'])

plt.figure(figsize=(20, 15))
sns.barplot(x="Value", y="Feature", data=feature_imp.sort_values(by="Value", ascending=False))
plt.title('LightGBM Features')
plt.tight_layout()

joblib.dump(clf, 'lgb1.pkl')

X = train.drop('date', axis=1)
for col in cat_feats:
    X[col] = pd.Categorical(X[col])

inv_map = {v: k for k, v in le_name_map.items()}
inv_map