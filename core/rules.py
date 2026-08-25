import math
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from config import settings

class RuleCheckResult(BaseModel):
    passed: bool = True
    triggered_rules: List[str] = Field(default_factory=list)
    hard_action: Optional[str] = None  # 'DECLINE', 'REVIEW', or None
    rule_latency_ms: float = 0.0

HIGH_RISK_COUNTRIES = {"XX", "YY", "ZZ", "PRK", "IRN"}
HIGH_RISK_MCC = {6012, 7995, 6211}  # Financial institutions, gambling, securities

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Great Circle distance in km between two lat/lon points."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class RuleEngine:
    def evaluate(self, transaction: Dict[str, Any], user_history: Dict[str, Any]) -> RuleCheckResult:
        triggered_rules = []
        hard_action = None
        
        amount = float(transaction.get("amount", 0.0))
        country = str(transaction.get("country", "US")).upper()
        mcc = int(transaction.get("mcc", 0))
        
        # Rule 1: Exceeds Maximum Single Transaction Limit
        if amount > settings.MAX_SINGLE_TRANSACTION_AMOUNT:
            triggered_rules.append(f"HARD_LIMIT_EXCEEDED: amount ${amount:,.2f} > ${settings.MAX_SINGLE_TRANSACTION_AMOUNT:,.2f}")
            hard_action = "DECLINE"
            
        # Rule 2: Blacklisted Country
        if country in HIGH_RISK_COUNTRIES:
            triggered_rules.append(f"SANCTIONED_COUNTRY: {country}")
            hard_action = "DECLINE"
            
        # Rule 3: Velocity Limit (Txs in last 5 minutes)
        tx_count_5m = int(user_history.get("tx_count_5m", 0))
        if tx_count_5m >= settings.MAX_VELOCITY_5M:
            triggered_rules.append(f"HIGH_VELOCITY: {tx_count_5m} transactions in 5 minutes")
            if not hard_action:
                hard_action = "REVIEW"

        # Rule 4: Impossible Travel Speed Check
        last_lat = user_history.get("last_lat")
        last_lon = user_history.get("last_lon")
        last_timestamp = user_history.get("last_timestamp")
        
        curr_lat = transaction.get("lat")
        curr_lon = transaction.get("lon")
        curr_timestamp = transaction.get("timestamp")
        
        if None not in (last_lat, last_lon, last_timestamp, curr_lat, curr_lon, curr_timestamp):
            time_diff_sec = float(curr_timestamp) - float(last_timestamp)
            if 0 < time_diff_sec < 3600:  # Within 1 hour
                dist_km = haversine_distance_km(float(last_lat), float(last_lon), float(curr_lat), float(curr_lon))
                speed_kmh = (dist_km / time_diff_sec) * 3600.0
                if speed_kmh > settings.IMPOSSIBLE_SPEED_KMH:
                    triggered_rules.append(f"IMPOSSIBLE_TRAVEL: {speed_kmh:.0f} km/h travel speed detected")
                    hard_action = "DECLINE"

        passed = len(triggered_rules) == 0
        return RuleCheckResult(
            passed=passed,
            triggered_rules=triggered_rules,
            hard_action=hard_action
        )
