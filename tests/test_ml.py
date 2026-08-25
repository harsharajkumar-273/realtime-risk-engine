import pytest
from ml.predictor import MLPredictor

def test_ml_predictor_inference():
    predictor = MLPredictor()
    assert predictor.is_loaded is True
    
    sample_features = {
        "amount": 150.0,
        "tx_count_5m": 1,
        "spend_24h": 450.0,
        "avg_amount_24h": 150.0,
        "amount_ratio": 1.0,
        "is_foreign": 0,
        "hour_of_day": 14,
        "mcc_risk_score": 0.1
    }
    
    score, reasons, latency_ms = predictor.predict_risk(sample_features)
    
    assert 0.0 <= score <= 1.0
    assert isinstance(reasons, list)
    assert latency_ms < 50.0  # Low latency SLA
