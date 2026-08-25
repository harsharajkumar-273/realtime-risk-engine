import time
import logging
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict
from config import settings

logger = logging.getLogger(__name__)

class FeatureStore:
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        self._init_redis()
        # Fallback In-Memory Storage if Redis is unavailable
        self._in_memory_tx_history = defaultdict(list)
        self._in_memory_user_profiles = {}

    def _init_redis(self):
        try:
            import redis
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_timeout=settings.REDIS_TIMEOUT,
                decode_responses=True
            )
            client.ping()
            self.redis_client = client
            self.use_redis = True
            logger.info("Successfully connected to Redis feature store.")
        except Exception as e:
            logger.warning(f"Redis connection unavailable ({e}). Falling back to In-Memory Feature Store.")
            self.use_redis = False

    def get_user_features(self, account_id: str, current_time: Optional[float] = None) -> Dict[str, Any]:
        """Fetch real-time rolling aggregates for a given account ID."""
        now = current_time or time.time()
        
        if self.use_redis:
            try:
                # Redis Pipeline for low latency batch read
                pipe = self.redis_client.pipeline()
                pipe.zcount(f"user:{account_id}:txs", now - 300, now)  # 5 min count
                pipe.zrangebyscore(f"user:{account_id}:txs", now - 86400, now, withscores=True)  # 24h txs
                pipe.hgetall(f"user:{account_id}:profile")
                res = pipe.execute()
                
                tx_count_5m = res[0]
                txs_24h = res[1]
                profile = res[2] or {}
                
                spend_24h = sum(float(tx_str.split(":")[0]) for tx_str, _ in txs_24h) if txs_24h else 0.0
                tx_count_24h = len(txs_24h)
                avg_amount_24h = (spend_24h / tx_count_24h) if tx_count_24h > 0 else 0.0
                
                return {
                    "tx_count_5m": tx_count_5m,
                    "spend_24h": spend_24h,
                    "tx_count_24h": tx_count_24h,
                    "avg_amount_24h": avg_amount_24h,
                    "last_lat": float(profile.get("last_lat")) if "last_lat" in profile else None,
                    "last_lon": float(profile.get("last_lon")) if "last_lon" in profile else None,
                    "last_timestamp": float(profile.get("last_timestamp")) if "last_timestamp" in profile else None,
                }
            except Exception as e:
                logger.warning(f"Redis read error ({e}). Switching to in-memory fallback.")
                self.use_redis = False

        # In-memory fallback computation
        user_txs = self._in_memory_tx_history[account_id]
        
        # Prune old records (> 24 hours)
        cutoff_24h = now - 86400
        cutoff_5m = now - 300
        valid_txs = [tx for tx in user_txs if tx["timestamp"] >= cutoff_24h]
        self._in_memory_tx_history[account_id] = valid_txs
        
        txs_5m = [tx for tx in valid_txs if tx["timestamp"] >= cutoff_5m]
        spend_24h = sum(tx["amount"] for tx in valid_txs)
        tx_count_24h = len(valid_txs)
        avg_amount_24h = (spend_24h / tx_count_24h) if tx_count_24h > 0 else 0.0
        
        profile = self._in_memory_user_profiles.get(account_id, {})
        
        return {
            "tx_count_5m": len(txs_5m),
            "spend_24h": spend_24h,
            "tx_count_24h": tx_count_24h,
            "avg_amount_24h": avg_amount_24h,
            "last_lat": profile.get("last_lat"),
            "last_lon": profile.get("last_lon"),
            "last_timestamp": profile.get("last_timestamp"),
        }

    def update_user_features(self, account_id: str, amount: float, lat: float, lon: float, timestamp: float):
        """Update feature store after transaction processing."""
        if self.use_redis:
            try:
                pipe = self.redis_client.pipeline()
                # Store tx amount & timestamp in Sorted Set
                pipe.zadd(f"user:{account_id}:txs", {f"{amount}:{timestamp}": timestamp})
                # Expire sorted set key after 24h
                pipe.expire(f"user:{account_id}:txs", 86400)
                # Update user profile hash
                pipe.hset(f"user:{account_id}:profile", mapping={
                    "last_lat": str(lat),
                    "last_lon": str(lon),
                    "last_timestamp": str(timestamp)
                })
                pipe.execute()
                return
            except Exception as e:
                logger.warning(f"Redis write error ({e}). Using in-memory store.")
                self.use_redis = False

        # In-memory update
        self._in_memory_tx_history[account_id].append({
            "amount": amount,
            "timestamp": timestamp
        })
        self._in_memory_user_profiles[account_id] = {
            "last_lat": lat,
            "last_lon": lon,
            "last_timestamp": timestamp
        }
