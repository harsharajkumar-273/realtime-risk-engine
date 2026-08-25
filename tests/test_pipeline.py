import pytest
import time
from core.pipeline import RiskPipeline

def test_risk_pipeline_normal_tx():
    pipeline = RiskPipeline()
    tx = {
        "transaction_id": "tx_test_normal",
        "account_id": "acc_normal_1",
        "amount": 45.50,
        "country": "US",
        "mcc": 5411,
        "lat": 40.7128,
        "lon": -74.0060,
        "timestamp": time.time()
    }
    
    res = pipeline.process_transaction(tx)
    
    assert res.decision in ("ALLOW", "REVIEW")
    assert res.latencies["total_ms"] > 0
    assert "total_ms" in res.latencies
    assert res.circuit_state in ("CLOSED", "HALF_OPEN", "OPEN")

def test_risk_pipeline_decline_tx():
    pipeline = RiskPipeline()
    tx = {
        "transaction_id": "tx_test_decline",
        "account_id": "acc_decline_1",
        "amount": 25000.0,  # Exceeds max amount
        "country": "US",
        "mcc": 5411,
        "lat": 40.7128,
        "lon": -74.0060,
        "timestamp": time.time()
    }
    
    res = pipeline.process_transaction(tx)
    assert res.decision == "DECLINE"
    assert any("HARD_LIMIT_EXCEEDED" in r for r in res.reason_codes)
