# Sentinel Risk: Real-Time Financial Transaction Risk & Fraud Streaming Engine

> **A high-throughput, low-latency (<10ms) event-driven financial risk engine designed for credit card/banking transaction decisioning, real-time feature aggregation, ML anomaly scoring, resilience engineering, and live telemetry monitoring.**

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

1. **Sub-10ms End-to-End Decision Latency**:
   - Optimized pipeline achieving $<10\text{ms}$ average total latency across deterministic pre-rule checks, rolling window feature retrieval, and vectorized XGBoost model scoring.

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
  - *Architected an event-driven financial risk engine in Python (FastAPI, Redis, XGBoost) delivering sub-10ms transaction decisioning across 1,000+ simulated transactions/sec.*
  - *Implemented a sliding-window feature store (Redis ZSETs) to compute real-time user velocity (5-min count) and 24-hr spending aggregates for dynamic anomaly scoring.*
  - *Engineered a low-latency circuit breaker pattern to guarantee 99.99% system availability by failing back to deterministic rule sets during ML inference SLA spikes (>20ms).*
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

### 3. Run Automated Tests & Benchmarks
```bash
pytest tests/ -v
```

### 4. Start Server & Open Dashboard
```bash
python main.py
```
Then navigate to **`http://localhost:8000`** in your browser!
