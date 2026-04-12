"""Request metrics tracking for observability and cost estimation.

Tracks per-request metrics including:
- RAG retrieval latency
- LLM calls (model, tokens, latency)
- Tool calls (tool name, latency, success)
- Cost estimation based on model pricing
- Slow request detection
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Model pricing (USD per million tokens)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku": {"input": 0.8, "output": 4.0},
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}

# Default pricing for unknown models
DEFAULT_PRICING = {"input": 5.0, "output": 15.0}

# Slow request threshold (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 5000


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call."""
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    provider: str = ""
    success: bool = True
    error: str = ""


@dataclass
class ToolCallMetrics:
    """Metrics for a single tool call."""
    tool: str
    latency_ms: float
    success: bool
    error: str = ""


@dataclass
class RAGMetrics:
    """Metrics for RAG retrieval."""
    chunks_count: int
    top_score: float
    latency_ms: float
    success: bool = True
    error: str = ""


@dataclass
class RequestMetrics:
    """Complete metrics for a single game request.
    
    Usage:
        metrics = RequestMetrics(trace_id="abc123")
        
        # RAG retrieval
        rag_result = query_novels(...)
        metrics.add_rag_result(chunks_count, top_score, latency_ms)
        
        # LLM call
        metrics.add_llm_call("gpt-4o", 1000, 500, 1200)
        
        # Tool call
        metrics.add_tool_call("attack", 50, True)
        
        # Final logging
        metrics.log_summary(player_id)
        metrics.check_slow_request()
    """
    
    trace_id: str
    start_time: float = field(default_factory=time.time)
    
    # RAG metrics
    rag: RAGMetrics | None = None
    
    # LLM calls
    llm_calls: list[LLMCallMetrics] = field(default_factory=list)
    
    # Tool calls
    tool_calls: list[ToolCallMetrics] = field(default_factory=list)
    
    # Totals (computed on the fly)
    _rag_ms: float = 0.0
    _llm_ms: float = 0.0
    _tool_ms: float = 0.0
    
    def add_rag_result(self, chunks_count: int, top_score: float, latency_ms: float, success: bool = True, error: str = "") -> None:
        """Add RAG retrieval metrics."""
        self.rag = RAGMetrics(
            chunks_count=chunks_count,
            top_score=top_score,
            latency_ms=latency_ms,
            success=success,
            error=error,
        )
        self._rag_ms = latency_ms
    
    def add_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        provider: str = "",
        success: bool = True,
        error: str = "",
    ) -> None:
        """Add an LLM call metrics."""
        self.llm_calls.append(LLMCallMetrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            provider=provider,
            success=success,
            error=error,
        ))
        self._llm_ms += latency_ms
    
    def add_tool_call(self, tool: str, latency_ms: float, success: bool, error: str = "") -> None:
        """Add a tool call metrics."""
        self.tool_calls.append(ToolCallMetrics(
            tool=tool,
            latency_ms=latency_ms,
            success=success,
            error=error,
        ))
        self._tool_ms += latency_ms
    
    def total_ms(self) -> float:
        """Get total request duration in milliseconds."""
        return (time.time() - self.start_time) * 1000
    
    def total_llm_ms(self) -> float:
        """Get total LLM call time in milliseconds."""
        return self._llm_ms
    
    def total_tool_ms(self) -> float:
        """Get total tool execution time in milliseconds."""
        return self._tool_ms
    
    def total_input_tokens(self) -> int:
        """Get total input tokens across all LLM calls."""
        return sum(c.input_tokens for c in self.llm_calls)
    
    def total_output_tokens(self) -> int:
        """Get total output tokens across all LLM calls."""
        return sum(c.output_tokens for c in self.llm_calls)
    
    def estimate_cost(self) -> float:
        """Estimate total cost in USD."""
        total_cost = 0.0
        for call in self.llm_calls:
            pricing = MODEL_PRICING.get(call.model, DEFAULT_PRICING)
            input_cost = (call.input_tokens / 1_000_000) * pricing["input"]
            output_cost = (call.output_tokens / 1_000_000) * pricing["output"]
            total_cost += input_cost + output_cost
        return total_cost
    
    def get_model_name(self) -> str:
        """Get the primary model name used."""
        if self.llm_calls:
            return self.llm_calls[0].model
        return "unknown"
    
    def log_summary(self, player_id: str) -> None:
        """Log request summary at INFO level."""
        total_ms = self.total_ms()
        llm_ms = self.total_llm_ms()
        tool_ms = self.total_tool_ms()
        input_tokens = self.total_input_tokens()
        output_tokens = self.total_output_tokens()
        cost = self.estimate_cost()
        model = self.get_model_name()
        
        # RAG info
        rag_chunks = self.rag.chunks_count if self.rag else 0
        rag_score = self.rag.top_score if self.rag else 0.0
        rag_ms = self.rag.latency_ms if self.rag else 0.0
        
        logger.info(
            "trace=%s step=request_summary player=%s model=%s "
            "total_ms=%.1f rag_ms=%.1f llm_ms=%.1f tool_ms=%.1f "
            "rag_chunks=%d rag_score=%.3f "
            "input_tokens=%d output_tokens=%d cost_usd=%.6f "
            "llm_calls=%d tool_calls=%d",
            self.trace_id, player_id, model,
            total_ms, rag_ms, llm_ms, tool_ms,
            rag_chunks, rag_score,
            input_tokens, output_tokens, cost,
            len(self.llm_calls), len(self.tool_calls),
        )
    
    def check_slow_request(self) -> bool:
        """Check if this is a slow request and log warning if so.
        
        Returns True if slow request detected.
        """
        total_ms = self.total_ms()
        if total_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "trace=%s step=slow_request_alert latency_ms=%.1f threshold_ms=%d "
                "rag_ms=%.1f llm_ms=%.1f tool_ms=%.1f",
                self.trace_id, total_ms, SLOW_REQUEST_THRESHOLD_MS,
                self._rag_ms, self._llm_ms, self._tool_ms,
            )
            return True
        return False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "total_ms": self.total_ms(),
            "rag": {
                "chunks_count": self.rag.chunks_count if self.rag else 0,
                "top_score": self.rag.top_score if self.rag else 0.0,
                "latency_ms": self.rag.latency_ms if self.rag else 0.0,
                "success": self.rag.success if self.rag else True,
            },
            "llm": {
                "calls": len(self.llm_calls),
                "total_input_tokens": self.total_input_tokens(),
                "total_output_tokens": self.total_output_tokens(),
                "total_ms": self.total_llm_ms(),
                "model": self.get_model_name(),
            },
            "tools": {
                "calls": len(self.tool_calls),
                "total_ms": self.total_tool_ms(),
                "success_count": sum(1 for t in self.tool_calls if t.success),
            },
            "cost_usd": self.estimate_cost(),
        }
