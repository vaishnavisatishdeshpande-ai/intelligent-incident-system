# Intelligent Incident Detection System

A real-time system that detects anomalies, explains why they occur, and decides what action to take.

---

## Example Output

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

This is not just detection.
This is **explainable, decision-driven system behavior**.

---

## Problem

Traditional monitoring systems rely on:

* static thresholds
* isolated metrics
* manual interpretation

They fail to:

* capture evolving system behavior
* detect complex failure patterns
* provide actionable insights

Result:

* missed failures
* alert noise
* delayed response

---

## Approach

This system combines:

* dynamic baselines
* rule-based detection
* machine learning
* reasoning

Pipeline:

```
stream → features → baseline → rules → ML → reasoning → decision
```

Each stage transforms raw signals into structured decisions.

---

## Core Components

**Feature Engine**

* avg_latency
* latency_change
* error_rate
* rolling baseline

**Baseline Modeling**

* slow adaptation
* prevents drift masking

**Rule Engine**

* threshold breaches
* sustained anomalies
* noise control

**ML Layer (XGBoost)**

* learns non-linear patterns
* detects unknown anomalies

**Reasoning Engine**

* aligns signals with causes
* filters weak signals
* produces explanations

**Decision Engine**

| Severity | Action             |
| -------- | ------------------ |
| LOW      | NO_ACTION          |
| MEDIUM   | LOG_AND_MONITOR    |
| HIGH     | TRIGGER_ALERT      |
| CRITICAL | ESCALATE_TO_ONCALL |

---

## Key Design Choice

```
High Recall > High Precision
```

Critical failures must not be missed.
False positives are acceptable within limits.

---

## Model Performance

```
Accuracy  : 0.9888
Precision : 0.9611
Recall    : 0.9886
F1 Score  : 0.9746
ROC-AUC   : 0.9999
```

Evaluation is based on behavior-derived labels, not manually annotated incidents.

---

## System Behavior

| Scenario            | Output              |
| ------------------- | ------------------- |
| Stable system       | No alerts           |
| Gradual degradation | Medium severity     |
| Sudden spike        | High severity       |
| Error surge         | Critical escalation |
| Unknown pattern     | ML-based anomaly    |

---

## Why This Is Different

This is not:

* just a model
* just a monitoring script

This system:

* models behavior
* reasons about anomalies
* produces decisions

---

## Run

Train model:

```
python -m services.model.train_model
```

Run processor:

```
python -m services.processor.processor
```

---

## Summary

A system that:

* understands signals
* detects anomalies
* explains decisions
* takes action

Designed to reflect real-world observability systems, not isolated ML pipelines.
