# Intelligent Incident Detection System

A real-time observability and anomaly detection system that combines streaming data processing, rule-based detection, and machine learning with explainable reasoning.

---

## Overview

Modern production systems generate high-volume telemetry data, but detecting meaningful incidents remains challenging due to noise, drift, and evolving system behavior.

This project implements a **hybrid observability system** that:

* Processes live system signals
* Learns normal behavior dynamically
* Detects anomalies using both rules and machine learning
* Explains *why* a decision was made
* Outputs actionable decisions, not just predictions

---

## System Design

The system follows a structured pipeline:

```
stream → feature engineering → baseline modeling → rule detection → ML prediction → reasoning → decision
```

### Core Components

**1. Streaming Processor**

* Consumes events continuously
* Maintains sliding window for feature computation

**2. Feature Engine**

* Computes:

  * avg_latency
  * error_rate
  * latency_change
  * rolling_mean / rolling_std
* Maintains adaptive baseline using exponential smoothing

**3. Rule-Based Detection**

* Detects threshold breaches
* Tracks sustained anomalies
* Prevents alert flapping

**4. Machine Learning Layer**

* XGBoost classifier trained on engineered signals
* Learns complex failure patterns beyond rules
* Handles non-linear relationships

**5. Reasoning Engine**

* Aligns every alert with a clear explanation
* Filters weak signals
* Outputs only meaningful deviations

**6. Decision Engine**

* Converts signals into actions:

| Severity | Action             |
| -------- | ------------------ |
| LOW      | NO_ACTION          |
| MEDIUM   | LOG_AND_MONITOR    |
| HIGH     | TRIGGER_ALERT      |
| CRITICAL | ESCALATE_TO_ONCALL |

---

## Key Idea

The system is not purely rule-based and not purely ML-driven.

It is a **hybrid system** designed for reliability:

* Rules ensure safety and deterministic detection
* ML captures complex and unknown patterns
* Reasoning ensures transparency and trust

---

## Dataset

The system uses real-world time-series data derived from cloud infrastructure metrics.

Dataset characteristics:

* Time-series CPU utilization data
* Converted into latency-style signals
* Features engineered from real behavior:

  * trend (latency_change)
  * variability (error_rate)
  * baseline deviation

Failure labels are **behavior-driven**, not manually annotated, simulating real observability environments.

---

## Model Evaluation

The model is evaluated using standard classification metrics:

* Accuracy
* Precision
* Recall
* F1 Score
* ROC-AUC

### Results

```
Accuracy  : 0.9888
Precision : 0.9611
Recall    : 0.9886
F1 Score  : 0.9746
ROC-AUC   : 0.9999
```

### Important Note

Evaluation is performed on **proxy labels derived from system behavior**, not manually labeled failures.

The focus is not absolute accuracy, but **learning meaningful patterns from signals**.

---

## Design Trade-Off

The system prioritizes:

```
High Recall > High Precision
```

This ensures:

* Critical failures are not missed
* Some false positives are acceptable in exchange for safety

This trade-off reflects real-world production systems.

---

## System Behavior

| Scenario            | Input Pattern             | Output Behavior |
| ------------------- | ------------------------- | --------------- |
| Stable system       | Low variance              | No alerts       |
| Gradual degradation | Slowly increasing latency | Medium severity |
| Sudden spike        | Sharp latency increase    | High severity   |
| Error surge         | High error_rate           | High / Critical |
| ML anomaly          | Pattern unseen in rules   | ML-based alert  |

---

## Why This System Stands Out

Most projects:

* Train a model
* Output predictions

This system:

* Models system behavior
* Detects anomalies in context
* Explains decisions
* Produces actions

It demonstrates:

* System design thinking
* Signal vs noise handling
* Failure detection strategy
* Explainability in ML systems

---

## Future Improvements

* Integration with feature store for consistent training/inference
* Online learning for continuous adaptation
* Multi-metric correlation (CPU, memory, network)
* Real incident datasets for stronger evaluation
* Alert prioritization using impact scoring

---

## Conclusion

This project demonstrates how to build an **intelligent observability system**, not just a machine learning model.

It combines:

* streaming systems
* feature engineering
* anomaly detection
* explainable reasoning
* decision-making

The result is a system that behaves closer to real production monitoring platforms.

---

## Running the System

Train the model:

```
python -m services.model.train_model
```

Run the processor:

```
python -m services.processor.processor
```

---

This project focuses on clarity of thinking, system behavior, and meaningful signal extraction — the core of real-world backend intelligence systems.
