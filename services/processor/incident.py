class IncidentScorer:
    """Combines multiple signals into a single incident score."""

    def compute_score(self, features, alerts, ml_prediction, confidence):
        score = 0

        # --- Latency contribution ---
        latency = features.get("avg_latency", 0)
        if latency > 300:
            score += 2
        if latency > 450:
            score += 3

        # --- Error rate contribution ---
        error_rate = features.get("error_rate", 0)
        if error_rate > 0.3:
            score += 2
        if error_rate > 0.6:
            score += 3

        # --- Rule alerts ---
        score += len(alerts) * 2

        if ml_prediction == "ANOMALY":
            score += int(confidence * 5)

        return score

    def get_severity(self, score):
        if score >= 8:
            return "CRITICAL"
        elif score >= 5:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        return "LOW"