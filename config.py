import os
from pydantic import BaseModel

class Config(BaseModel):
    # App Settings
    APP_NAME: str = "Real-Time Transaction Risk Engine"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = 0
    REDIS_TIMEOUT: float = 0.5  # 500ms max timeout for feature store
    
    # Risk Rule Thresholds
    MAX_SINGLE_TRANSACTION_AMOUNT: float = 10000.0  # Max single tx before hard flag
    MAX_VELOCITY_5M: int = 5  # Max txs per user in 5 minutes
    HIGH_RISK_AMOUNT_THRESHOLD: float = 2500.0
    IMPOSSIBLE_SPEED_KMH: float = 800.0  # Travel speed threshold between transactions
    
    # ML & Circuit Breaker Thresholds
    ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "ml/model_artifact.joblib")
    ML_LATENCY_THRESHOLD_MS: float = 20.0  # If ML takes > 20ms, increment circuit failure
    CIRCUIT_FAILURE_THRESHOLD: int = 3
    CIRCUIT_RECOVERY_TIME_SEC: float = 10.0
    RISK_SCORE_DECLINE_THRESHOLD: float = 0.75
    RISK_SCORE_REVIEW_THRESHOLD: float = 0.45

settings = Config()
