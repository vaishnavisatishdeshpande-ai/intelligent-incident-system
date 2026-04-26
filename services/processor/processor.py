from collections import deque
import json

from services.feature_store.feast_client import FeastClient
from kafka import KafkaConsumer
from prometheus_client import start_http_server, Counter, Gauge

from services.processor.incident import IncidentScorer
from services.model.model import AnomalyModel
from services.producer.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
)

# -----------------------------
# Metrics
# -----------------------------
EVENTS_PROCESSED = Counter("events_processed_total", "Total events processed")
ALERTS_TRIGGERED = Counter("alerts_triggered_total", "Total alerts triggered")
ML_ANOMALIES = Counter("ml_anomalies_total", "Total ML anomalies detected")

LATENCY_GAUGE = Gauge("avg_latency", "Average latency")
ERROR_RATE_GAUGE = Gauge("error_rate", "Error rate")

WINDOW_SIZE = 10


# -----------------------------
# Feature Engine
# -----------------------------
class FeatureEngine:
    def __init__(self):
        self.events = deque(maxlen=WINDOW_SIZE)
        self.prev_avg_latency = None
        self.baseline_latency = None
        self.baseline_error = None

    def add_event(self, event):
        if isinstance(event, dict):
            self.events.append(event)

    def compute_features(self):
        if not self.events:
            return None

        latencies = [e.get("latency", 0) for e in self.events]
        errors = [e.get("error", 0) for e in self.events]

        avg_latency = sum(latencies) / len(latencies)
        error_rate = sum(errors) / len(errors)

        latency_change = 0.0 if self.prev_avg_latency is None else avg_latency - self.prev_avg_latency
        self.prev_avg_latency = avg_latency

        if self.baseline_latency is None:
            self.baseline_latency = avg_latency
            self.baseline_error = error_rate
        else:
            alpha = 0.98
            self.baseline_latency = alpha * self.baseline_latency + (1 - alpha) * avg_latency
            self.baseline_error = alpha * self.baseline_error + (1 - alpha) * error_rate

        return {
            "avg_latency": avg_latency,
            "error_rate": error_rate,
            "latency_change": latency_change,
            "baseline_latency": self.baseline_latency,
            "baseline_error": self.baseline_error,
        }


# -----------------------------
# Rule-based Detector
# -----------------------------
class AnomalyDetector:
    def __init__(self):
        self.latency_threshold = 300
        self.error_threshold = 0.3

    def detect(self, features):
        alerts = []

        if features["avg_latency"] > self.latency_threshold:
            alerts.append({
                "type": "HIGH_LATENCY",
                "severity": "HIGH",
                "value": features["avg_latency"]
            })

        if features["error_rate"] > self.error_threshold:
            alerts.append({
                "type": "HIGH_ERROR_RATE",
                "severity": "HIGH",
                "value": features["error_rate"]
            })

        return alerts


# -----------------------------
# Reason Generator
# -----------------------------
class ReasonGenerator:
    def generate_reason(self, features, alerts, ml_result):
        reasons = {}

        if alerts:
            for alert in alerts:
                reasons[alert["type"]] = {
                    "value": alert.get("value")
                }

        if ml_result.get("prediction") == "ANOMALY":
            reasons["ml_signal"] = f"model detected anomaly (confidence={ml_result.get('confidence')})"

        if not reasons:
            reasons["note"] = "No significant anomalies detected"

        return reasons


# -----------------------------
# Kafka Consumer
# -----------------------------
def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )


# -----------------------------
# Main Processor
# -----------------------------
def main():
    print("Starting processor...")
    start_http_server(8000)

    consumer = create_consumer()
    engine = FeatureEngine()
    detector = AnomalyDetector()
    model = AnomalyModel()
    scorer = IncidentScorer()
    reason_generator = ReasonGenerator()
    feast_client = FeastClient()

    try:
        for message in consumer:
            try:
                event = message.value
                EVENTS_PROCESSED.inc()

                # -----------------------------
                # Feature Fetch (Feast + fallback)
                # -----------------------------
                features = feast_client.get_features(event["service"])

                if not features or features.get("avg_latency") is None:
                    engine.add_event(event)
                    features = engine.compute_features()
                    if not features:
                        continue

                # -----------------------------
                # Metrics
                # -----------------------------
                LATENCY_GAUGE.set(features.get("avg_latency", 0))
                ERROR_RATE_GAUGE.set(features.get("error_rate", 0))

                # -----------------------------
                # Rule Alerts
                # -----------------------------
                alerts = detector.detect(features)

                # -----------------------------
                # ML Pipeline
                # -----------------------------
                model.add_data(features)

                if len(model.data) > 30:
                    model.train()

                ml_result = model.predict(features) or {}
                prediction = ml_result.get("prediction", "NOT_READY")
                confidence = float(ml_result.get("confidence", 0.0))

                if prediction == "ANOMALY":
                    ML_ANOMALIES.inc()

                # -----------------------------
                # Fusion (simple + clean)
                # -----------------------------
                final_alerts = alerts.copy()

                if prediction == "ANOMALY" and not alerts:
                    final_alerts.append({
                        "type": "ML_ANOMALY",
                        "severity": "HIGH" if confidence > 0.9 else "MEDIUM",
                        "confidence": confidence,
                    })

                # -----------------------------
                # Scoring
                # -----------------------------
                score = scorer.compute_score(
                    features,
                    final_alerts,
                    prediction,
                    confidence
                )

                severity = scorer.get_severity(score)

                # -----------------------------
                # Reasoning
                # -----------------------------
                reason = reason_generator.generate_reason(
                    features,
                    final_alerts,
                    ml_result
                )

                incident = {
                    "score": score,
                    "severity": severity,
                    "features": features,
                    "alerts": final_alerts,
                    "ml_signal": {
                        "prediction": prediction,
                        "confidence": confidence,
                    },
                    "reason": reason
                }

                print(json.dumps(incident, indent=2))

                if final_alerts:
                    ALERTS_TRIGGERED.inc()

            except Exception as e:
                print("Processing error:", str(e))

    except KeyboardInterrupt:
        print("Shutting down processor...")


if __name__ == "__main__":
    main()