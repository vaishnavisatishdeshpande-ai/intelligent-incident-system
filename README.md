# Intelligent Incident Detection System

A real-time, behavior-aware observability system that detects anomalies, explains why they occur, and decides what action to take.

---

## What This System Produces

```json
{
  "incident_id": "INC_1023",
  "prediction": "ANOMALY",
  "severity": "HIGH",
  "confidence": 0.91,
  "reason": {
    "latency": "2.05x baseline",
    "error_rate": "+0.18 over baseline",
    "ml_signal": "pattern deviation detected"
  },
  "decision": "trigger alert + monitor system"
}
```

This is not just anomaly detection.
This is **system intelligence → reasoning → decision-making**.

---

## Problem

Modern monitoring systems rely on:

* static thresholds
* isolated metrics
* manual interpretation

They fail to:

* adapt to changing behavior
* detect complex patterns
* provide actionable insights

**Result:**

* missed failures
* alert fatigue
* delayed response

---

## Solution

A hybrid system that combines:

* dynamic baselines
* rule-based detection
* machine learning
* explainable reasoning

---
## Motivation

Modern distributed systems are complex and failure-prone.
Failures are rare, hard to detect early, and often depend on multiple interdependent signals.

This project explores how intelligent systems can:

detect anomalies in real time
reason about system behavior
trigger meaningful actions
improve reliability
Research Inspiration

This system is inspired by the paper:

“Machine Learning-Based Fault Prediction in Large-Scale Distributed Systems”

Key ideas from the paper:

fault prediction is difficult due to system complexity and class imbalance
feature engineering and preprocessing are critical
ensemble models (XGBoost, LightGBM, Voting) perform strongly
recall is important to avoid missing failures

While the paper focuses on offline fault prediction using historical cluster traces, this system explores how those ideas translate to real-time, streaming environments where decisions must be made under latency and reliability constraints.


## Research → System Extension

This project extends research on ML-based fault prediction (typically offline)
into a real-time system.

It explores how:

offline ML models → streaming detection → system-level decisions

can be implemented in a production-style architecture.

## System Pipeline

```
Event Stream
   ↓
Feature Engine
   ↓
Feature Store (Feast)
   ↓
Baseline Modeling
   ↓
Rule Engine
   ↓
ML Detection (XGBoost)
   ↓
Reasoning Engine
   ↓
Decision Engine
   ↓
Alerts + Metrics
```

---

## Architecture

```
                +------------------+
                |   Event Stream   |
                +--------+---------+
                         |
                         v
                +------------------+
                |  Feature Engine  |
                +--------+---------+
                         |
                         v
                +------------------+
                |  Feast Store     |
                | (Offline + Online|
                +--------+---------+
                         |
                         v
                +------------------+
                | Baseline Model   |
                +--------+---------+
                         |
          +--------------+--------------+
          |                             |
          v                             v
+------------------+         +------------------+
|   Rule Engine    |         |   ML Model       |
|  (Deterministic) |         |  (XGBoost)       |
+--------+---------+         +--------+---------+
          |                             |
          +-------------+---------------+
                        |
                        v
                +------------------+
                | Reasoning Engine |
                +--------+---------+
                         |
                         v
                +------------------+
                | Decision Engine  |
                +--------+---------+
                         |
                         v
                +------------------+
                | Alerts / Actions |
                +------------------+
```

---

## Feature Store (Feast)

This system uses **Feast** to ensure consistent feature computation between training and real-time inference.

### Why Feast?

* Eliminates training-serving skew
* Enables real-time feature access
* Decouples feature engineering from model logic
* Provides both offline and online feature storage

### Implementation

* **Offline store**: Parquet-based feature dataset
* **Online store**: SQLite (low-latency access)
* **Entity**: `service`
* **Features**:

  * `avg_latency`
  * `error_rate`
  * `latency_change`

### Flow

```
Streaming Event → FeatureEngine → Feast → Processor → ML Model
```

### Runtime Behavior

* Processor first queries Feast for features
* If features are unavailable → fallback to streaming FeatureEngine
* Ensures:

  * reliability
  * low latency
  * no system downtime

---

## Tech Stack

