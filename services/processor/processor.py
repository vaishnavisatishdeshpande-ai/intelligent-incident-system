from collections import deque
import json
from services.model.model import AnomalyModel

from kafka import KafkaConsumer

from services.producer.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
)

WINDOW_SIZE = 10


class FeatureEngine:
    """Processes incoming events and computes aggregated features."""

    def __init__(self):
        self.events = deque(maxlen=WINDOW_SIZE)

    def add_event(self, event):
        """Add a new event to the sliding window."""
        self.events.append(event)

    def compute_features(self):
        """Compute average latency and error rate."""
        if not self.events:
            return None

        latencies = [event["latency"] for event in self.events]
        errors = [event["error"] for event in self.events]

        avg_latency = sum(latencies) / len(latencies)
        error_rate = sum(errors) / len(errors)

        return {
            "avg_latency": avg_latency,
            "error_rate": error_rate,
        }


class AnomalyDetector:
    """Detects anomalies based on thresholds and assigns severity."""

    def __init__(self, latency_threshold=300, error_threshold=0.3):
        self.latency_threshold = latency_threshold
        self.error_threshold = error_threshold
        self.active_alerts = set()
        self.latency_breach_count = 0
        self.error_breach_count = 0
        self.breach_threshold = 3

    def detect(self, features):
        """Return alerts with severity, deduplication, and recovery handling."""
        alerts = []
        current_alerts = set()

        if not features:
            return alerts

        avg_latency = features.get("avg_latency")
        error_rate = features.get("error_rate")

        # --- Latency detection ---
        # --- Latency detection (with stability) ---
        if avg_latency is not None:
            if avg_latency > self.latency_threshold:
                self.latency_breach_count += 1
            else:
                self.latency_breach_count = 0

            if self.latency_breach_count >= self.breach_threshold:
                severity = "HIGH"
                if avg_latency > self.latency_threshold * 1.5:
                    severity = "CRITICAL"

                current_alerts.add("HIGH_LATENCY")

                if "HIGH_LATENCY" not in self.active_alerts:
                    alerts.append(
                        {
                            "type": "HIGH_LATENCY",
                            "severity": severity,
                            "value": avg_latency,
                            "threshold": self.latency_threshold,
                        }
                    )

        # --- Error rate detection ---
        # --- Error rate detection (with stability) ---
        if error_rate is not None:
            if error_rate > self.error_threshold:
                self.error_breach_count += 1
            else:
                self.error_breach_count = 0

            if self.error_breach_count >= self.breach_threshold:
                severity = "HIGH"
                if error_rate > self.error_threshold * 2:
                    severity = "CRITICAL"

                current_alerts.add("HIGH_ERROR_RATE")

                if "HIGH_ERROR_RATE" not in self.active_alerts:
                    alerts.append(
                        {
                            "type": "HIGH_ERROR_RATE",
                            "severity": severity,
                            "value": error_rate,
                            "threshold": self.error_threshold,
                        }
                    )
        # --- Recovery detection (FIXED: no duplication) ---
        resolved_alerts = self.active_alerts - current_alerts

        for alert_type in resolved_alerts:
            alerts.append(
                {
                    "type": alert_type,
                    "status": "RESOLVED",
                }
            )

        # --- Update state ---
        self.active_alerts = current_alerts

        return alerts

def create_consumer():
    """Create Kafka consumer for system events."""
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda message: json.loads(message.decode("utf-8")),
        auto_offset_reset="earliest",
    )


def main():
    """Main processing loop."""
    print("Starting processor...")

    consumer = create_consumer()
    engine = FeatureEngine()
    detector = AnomalyDetector()
    model = AnomalyModel()

    for message in consumer:
        event = message.value
        print("Received event:", event)

        engine.add_event(event)
        features = engine.compute_features()

        if features:
            print("Computed features:", features)

            # Rule-based alerts
            alerts = detector.detect(features)

            if alerts:
                print("ALERT:", alerts)

            # ML pipeline
            model.add_data(features)
            model.train()

            prediction = model.predict(features)
            print("ML Prediction:", prediction)
            final_alerts = [alert.copy() for alert in alerts]

            # --- Smart ML fusion ---
            if prediction == "ANOMALY":

                # Case 1: ML detects anomaly but rules don't → weak signal
                if not alerts:
                    severity = "LOW"

                    if features["error_rate"] > 0.6 or features["avg_latency"] > 400:
                        severity = "HIGH"

                    final_alerts.append(
                        {
                            "type": "ML_ONLY_ANOMALY",
                            "severity": severity,
                            "details": features,
                        }
                    )

                # Case 2: ML + Rule both detect → strong signal
                else:
                    for alert in final_alerts:
                        alert["ml_confirmed"] = True

            # --- Print final alerts ---
            if final_alerts:
                print("🚨 FINAL ALERT:", final_alerts)


if __name__ == "__main__":
    main()