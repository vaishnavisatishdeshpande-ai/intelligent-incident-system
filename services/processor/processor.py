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

EVENTS_PROCESSED = Counter("events_processed_total", "Total events processed")
ALERTS_TRIGGERED = Counter("alerts_triggered_total", "Total alerts triggered")
ML_ANOMALIES = Counter("ml_anomalies_total", "Total ML anomalies detected")

ML_ONLY_ALERTS = Counter("ml_only_alerts_total", "ML-only alerts triggered")
SUPPRESSED_ML = Counter("ml_suppressed_total", "ML anomalies suppressed")

LATENCY_GAUGE = Gauge("avg_latency", "Average latency")
ERROR_RATE_GAUGE = Gauge("error_rate", "Error rate")

WINDOW_SIZE = 10


class FeatureEngine:
    def __init__(self):
        self.events = deque(maxlen=WINDOW_SIZE)
        self.baseline_latency = None
        self.baseline_error = None
        self.prev_avg_latency = None

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

        # ✅ ADD THIS (CRITICAL)
        if self.prev_avg_latency is None:
            latency_change = 0.0
        else:
            latency_change = avg_latency - self.prev_avg_latency

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
            "latency_change": latency_change,  # 🔥 THIS FIXES EVERYTHING
            "baseline_latency": self.baseline_latency,
            "baseline_error": self.baseline_error,
        }

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

        for alert_type in self.active_alerts - current_alerts:
            alerts.append({"type": alert_type, "status": "RESOLVED"})

        self.active_alerts = current_alerts
        return alerts


class ReasonGenerator:
    def generate_reason(self, features, alerts=None, ml_signal=None):
        reasons = {}

        latency = features["avg_latency"]
        error = features["error_rate"]

        base_latency = features.get("baseline_latency", latency)
        base_error = features.get("baseline_error", error)

        alerts = alerts or []

        latency_alert_present = any(a.get("type") == "HIGH_LATENCY" for a in alerts)

        if latency_alert_present:
            ratio = latency / max(base_latency, 1)

            if latency > base_latency * 1.15:
                reasons["latency"] = {
                    "current": round(latency, 2),
                    "baseline": round(base_latency, 2),
                    "deviation": f"{round(ratio, 2)}x"
                }
            else:
                reasons["latency"] = {
                    "current": round(latency, 2),
                    "baseline": round(base_latency, 2),
                    "status": "threshold_breach"
                }

        elif latency > 350 and latency > base_latency * 1.3:
            ratio = latency / max(base_latency, 1)
            reasons["latency"] = {
                "current": round(latency, 2),
                "baseline": round(base_latency, 2),
                "deviation": f"{round(ratio, 2)}x"
            }

        error_alert_present = any(a.get("type") == "HIGH_ERROR_RATE" for a in alerts)

        if error_alert_present:
            reasons["error_rate"] = {
                "current": round(error, 2),
                "baseline": round(base_error, 2),
                "delta": max(0, round(error - base_error, 2))
            }

        elif error > base_error + 0.05:
            reasons["error_rate"] = {
                "current": round(error, 2),
                "baseline": round(base_error, 2),
                "delta": max(0, round(error - base_error, 2))
            }

        if ml_signal and ml_signal.get("prediction") == "ANOMALY":
            reasons["ml_signal"] = f"model detected anomaly (confidence={ml_signal.get('confidence')})"

        if not reasons:
            reasons["note"] = "No significant anomalies detected"

        return reasons


def determine_action(severity):
    return {
        "CRITICAL": "ESCALATE_TO_ONCALL",
        "HIGH": "TRIGGER_ALERT",
        "MEDIUM": "LOG_AND_MONITOR"
    }.get(severity, "NO_ACTION")


def determine_decision(severity):
    if severity == "CRITICAL":
        return "escalate + immediate action"
    elif severity == "HIGH":
        return "trigger alert + monitor system"
    elif severity == "MEDIUM":
        return "log and observe trend"
    return "no action"


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )


def main():
    print("Starting processor...")
    start_http_server(8000)

    consumer = create_consumer()
    engine = FeatureEngine()
    detector = AnomalyDetector()
    model = AnomalyModel()
    scorer = IncidentScorer()
    reason_generator = ReasonGenerator()

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

                # -----------------------------
                # Rule-based alerts
                # -----------------------------
                alerts = detector.detect(features)
                alerts = [a for a in alerts if a.get("status") != "RESOLVED"]

                # -----------------------------
                # ML pipeline
                # -----------------------------
                model.add_data(features)

                if not model.if_trained and len(model.data) > 30:
                    model.train()

                ml_result = model.predict(features) or {}

                prediction = ml_result.get("prediction", "NOT_READY")
                confidence = float(ml_result.get("confidence", 0.0))

                signals = ml_result.get("signals", {})
                if_signal = signals.get("isolation_forest", {}).get("anomaly", False)
                xgb_signal = signals.get("xgboost", {}).get("anomaly", False)

                # -----------------------------
                # Merge alerts
                # -----------------------------
                final_alerts = [a.copy() for a in alerts]

                if prediction == "ANOMALY":
                    ML_ANOMALIES.inc()

                    if (
                            confidence >= 0.9  # 🔥 FIXED
                            or features["error_rate"] > 0.6
                            or features["avg_latency"] > 400
                    ):
                        ml_severity = "HIGH"
                    else:
                        ml_severity = "MEDIUM"

                    alert_type = "ML_ONLY_ANOMALY" if not alerts else "ML_ANOMALY"

                    existing_ml = any(a["type"].startswith("ML") for a in final_alerts)

                    if not existing_ml:
                        if alert_type == "ML_ONLY_ANOMALY" and ml_severity == "HIGH":
                            ML_ONLY_ALERTS.inc()

                        final_alerts.append({
                            "type": alert_type,
                            "severity": ml_severity,
                            "confidence": confidence,
                        })
                    else:
                        SUPPRESSED_ML.inc()
                # -----------------------------
                # Scoring + severity
                # -----------------------------
                score = scorer.compute_score(
                    features,
                    final_alerts,
                    prediction,
                    confidence
                )

                severity = scorer.get_severity(score)

                # prevent ML-only CRITICAL (too aggressive)
                if not alerts and prediction == "ANOMALY" and severity == "CRITICAL":
                    severity = "HIGH"

                action = determine_action(severity)
                decision = determine_decision(severity)

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
                    "action": action,
                    "decision": decision,
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