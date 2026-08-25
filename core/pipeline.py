import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from config import settings
from core.rules import RuleEngine, RuleCheckResult
from core.feature_store import FeatureStore
from core.circuit_breaker import CircuitBreaker, CircuitState
from ml.predictor import MLPredictor

logger = logging.getLogger(__name__)

class RiskDecisionResponse(BaseModel):
    transaction_id: str
    account_id: str
    decision: str  # "ALLOW", "REVIEW", "DECLINE"
    risk_score: float
    reason_codes: List[str]
    rule_results: Dict[str, Any]
    ml_evaluated: bool
    circuit_state: str
    latencies: Dict[str, float]  # Latency in ms (rule_ms, feature_ms, ml_ms, total_ms)

class RiskPipeline:
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.feature_store = FeatureStore()
        self.circuit_breaker = CircuitBreaker()
        self.ml_predictor = MLPredictor()

    def process_transaction(self, transaction: Dict[str, Any]) -> RiskDecisionResponse:
        start_total = time.perf_counter()
        
        tx_id = str(transaction.get("transaction_id", "tx_unknown"))
        account_id = str(transaction.get("account_id", "acc_unknown"))
        amount = float(transaction.get("amount", 0.0))
        timestamp = float(transaction.get("timestamp", time.time()))
        lat = float(transaction.get("lat", 0.0))
        lon = float(transaction.get("lon", 0.0))
        country = str(transaction.get("country", "US"))
        
        # 1. Feature Store Lookup
        t0 = time.perf_counter()
        user_history = self.feature_store.get_user_features(account_id, timestamp)
        feature_ms = (time.perf_counter() - t0) * 1000.0
        
        # 2. Rule Engine Evaluation
        t1 = time.perf_counter()
        rule_check: RuleCheckResult = self.rule_engine.evaluate(transaction, user_history)
        rule_ms = (time.perf_counter() - t1) * 1000.0
        
        reason_codes = list(rule_check.triggered_rules)
        decision = "ALLOW"
        risk_score = 0.0
        ml_evaluated = False
        ml_ms = 0.0
        
        # If Hard Rule Violation (e.g. max limit exceeded, sanctioned country), immediate DECLINE
        if rule_check.hard_action == "DECLINE":
            decision = "DECLINE"
            risk_score = 1.0
        else:
            # 3. ML Inference with Circuit Breaker Protection
            if self.circuit_breaker.allow_request() and self.ml_predictor.is_loaded:
                t2 = time.perf_counter()
                try:
                    # Construct feature dictionary for ML predictor
                    amount_ratio = amount / (user_history["avg_amount_24h"] + 1.0)
                    is_foreign = 1 if country.upper() != "US" else 0
                    hour_of_day = int((timestamp % 86400) // 3600)
                    mcc = int(transaction.get("mcc", 0))
                    mcc_risk_score = 0.8 if mcc in (6012, 7995, 6211) else 0.1
                    
                    ml_features = {
                        "amount": amount,
                        "tx_count_5m": user_history["tx_count_5m"],
                        "spend_24h": user_history["spend_24h"],
                        "avg_amount_24h": user_history["avg_amount_24h"],
                        "amount_ratio": amount_ratio,
                        "is_foreign": is_foreign,
                        "hour_of_day": hour_of_day,
                        "mcc_risk_score": mcc_risk_score
                    }
                    
                    ml_score, ml_reasons, ml_ms = self.ml_predictor.predict_risk(ml_features)
                    ml_evaluated = True
                    risk_score = ml_score
                    
                    # Latency SLA check for Circuit Breaker
                    if ml_ms > settings.ML_LATENCY_THRESHOLD_MS:
                        self.circuit_breaker.record_failure(f"ML latency {ml_ms:.2f}ms > SLA threshold")
                    else:
                        self.circuit_breaker.record_success()
                        
                    reason_codes.extend(ml_reasons)
                    
                    # Make final decision combining Rule & ML Risk Score
                    if ml_score >= settings.RISK_SCORE_DECLINE_THRESHOLD:
                        decision = "DECLINE"
                    elif ml_score >= settings.RISK_SCORE_REVIEW_THRESHOLD or rule_check.hard_action == "REVIEW":
                        decision = "REVIEW"
                    else:
                        decision = "ALLOW"

                except Exception as e:
                    logger.error(f"ML Inference error: {e}")
                    self.circuit_breaker.record_failure(str(e))
                    ml_evaluated = False
                    # Fallback to rule action
                    decision = rule_check.hard_action or "ALLOW"
                    risk_score = 0.5 if decision == "REVIEW" else 0.1
            else:
                # Circuit Breaker OPEN or ML offline - Fallback to deterministic rules
                decision = rule_check.hard_action or "ALLOW"
                risk_score = 0.8 if decision == "DECLINE" else (0.5 if decision == "REVIEW" else 0.1)
                reason_codes.append("FALLBACK_RULE_DECISION_CIRCUIT_OPEN")

        # 4. Asynchronous update to Feature Store
        self.feature_store.update_user_features(
            account_id=account_id,
            amount=amount,
            lat=lat,
            lon=lon,
            timestamp=timestamp
        )

        total_ms = (time.perf_counter() - start_total) * 1000.0

        return RiskDecisionResponse(
            transaction_id=tx_id,
            account_id=account_id,
            decision=decision,
            risk_score=round(risk_score, 4),
            reason_codes=reason_codes,
            rule_results={
                "passed": rule_check.passed,
                "triggered_rules": rule_check.triggered_rules
            },
            ml_evaluated=ml_evaluated,
            circuit_state=self.circuit_breaker.state.value,
            latencies={
                "rule_ms": round(rule_ms, 3),
                "feature_ms": round(feature_ms, 3),
                "ml_ms": round(ml_ms, 3),
                "total_ms": round(total_ms, 3)
            }
        )
