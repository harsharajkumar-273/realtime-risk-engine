# Sentinel Risk: Real-Time Financial Transaction Risk & Fraud Streaming Engine

> **An event-driven financial risk engine prototype for transaction decisioning, real-time feature aggregation, ML anomaly scoring, and live telemetry monitoring — built and measured on synthetic data only.**

> **Accuracy note (Nov 2026):** Sentinel is a prototype. It has never processed real transactions or run in production, and no availability figure is claimed. Latency statements below refer only to the local `benchmark.py` run described in the Quick Start.

---

## 🏛 System Architecture

```
                          +-----------------------------------+
                          | Transaction Stream Generator     |
                          | (Simulates High TPS Stream)       |
                          +-----------------+-----------------+
                                            |
                                            v
+-------------------------------------------+-------------------------------------------+
|                          Real-Time Risk Engine (FastAPI)                               |
|                                                                                       |
|  +------------------------+    +-----------------------------+    +----------------+  |
|  |  1. Rule Engine        |    |  2. Real-Time Feature Store |    | 3. ML Model    |  |
|  |  (Velocity, Limits,    +--->|  (Redis Rolling Aggregates: |--->|    Inference   |  |
|  |   Blacklists)          |    |   1h spend, 5m count, etc.) |    | (XGBoost/Light)|  |
|  +-----------+------------+    +--------------+--------------+    +-------+--------+  |
|              |                                |                           |           |
|              +--------------------------------+---------------------------+           |
|                                               |                                       |
|                                               v                                       |
|                               +-------------------------------+                       |
|                               | Decision & Fallback Circuit   |                       |
|                               | (Score, Latency, Reason Codes)|                       |
|                               +---------------+---------------+                       |
+-----------------------------------------------+---------------------------------------+
                                                |
                                                v
                        +-----------------------+-----------------------+
                        | WebSocket & Live Alert Monitoring Service     |
                        +-----------------------+-----------------------+
                                                |
                                                v
                        +-----------------------+-----------------------+
                        | Real-Time Dashboard (Interactive Web UI)      |
                        +-----------------------+-----------------------+
```

---

## 🌟 Key Engineering & Quant Risk Highlights

1. **Low-Latency Decision Pipeline (local benchmark)**:
   - The pipeline is designed for low-latency decisions across deterministic pre-rule checks, rolling window feature retrieval, and XGBoost model scoring. [`benchmark.py`](benchmark.py) runs 1,000 synthetic transactions through the pipeline locally and reports p50/p95/p99 — run it to see current numbers on your machine.

2. **Real-Time Sliding-Window Feature Store**:
   - In-memory Redis ZSET rolling window feature store calculating real-time aggregate signals ($5\text{-min transaction velocity}$, $24\text{-hr cumulative spend}$, historical mean spend ratio) with automatic in-memory fallback.

3. **Resilience & Circuit Breaker Pattern**:
   - Built-in `CircuitBreaker` state machine (`CLOSED`, `OPEN`, `HALF_OPEN`). Automatically trips to `OPEN` if ML inference latency exceeds SLA ($>20\text{ms}$) or encounters errors, seamlessly failing back to rule-based evaluation without dropping transaction stream processing.

4. **Impossible Travel Speed & Geo-Sanction Rules Engine**:
   - Haversine Great Circle distance calculation between consecutive transactions detecting impossible travel speeds ($>800\text{ km/h}$ within short time windows) and hard sanctioned country blacklists.

5. **MLOps & Real-Time Decision Reason Attribution**:
   - XGBoost classifier trained on synthetic financial distributions. Generates real-time decision reason codes (`HIGH_VELOCITY`, `IMPOSSIBLE_TRAVEL`, `ML_FLAG_AMOUNT_RATIO`, `SANCTIONED_COUNTRY`).

6. **Interactive Dark-Mode Telemetry Dashboard**:
   - Real-time WebSockets telemetry feed displaying live throughput (TPS), latency percentiles ($p_{50}, p_{95}, p_{99}$), decision distributions (`ALLOW`, `REVIEW`, `DECLINE`), and instant anomaly injection triggers (`High Amount`, `Velocity Burst`, `Impossible Travel`, `Sanctioned Geo`).

---

## 💼 Resume Bullet Points

- **Real-Time Transaction Risk Engine (SDE + ML)**:
  - *Architected an event-driven financial risk engine in Python (FastAPI, Redis, XGBoost) and measured it with an included benchmark over 1,000 simulated transactions.*
  - *Implemented a sliding-window feature store (Redis ZSETs) to compute real-time user velocity (5-min count) and 24-hr spending aggregates for dynamic anomaly scoring.*
  - *Engineered a circuit breaker pattern that keeps decisions flowing by failing back to deterministic rule sets during ML inference spikes (>20ms).*
  - *Designed an interactive WebSockets telemetry dashboard monitoring live TPS, p95/p99 latency distributions, and decision reason codes.*

---

## 🚀 Quick Start Guide

### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Train ML Risk Model
```bash
python ml/train_model.py
```

### 3. Run Automated Tests
```bash
pytest tests/ -v
```

### 4. Run the Latency/Throughput Benchmark
```bash
python benchmark.py
```
Runs 1,000 simulated transactions end-to-end through the pipeline and prints throughput (TPS) and p50/p95/p99 latency for the synthetic workload on your machine. No fixed latency or throughput figure is claimed for other environments.

### 5. Start Server & Open Dashboard
```bash
python main.py
```
Then navigate to **`http://localhost:8000`** in your browser!
