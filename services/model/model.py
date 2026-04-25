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
        """Predict anomaly or normal."""
        if not self.trained:
            return "NOT_READY"

        vector = np.array([[
            features["avg_latency"],
            features["error_rate"]
        ]])

        result = self.model.predict(vector)

        return "ANOMALY" if result[0] == -1 else "NORMAL"