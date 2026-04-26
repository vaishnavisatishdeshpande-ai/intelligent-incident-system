import numpy as np
import joblib
from sklearn.ensemble import IsolationForest


class AnomalyModel:
    def __init__(self):
        self.if_model = IsolationForest(contamination=0.1)
        self.if_trained = False
        self.data = []

        self.xgb_model = None
        try:
            self.xgb_model = joblib.load("services/model/xgb_model.pkl")
        except Exception:
            pass

    def _vector(self, features):
        return np.array([[
            features["avg_latency"],
            features["error_rate"],
            features["latency_change"]
        ]])

    def add_data(self, features):
        self.data.append([
            features["avg_latency"],
            features["error_rate"],
            features["latency_change"]
        ])

    def train(self):
        if len(self.data) < 20:
            return
        self.if_model.fit(np.array(self.data))
        self.if_trained = True

    def predict(self, features):
        if not self.if_trained:
            return {
                "prediction": "NOT_READY",
                "confidence": 0.0,
                "signals": {}
            }

        vector = self._vector(features)

        latency = features["avg_latency"]
        error = features["error_rate"]

        # Isolation Forest
        if_pred = self.if_model.predict(vector)[0]
        if_anomaly = (if_pred == -1)

        if_score = self.if_model.decision_function(vector)[0]
        if_conf = float(round(1 / (1 + np.exp(-if_score * 5)), 2))

        # XGBoost
        xgb_anomaly = False
        xgb_conf = 0.0

        if self.xgb_model is not None:
            prob = self.xgb_model.predict_proba(vector)[0][1]
            xgb_conf = float(round(min(prob, 0.9), 2))
            xgb_anomaly = prob > 0.9

            if latency < 250 and error < 0.3:
                xgb_anomaly = False
                xgb_conf = 0.0

        # Fusion
        prediction = "NORMAL"

        if xgb_anomaly and if_anomaly:
            prediction = "ANOMALY"

        elif xgb_anomaly and (latency > 320 or error > 0.45):
            prediction = "ANOMALY"

        elif if_anomaly and if_conf > 0.95:
            prediction = "ANOMALY"

        if prediction == "ANOMALY":
            confidence = float(round(max(if_conf, xgb_conf), 2))
        else:
            confidence = float(round(min(if_conf, xgb_conf), 2))

        return {
            "prediction": prediction,
            "confidence": confidence,
            "signals": {
                "if": {
                    "anomaly": if_anomaly,
                    "confidence": if_conf
                },
                "xgb": {
                    "anomaly": xgb_anomaly,
                    "confidence": xgb_conf
                }
            }
        }
