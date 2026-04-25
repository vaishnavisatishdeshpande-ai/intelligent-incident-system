from sklearn.ensemble import IsolationForest
import numpy as np


class AnomalyModel:
    """ML-based anomaly detection using Isolation Forest."""

    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.trained = False
        self.data = []

    def add_data(self, features):
        """Store feature vector."""
        vector = [
            features["avg_latency"],
            features["error_rate"]
        ]
        self.data.append(vector)

    def train(self):
        """Train model once enough data is available."""
        if len(self.data) < 20:
            return

        X = np.array(self.data)
        self.model.fit(X)
        self.trained = True

    def predict(self, features):
        """Predict anomaly with adjustable threshold"""

        if not self.trained:
            return {"prediction": "NOT_READY", "confidence": 0.0}

        vector = [[
            features["avg_latency"],
            features["error_rate"]
        ]]

        prob = self.model.predict_proba(vector)[0][1]

        # 🔥 Controlled threshold (key change)
        threshold = 0.7

        prediction = "ANOMALY" if prob > threshold else "NORMAL"

        return {
            "prediction": prediction,
            "confidence": round(prob, 2)
        }