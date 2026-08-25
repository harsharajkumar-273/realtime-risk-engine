import time
import random
import uuid
import asyncio
import numpy as np
from typing import Dict, Any, Generator

# Major US Tech/Finance Cities lat/lon
CITIES = [
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "country": "US"},
    {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194, "country": "US"},
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "country": "US"},
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "country": "JP"},
    {"name": "High Risk Country", "lat": 39.0392, "lon": 125.7625, "country": "XX"}
]

MCC_CODES = [5411, 5812, 5311, 5912, 6012, 7995, 6211]  # Supermarkets, Dining, Retail, Gambling, Financial

class TransactionStreamGenerator:
    def __init__(self, num_users: int = 100):
        self.user_ids = [f"acc_{1000 + i}" for i in range(num_users)]
        self.anomaly_injection_mode = False

    def generate_single_transaction(self, force_fraud_type: str = None) -> Dict[str, Any]:
        tx_id = f"tx_{uuid.uuid4().hex[:10]}"
        account_id = random.choice(self.user_ids)
        timestamp = time.time()
        
        # Decide if this transaction is an anomaly
        is_anomaly = force_fraud_type is not None or (random.random() < 0.12 if self.anomaly_injection_mode else random.random() < 0.04)
        
        if not is_anomaly:
            # Normal Transaction
            amount = round(float(np.random.exponential(scale=35.0)) + 1.5, 2)
            city = CITIES[0] if random.random() < 0.8 else CITIES[1]
            country = city["country"]
            mcc = random.choice([5411, 5812, 5311, 5912])
            lat = city["lat"] + random.uniform(-0.05, 0.05)
            lon = city["lon"] + random.uniform(-0.05, 0.05)
        else:
            fraud_type = force_fraud_type or random.choice(["HIGH_AMOUNT", "VELOCITY_SPIKE", "IMPOSSIBLE_TRAVEL", "SANCTIONED_GEO"])
            
            if fraud_type == "HIGH_AMOUNT":
                amount = round(random.uniform(12000.0, 50000.0), 2)
                city = CITIES[0]
                country = "US"
                mcc = 6211
                lat, lon = city["lat"], city["lon"]
                
            elif fraud_type == "VELOCITY_SPIKE":
                amount = round(random.uniform(200.0, 800.0), 2)
                city = CITIES[1]
                country = "US"
                mcc = 7995
                lat, lon = city["lat"], city["lon"]
                
            elif fraud_type == "IMPOSSIBLE_TRAVEL":
                # Travel from NY to Tokyo in 2 seconds
                amount = round(random.uniform(400.0, 1500.0), 2)
                city = CITIES[4]  # Tokyo
                country = "JP"
                mcc = 5912
                lat, lon = city["lat"], city["lon"]
                
            elif fraud_type == "SANCTIONED_GEO":
                amount = round(random.uniform(500.0, 2000.0), 2)
                city = CITIES[5]  # XX
                country = "XX"
                mcc = 6012
                lat, lon = city["lat"], city["lon"]

        return {
            "transaction_id": tx_id,
            "account_id": account_id,
            "amount": amount,
            "currency": "USD",
            "country": country,
            "mcc": mcc,
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "timestamp": timestamp
        }

    async def stream_transactions(self, tps: float = 10.0):
        """Async generator yielding transactions at specified Transactions Per Second (TPS)."""
        interval = 1.0 / tps
        while True:
            yield self.generate_single_transaction()
            await asyncio.sleep(interval)
