import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
import joblib
from services.model.real_data_loader import load_nab_data

# ================================
# 📊 LOAD REAL DATA
# ================================

df = load_nab_data("data/nab_cpu.csv")

# ✅ FIXED: correct column mapping
X = df[["latency", "error"]]
y = df["failure"]

print("Original class distribution:")
print(y.value_counts())


# ================================
# ⚠️ SPLIT FIRST (avoid leakage)
# ================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# ================================
# ⚖️ SMOTE ONLY ON TRAIN
# ================================

smote = SMOTE()
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

print("\nAfter SMOTE (train only):")
print(pd.Series(y_train_res).value_counts())


# ================================
# 🚀 TRAIN MODEL
# ================================

model = XGBClassifier(
    n_estimators=120,
    max_depth=4,
    learning_rate=0.1,
    eval_metric="logloss"
)

model.fit(X_train_res, y_train_res)


# ================================
# 📊 EVALUATION (REAL TEST SET)
# ================================

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

print("ROC-AUC:", roc_auc_score(y_test, y_prob))


# ================================
# 💾 SAVE MODEL
# ================================

joblib.dump(model, "services/model/xgb_model.pkl")

print("\n✅ Model saved!")