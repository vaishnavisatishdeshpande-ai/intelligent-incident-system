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

ML_ONLY_ALERTS = Counter("ml_only_alerts_total", "ML-only alerts triggered")
SUPPRESSED_ML = Counter("ml_suppressed_total", "ML anomalies suppressed")

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
        if not isinstance(event, dict):
            return
        self.events.append(event)

    def compute_features(self):
        if not self.events:
            return None

        try:
            latencies = [e.get("latency", 0) for e in self.events]
            errors = [e.get("error", 0) for e in self.events]

            return {
                "avg_latency": sum(latencies) / len(latencies),
                "error_rate": sum(errors) / len(errors),
            }
        except Exception:
            return None


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

        # LATENCY
        if avg_latency is not None:
            self.latency_breach_count = (
                self.latency_breach_count + 1
                if avg_latency > self.latency_threshold
                else 0
            )

            if self.latency_breach_count >= self.breach_threshold:
                severity = "CRITICAL" if avg_latency > self.latency_threshold * 1.5 else "HIGH"
                current_alerts.add("HIGH_LATENCY")

                if "HIGH_LATENCY" not in self.active_alerts:
                    alerts.append({
                        "type": "HIGH_LATENCY",
                        "severity": severity,
                        "value": avg_latency,
                    })

        # ERROR RATE
        if error_rate is not None:
            self.error_breach_count = (
                self.error_breach_count + 1
                if error_rate > self.error_threshold
                else 0
            )

            if self.error_breach_count >= self.breach_threshold:
                severity = "CRITICAL" if error_rate > self.error_threshold * 2 else "HIGH"
                current_alerts.add("HIGH_ERROR_RATE")

                if "HIGH_ERROR_RATE" not in self.active_alerts:
                    alerts.append({
                        "type": "HIGH_ERROR_RATE",
                        "severity": severity,
                        "value": error_rate,
                    })

        # RECOVERY
        for alert_type in self.active_alerts - current_alerts:
            alerts.append({"type": alert_type, "status": "RESOLVED"})

        self.active_alerts = current_alerts
        return alerts


# ================================
# 🧠 EXPLAINABILITY
# ================================

def generate_reason(features):
    reasons = {}

    latency = features.get("avg_latency", 0)
    error = features.get("error_rate", 0)

    if latency > 350:
        reasons["latency"] = {
            "current": round(latency, 2),
            "threshold": 350,
            "status": "HIGH"
        }

    if error > 0.5:
        reasons["error_rate"] = {
            "current": round(error, 2),
            "threshold": 0.5,
            "status": "HIGH"
        }

    return reasons


# ================================
# 🎯 ACTION
# ================================

def determine_action(severity):
    return {
        "CRITICAL": "ESCALATE_TO_ONCALL",
        "HIGH": "TRIGGER_ALERT",
        "MEDIUM": "LOG_AND_MONITOR"
    }.get(severity, "NO_ACTION")


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
    scorer = IncidentScorer()

    try:
        for message in consumer:
            try:
                event = message.value
                EVENTS_PROCESSED.inc()

                engine.add_event(event)
                features = engine.compute_features()

                if not features:
                    continue

                LATENCY_GAUGE.set(features["avg_latency"])
                ERROR_RATE_GAUGE.set(features["error_rate"])

                # -------------------------------
                # RULES
                # -------------------------------
                alerts = detector.detect(features)

                # -------------------------------
                # ML
                # -------------------------------
                model.add_data(features)
                model.train()

                ml_result = model.predict(features) or {}

                prediction = ml_result.get("prediction", "NOT_READY")
                confidence = float(ml_result.get("confidence", 0.0))

                signals = ml_result.get("signals", {})
                if_signal = signals.get("isolation_forest", {}).get("anomaly", False)
                xgb_signal = signals.get("xgboost", {}).get("anomaly", False)

                final_alerts = [a.copy() for a in alerts]

                # -------------------------------
                # ML FUSION (STRICT)
                # -------------------------------
                if prediction == "ANOMALY":
                    ML_ANOMALIES.inc()

                    if not alerts and confidence > 0.88 and (
                            features["avg_latency"] > 380 or
                            features["error_rate"] > 0.6
                    ):
                        ML_ONLY_ALERTS.inc()

                        final_alerts.append({
                            "type": "ML_ONLY_ANOMALY",
                            "severity": "HIGH",
                            "confidence": confidence,
                        })
                    else:
                        SUPPRESSED_ML.inc()

                else:
                    if if_signal or xgb_signal:
                        SUPPRESSED_ML.inc()

                # -------------------------------
                # SCORING
                # -------------------------------
                score = scorer.compute_score(
                    features,
                    final_alerts,
                    prediction,
                    confidence
                )

                severity = scorer.get_severity(score)

                # prevent ML-only critical escalation
                if not alerts and prediction == "ANOMALY" and severity == "CRITICAL":
                    severity = "HIGH"

                action = determine_action(severity)

                # -------------------------------
                # EXPLAINABILITY (FINAL)
                # -------------------------------
                reason = generate_reason(features)

                if not reason:
                    if prediction == "ANOMALY":
                        reason = {"note": "ML-detected anomaly without strong rule trigger"}
                    else:
                        reason = {"note": "No significant anomalies detected"}

                # -------------------------------
                # INCIDENT
                # -------------------------------
                incident = {
                    "score": score,
                    "severity": severity,
                    "action": action,
                    "features": features,
                    "alerts": final_alerts,
                    "ml_signal": {
                        "prediction": prediction,
                        "confidence": confidence,
                    },
                    "reason": reason
                }

                print("\n🔥 INCIDENT")
                print(json.dumps(incident, indent=2))

                if final_alerts:
                    ALERTS_TRIGGERED.inc()
                    print("🚨 FINAL ALERT:", final_alerts)

            except Exception as e:
                print("⚠️ Processing error:", str(e))

    except KeyboardInterrupt:
        print("\n🛑 Shutting down processor gracefully...")


if __name__ == "__main__":
    main()