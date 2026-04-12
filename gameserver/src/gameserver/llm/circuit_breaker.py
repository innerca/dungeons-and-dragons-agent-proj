"""Circuit Breaker for LLM providers.

Implements the circuit breaker pattern to gracefully handle LLM failures:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests fail fast
- HALF_OPEN: Testing if service has recovered

State transitions:
    CLOSED → OPEN: fail_rate > 50% AND request_count >= 5 in 60s window
    OPEN → HALF_OPEN: after 30s timeout
    HALF_OPEN → CLOSED: probe request succeeds
    HALF_OPEN → OPEN: probe request fails
"""

from __future__ import annotations

import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: float = 0.5      # Fail rate > 50% triggers open
    min_requests: int = 5               # Minimum requests before evaluation
    window_seconds: float = 60.0        # Sliding window size
    open_duration_seconds: float = 30.0 # Time before half-open
    half_open_max_calls: int = 1        # Max calls in half-open state


@dataclass
class _RequestRecord:
    """Internal record of a request outcome."""
    timestamp: float
    success: bool


class CircuitBreaker:
    """Thread-safe circuit breaker for LLM providers.
    
    Usage:
        cb = CircuitBreaker("openai")
        
        @cb.protect
        async def call_llm(...):
            ...
    """
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._state_changed_at = time.time()
        self._records: list[_RequestRecord] = []
        self._half_open_calls = 0
        
        self._lock = threading.RLock()
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        with self._lock:
            return self._state
    
    def _clean_old_records(self) -> None:
        """Remove records outside the sliding window."""
        cutoff = time.time() - self.config.window_seconds
        self._records = [r for r in self._records if r.timestamp > cutoff]
    
    def _evaluate_state(self) -> None:
        """Evaluate if we should transition to OPEN state."""
        if self._state != CircuitState.CLOSED:
            return
        
        self._clean_old_records()
        
        if len(self._records) < self.config.min_requests:
            return
        
        failures = sum(1 for r in self._records if not r.success)
        fail_rate = failures / len(self._records)
        
        if fail_rate > self.config.failure_threshold:
            self._state = CircuitState.OPEN
            self._state_changed_at = time.time()
            logger.warning(
                "trace=no-trace step=circuit_breaker status=open provider=%s fail_rate=%.2f",
                self.name, fail_rate
            )
    
    def _try_transition_to_half_open(self) -> bool:
        """Check if we should transition from OPEN to HALF_OPEN."""
        if self._state != CircuitState.OPEN:
            return False
        
        elapsed = time.time() - self._state_changed_at
        if elapsed >= self.config.open_duration_seconds:
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            self._state_changed_at = time.time()
            logger.info(
                "trace=no-trace step=circuit_breaker status=half_open provider=%s",
                self.name
            )
            return True
        return False
    
    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                if self._try_transition_to_half_open():
                    self._half_open_calls += 1
                    return True
                return False
            
            # HALF_OPEN
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
    
    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            now = time.time()
            self._records.append(_RequestRecord(now, True))
            self._clean_old_records()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._half_open_calls = 0
                self._state_changed_at = now
                logger.info(
                    "trace=no-trace step=circuit_breaker status=closed provider=%s",
                    self.name
                )
    
    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            now = time.time()
            self._records.append(_RequestRecord(now, False))
            self._clean_old_records()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._state_changed_at = now
                logger.warning(
                    "trace=no-trace step=circuit_breaker status=open provider=%s reason=probe_failed",
                    self.name
                )
            else:
                self._evaluate_state()
    
    def get_stats(self) -> dict[str, Any]:
        """Get current circuit breaker statistics."""
        with self._lock:
            self._clean_old_records()
            total = len(self._records)
            failures = sum(1 for r in self._records if not r.success)
            return {
                "state": self._state.value,
                "total_requests": total,
                "failures": failures,
                "fail_rate": failures / total if total > 0 else 0.0,
            }
    
    def protect(self, func: Callable) -> Callable:
        """Decorator to protect a function with circuit breaker."""
        async def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker for '{self.name}' is OPEN"
                )
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
    """Get or create a circuit breaker for a provider."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def reset_circuit_breaker(name: str) -> None:
    """Reset a circuit breaker (for testing)."""
    if name in _circuit_breakers:
        del _circuit_breakers[name]
