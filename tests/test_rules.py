import pytest
import time
from core.rules import RuleEngine, haversine_distance_km

def test_haversine_distance():
    # NYC to SF ~ 4130 km
    dist = haversine_distance_km(40.7128, -74.0060, 37.7749, -122.4194)
    assert 4100 <= dist <= 4200

def test_rule_hard_amount_limit():
    engine = RuleEngine()
    tx = {"amount": 15000.0, "country": "US", "mcc": 5411}
    user_history = {}
    res = engine.evaluate(tx, user_history)
    
    assert res.passed is False
    assert res.hard_action == "DECLINE"
    assert any("HARD_LIMIT_EXCEEDED" in r for r in res.triggered_rules)

def test_rule_sanctioned_country():
    engine = RuleEngine()
    tx = {"amount": 50.0, "country": "XX", "mcc": 5411}
    res = engine.evaluate(tx, {})
    
    assert res.passed is False
    assert res.hard_action == "DECLINE"
    assert any("SANCTIONED_COUNTRY" in r for r in res.triggered_rules)

def test_rule_velocity_exceeded():
    engine = RuleEngine()
    tx = {"amount": 100.0, "country": "US", "mcc": 5411}
    user_history = {"tx_count_5m": 6}
    res = engine.evaluate(tx, user_history)
    
    assert res.passed is False
    assert res.hard_action == "REVIEW"
    assert any("HIGH_VELOCITY" in r for r in res.triggered_rules)

def test_rule_impossible_travel():
    engine = RuleEngine()
    now = time.time()
    tx = {
        "amount": 200.0,
        "country": "US",
        "lat": 37.7749,  # SF
        "lon": -122.4194,
        "timestamp": now
    }
    user_history = {
        "last_lat": 40.7128,  # NYC
        "last_lon": -74.0060,
        "last_timestamp": now - 10.0  # 10 seconds ago (NYC to SF in 10s = ~1.4 million km/h)
    }
    res = engine.evaluate(tx, user_history)
    
    assert res.passed is False
    assert res.hard_action == "DECLINE"
    assert any("IMPOSSIBLE_TRAVEL" in r for r in res.triggered_rules)
