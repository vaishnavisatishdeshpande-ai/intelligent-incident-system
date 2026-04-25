import numpy as np
import joblib
from sklearn.ensemble import IsolationForest


class AnomalyModel:
    """
    Hybrid ML model:
    - IsolationForest → unknown anomaly detection
    - XGBoost → learned failure prediction
    - Smart fusion → reduces noise
    """

    def __init__(self):
        # -----------------------------
        # Isolation Forest
        # -----------------------------
        self.if_model = IsolationForest(contamination=0.1)
        self.if_trained = False
        self.data = []

        # -----------------------------
        # XGBoost
        # -----------------------------
        try:
            self.xgb_model = joblib.load("services/model/xgb_model.pkl")
            self.xgb_available = True
        except Exception:
            print("⚠️ XGBoost model not found. Running IF-only mode.")
            self.xgb_available = False

    # -----------------------------
    # DATA COLLECTION
    # -----------------------------
    def add_data(self, features):
        vector = [
            features["avg_latency"],
            features["error_rate"]
        ]
        self.data.append(vector)

    # -----------------------------
    # TRAIN IF
    # -----------------------------
    def train(self):
        if len(self.data) < 20:
            return

        X = np.array(self.data)
        self.if_model.fit(X)
        self.if_trained = True

    # -----------------------------
    # PREDICT
    # -----------------------------
    def predict(self, features):
        if not self.if_trained:
            return {"prediction": "NOT_READY", "confidence": 0.0}

        vector = np.array([[
            features["avg_latency"],
            features["error_rate"]
        ]])

        latency = features["avg_latency"]
        error = features["error_rate"]

        # =====================================
        # 🔍 Isolation Forest
        # =====================================
        if_result = self.if_model.predict(vector)[0]
        if_anomaly = (if_result == -1)

        if_score = self.if_model.decision_function(vector)[0]
        if_conf = float(round(1 / (1 + np.exp(-if_score * 5)), 2))

        # =====================================
        # 🤖 XGBoost
        # =====================================
        xgb_conf = 0.0
        xgb_anomaly = False

        if self.xgb_available:
            prob = self.xgb_model.predict_proba(vector)[0][1]

            # stricter threshold (IMPORTANT)
            xgb_anomaly = prob > 0.90

            # reduce overconfidence
            xgb_conf = float(round(min(prob, 0.90), 2))

            # CONTEXT FILTER (VERY IMPORTANT)
            if latency < 250 and error < 0.3:
                xgb_anomaly = False
                xgb_conf = 0.0

        # =====================================
        # 🧠 FUSION (BALANCED)
        # =====================================
        prediction = "NORMAL"

        # 1. Strong agreement → highest trust
        if xgb_anomaly and if_anomaly:
            prediction = "ANOMALY"

        # 2. XGB alone only if strong + meaningful system signal
        elif xgb_anomaly and xgb_conf > 0.9 and (latency > 320 or error > 0.45):
            prediction = "ANOMALY"

        # 3. IF alone only if very strong deviation
        elif if_anomaly and if_conf > 0.95:
            prediction = "ANOMALY"

        # else NORMAL

        if prediction == "ANOMALY":
            final_conf = float(round(max(if_conf, xgb_conf), 2))
        else:
            final_conf = float(round(min(if_conf, xgb_conf), 2))

        return {
            "prediction": prediction,
            "confidence": final_conf,
            "signals": {
                "isolation_forest": {
                    "anomaly": if_anomaly,
                    "confidence": if_conf
                },
                "xgboost": {
                    "anomaly": xgb_anomaly,
                    "confidence": xgb_conf
                }
            }
        }