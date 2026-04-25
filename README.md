# Intelligent Incident Detection System

A real-time anomaly detection system designed to reduce alert noise, explain decisions, and behave reliably under production-like conditions.

---

## Problem

Modern systems generate continuous streams of metrics (latency, error rate, etc.).
Typical alerting systems fail because they:

* trigger too often (high false positives)
* lack clear reasoning
* cannot handle noisy, real-world signals

The goal is not just to detect anomalies, but to decide **when to act** and **why it matters**.

---

## Approach

This system combines:

* rule-based detection (deterministic signals)
* machine learning (pattern detection)
* strict decision control (noise reduction)
* explainability (human-readable reasoning)

---

## Architecture

Event Stream → Feature Engine → Rule Engine + ML → Fusion → Scoring → Action

### Components

* **Producer**: generates or ingests metrics (latency, error rate)
* **Kafka**: streaming pipeline for decoupled processing
* **Feature Engine**: computes rolling averages
* **Rule Engine**: detects threshold-based issues
* **ML Layer**:

  * Isolation Forest → unknown anomalies
  * XGBoost → learned failure patterns
* **Fusion Layer**: combines signals with strict gating
* **Scoring**: assigns severity (LOW → CRITICAL)
* **Explainability**: explains why alerts occur
* **Observability**: Prometheus + Grafana

---

## Dataset

Uses real-world time-series data:

* NAB (Numenta Anomaly Benchmark)
* AWS CloudWatch CPU metrics

Why:

* realistic noise patterns
* suitable for anomaly detection
* closer to production behavior than synthetic data

---

## Design Principles

### 1. Signal over Noise

Only meaningful anomalies should trigger alerts.

### 2. ML is Assistive

ML supports decisions, it does not override system logic.

### 3. Controlled Alerting

High severity requires strong evidence.

### 4. Explainability

Every alert includes a reason.

### 5. Failure Awareness

System handles:

* missing data
* ML not ready
* noisy inputs

---

## System Behavior

* Normal traffic → no alerts
* Sustained latency → HIGH
* Error spikes → HIGH / CRITICAL
* ML-only anomalies → rare and gated
* Weak signals → suppressed

---

## Trade-offs

* **Streaming vs Batch**
  Chosen: streaming (real-time)
  Trade-off: higher complexity

* **Rules vs ML**
  Chosen: hybrid
  Trade-off: more coordination

* **Sliding Window vs Full History**
  Chosen: sliding window
  Trade-off: less long-term memory

* **Strict Gating vs Recall**
  Chosen: strict gating
  Trade-off: may miss weak anomalies

---

## Metrics

* events_processed_total
* alerts_triggered_total
* ml_anomalies_total
* ml_only_alerts_total
* ml_suppressed_total
* avg_latency
* error_rate

---

## Results

* reduced alert noise
* controlled ML behavior
* improved interpretability
* realistic severity progression

---

## Research Basis

Inspired by concepts from:

* IEEE research on anomaly detection and system reliability
* streaming anomaly detection techniques
* hybrid ML + rule-based systems
* signal vs noise trade-offs

---

## Future Work

* real production data ingestion
* adaptive thresholds
* online learning
* distributed deployment
* cross-service correlation

---

## Key Insight

Detecting anomalies is easy.
Building a system that engineers trust is hard.

---

## Summary

This project demonstrates:

* system design thinking
* ML + backend integration
* real-time processing
* explainable decision-making

It is designed to behave like a production system, not a demo.
