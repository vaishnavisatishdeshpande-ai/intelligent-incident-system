import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier

from services.model.real_data_loader import load_nab_data


df = load_nab_data("data/nab_cpu.csv")

X = df[["avg_latency", "error_rate", "latency_change"]]
y = df["failure"]

print("Original class distribution:")
print(y.value_counts())


X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


smote = SMOTE()
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

print("\nAfter SMOTE (train only):")
print(pd.Series(y_train_res).value_counts())


model = XGBClassifier(
    n_estimators=120,
    max_depth=4,
    learning_rate=0.1,
    eval_metric="logloss"
)

model.fit(X_train_res, y_train_res)


y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_prob)

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print("\nMetrics:")
print(f"Accuracy  : {round(accuracy, 4)}")
print(f"Precision : {round(precision, 4)}")
print(f"Recall    : {round(recall, 4)}")
print(f"F1 Score  : {round(f1, 4)}")
print(f"ROC-AUC   : {round(roc_auc, 4)}")


joblib.dump(model, "services/model/xgb_model.pkl")


metrics = {
    "accuracy": round(accuracy, 4),
    "precision": round(precision, 4),
    "recall": round(recall, 4),
    "f1_score": round(f1, 4),
    "roc_auc": round(roc_auc, 4)
}

with open("services/model/model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("\nModel saved")
print("Metrics saved")