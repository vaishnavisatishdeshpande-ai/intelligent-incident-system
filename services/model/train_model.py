import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier

from services.model.real_data_loader import load_nab_data


FEATURES = ["avg_latency", "error_rate", "latency_change"]
MODEL_PATH = "services/model/xgb_model.pkl"
METRICS_PATH = "services/model/model_metrics.json"


def load_data():
    df = load_nab_data("data/nab_cpu.csv")
    X = df[FEATURES]
    y = df["failure"]
    return X, y


def train():
    X, y = load_data()

    print("Original class distribution:")
    print(y.value_counts())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    X_train_res, y_train_res = SMOTE().fit_resample(X_train, y_train)

    print("\nAfter SMOTE (train only):")
    print(pd.Series(y_train_res).value_counts())

    model = XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.1,
        eval_metric="logloss",
    )

    model.fit(X_train_res, y_train_res)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob),
    }

    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nMetrics:")
    for k, v in metrics.items():
        print(f"{k.upper():<10}: {round(v, 4)}")

    joblib.dump(model, MODEL_PATH)

    with open(METRICS_PATH, "w") as f:
        json.dump({k: round(v, 4) for k, v in metrics.items()}, f, indent=2)

    print("\nModel saved")
    print("Metrics saved")


if __name__ == "__main__":
    train()