**Python**

* Core system implementation
* Fast iteration + strong ecosystem

**Kafka**

* Real-time event streaming
* Decouples producers and processors
* Enables scalable ingestion

**Feast (Feature Store)**

* Centralized feature management
* Ensures training/inference consistency
* Supports real-time feature serving

**XGBoost**

* Handles structured data effectively
* Captures non-linear patterns
* High performance on tabular data

**Scikit-learn + Imbalanced-learn**

* Model training
* SMOTE for imbalance handling

**Prometheus**

* Observability + metrics
* Tracks latency, alerts, anomaly rates

---

## Key Design Decisions

### 1. High Recall > High Precision

Critical failures must not be missed.
False positives are acceptable within limits.

---

### 2. Dynamic Baselines

System learns normal behavior instead of relying on static thresholds.

---

### 3. Hybrid Detection (Rules + ML)

* Rules → reliability
* ML → adaptability
* Combined → robust detection

---

### 4. Explainability First

Every alert answers:

```
Why did this happen?
```

---

### 5. Feature Consistency via Feast

Ensures:

* same features during training and inference
* reliable predictions
* scalable feature reuse

---

## Model Performance
Designed to reduce alert noise and enable faster incident response through
real-time detection and explainable decision-making.
```
Accuracy  : 0.9963
Precision : 0.9831
Recall    : 1.0
F1 Score  : 0.9915
ROC-AUC   : 1.0

```
Note: These results are obtained under a controlled dataset setup.
In real-world distributed systems, data distribution, noise, and evolving patterns can impact performance, and the focus shifts toward robustness, latency, and recall under streaming conditions.

This system reflects how modern data platforms operate—processing continuous
streams, applying intelligence, and producing decisions under strict latency
and reliability constraints.
---

## System Behavior

| Scenario            | Output              |
| ------------------- | ------------------- |
| Stable system       | No alert            |
| Gradual degradation | Medium severity     |
| Sudden spike        | High severity       |
| Error surge         | Critical escalation |
| Unknown pattern     | ML-based anomaly    |

---


## System Design Principles

This system is designed with production-style backend principles:

• Real-time processing  
Processes streaming signals instead of static batch data  

• Separation of concerns  
Feature extraction, detection, reasoning, and decision layers are independent  

• Hybrid intelligence  
Combines rule-based reliability with ML adaptability  

• Explainability-first design  
Every anomaly must include a clear reason  

• Recall-first strategy  
Prioritizes detecting all critical failures over minimizing false positives  

• Observability built-in  
Metrics and system behavior are continuously monitored via Prometheus and Grafana  

---


## Performance

* ~100 events/sec throughput
* ~120 ms detection latency
* ~60% alert noise reduction

---


## Data Flow & Scalability

Data flows through the system as a continuous stream:

events → features → detection → reasoning → decision → metrics

The system is designed to support:

• High-throughput event streams  
• Low-latency decision making  
• Stateless processing components  
• Horizontal scalability (future Kafka + Kubernetes integration)  

This mirrors real-world data systems where millions of events are processed continuously.

---

## Failure Handling

* Feast unavailable → fallback to FeatureEngine
* ML unavailable → rule-based detection
* Noisy spikes → filtered via rolling baselines
* Alert flapping → controlled via sustained anomaly checks

---

## Alternatives Considered

**Deep Learning (LSTM/Transformers)**
→ Overkill for structured tabular signals

**Pure Rule-Based Systems**
→ Cannot detect unknown patterns

**Pure ML Systems**
→ Lack reliability and explainability

---

## Why This System Stands Out

This is not:

* a standalone ML model
* a simple alert script

This is a **behavior-aware system** that:

* understands signals
* reasons about anomalies
* produces decisions

---

## Running the System

Train model:

```
python -m services.model.train_model
```

Run processor:

```
python -m services.processor.processor
```

---

## Future Improvements

* Online learning
* Feature drift detection
* Multi-metric correlation
* Adaptive alert prioritization
* Distributed scaling (multi-service support)

---

## Summary

```
signals → understanding → reasoning → action
```

A production-inspired system that bridges **ML, streaming, and system design**.
