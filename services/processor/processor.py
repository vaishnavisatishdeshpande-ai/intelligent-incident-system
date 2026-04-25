from collections import deque
import json

from kafka import KafkaConsumer
from prometheus_client import start_http_server, Counter, Gauge

from services.processor.incident import IncidentScorer
from services.model.model import AnomalyModel
from services.producer.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
)

# ================================
# 📊 METRICS
# ================================

EVENTS_PROCESSED = Counter("events_processed_total", "Total events processed")
ALERTS_TRIGGERED = Counter("alerts_triggered_total", "Total alerts triggered")
ML_ANOMALIES = Counter("ml_anomalies_total", "Total ML anomalies detected")

LATENCY_GAUGE = Gauge("avg_latency", "Average latency")
ERROR_RATE_GAUGE = Gauge("error_rate", "Error rate")

WINDOW_SIZE = 10


# ================================
# ⚙️ FEATURE ENGINE
# ================================

class FeatureEngine:
    def __init__(self):
        self.events = deque(maxlen=WINDOW_SIZE)

    def add_event(self, event):
        self.events.append(event)

    def compute_features(self):
        if not self.events:
            return None

        latencies = [e["latency"] for e in self.events]
        errors = [e["error"] for e in self.events]

        return {
            "avg_latency": sum(latencies) / len(latencies),
            "error_rate": sum(errors) / len(errors),
        }


# ================================
# 🚨 RULE-BASED DETECTOR
# ================================

class AnomalyDetector:
    def __init__(self, latency_threshold=300, error_threshold=0.3):
        self.latency_threshold = latency_threshold
        self.error_threshold = error_threshold

        self.active_alerts = set()

        self.latency_breach_count = 0
        self.error_breach_count = 0
        self.breach_threshold = 3

    def detect(self, features):
        alerts = []
        current_alerts = set()

        avg_latency = features.get("avg_latency")
        error_rate = features.get("error_rate")

        # --- LATENCY ---
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
                    alerts.append({
                        "type": "HIGH_LATENCY",
                        "severity": severity,
                        "value": avg_latency,
                    })

        # --- ERROR RATE ---
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
                    alerts.append({
                        "type": "HIGH_ERROR_RATE",
                        "severity": severity,
                        "value": error_rate,
                    })

        # --- RECOVERY ---
        resolved = self.active_alerts - current_alerts
        for alert_type in resolved:
            alerts.append({"type": alert_type, "status": "RESOLVED"})

        self.active_alerts = current_alerts
        return alerts


# ================================
# 🔌 KAFKA
# ================================

def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )


# ================================
# 🚀 MAIN PIPELINE
# ================================

def main():
    print("🚀 Starting processor...")

    start_http_server(8000)

    consumer = create_consumer()
    engine = FeatureEngine()
    detector = AnomalyDetector()
    model = AnomalyModel()
    scorer = IncidentScorer()  # 🔥 NEW

    for message in consumer:
        event = message.value
        print("Received event:", event)

        EVENTS_PROCESSED.inc()

        engine.add_event(event)
        features = engine.compute_features()

        if not features:
            continue

        LATENCY_GAUGE.set(features["avg_latency"])
        ERROR_RATE_GAUGE.set(features["error_rate"])

        # --- RULE ALERTS ---
        alerts = detector.detect(features)

        # --- ML ---
        model.add_data(features)
        model.train()

        prediction = model.predict(features)

        final_alerts = [a.copy() for a in alerts]

        # --- ML FUSION ---
        if prediction == "ANOMALY":
            ML_ANOMALIES.inc()

            if not alerts:
                final_alerts.append({
                    "type": "ML_ONLY_ANOMALY",
                    "severity": "HIGH",
                    "details": features,
                })
            else:
                for alert in final_alerts:
                    alert["ml_confirmed"] = True

        # --- 🔥 INCIDENT SCORING ---
        score = scorer.compute_score(features, final_alerts, prediction)
        severity = scorer.get_severity(score)

        incident = {
            "score": score,
            "severity": severity,
            "features": features,
            "alerts": final_alerts,
        }

        print("🔥 INCIDENT:", incident)

        # --- FINAL ALERT OUTPUT ---
        if final_alerts:
            ALERTS_TRIGGERED.inc()
            print("🚨 FINAL ALERT:", final_alerts)


if __name__ == "__main__":
    main()