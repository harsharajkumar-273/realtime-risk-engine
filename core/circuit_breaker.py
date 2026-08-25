import time
import logging
from enum import Enum
from config import settings

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation, ML model active
    OPEN = "OPEN"          # ML model failing/bypassed, using Rule Fallback
    HALF_OPEN = "HALF_OPEN"# Testing ML recovery

class CircuitBreaker:
    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def allow_request(self) -> bool:
        """Check if request to ML model is allowed."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > settings.CIRCUIT_RECOVERY_TIME_SEC:
                logger.info("Circuit Breaker moving from OPEN to HALF_OPEN. Testing ML service...")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        return True

    def record_success(self):
        """Record successful ML inference."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit Breaker ML recovery confirmed. Moving to CLOSED state.")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, reason: str = ""):
        """Record ML inference failure or latency timeout."""
        self.failure_count += 1
        logger.warning(f"Circuit Breaker recorded ML failure ({self.failure_count}/{settings.CIRCUIT_FAILURE_THRESHOLD}): {reason}")
        
        if self.failure_count >= settings.CIRCUIT_FAILURE_THRESHOLD or self.state == CircuitState.HALF_OPEN:
            if self.state != CircuitState.OPEN:
                logger.error(f"Circuit Breaker TRIPPED to OPEN state! Falling back to rule engine for {settings.CIRCUIT_RECOVERY_TIME_SEC}s.")
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
