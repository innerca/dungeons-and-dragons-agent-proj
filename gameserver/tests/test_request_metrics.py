"""Tests for request_metrics module."""

import logging

from gameserver.service.request_metrics import RequestMetrics


def test_first_token_latency_recorded_once() -> None:
    metrics = RequestMetrics(trace_id="trace-1")

    metrics.set_first_token_latency(123.4)
    metrics.set_first_token_latency(456.7)

    assert metrics.first_token_ms == 123.4


def test_log_summary_includes_first_token_latency(caplog) -> None:
    metrics = RequestMetrics(trace_id="trace-2")
    metrics.set_first_token_latency(87.6)
    metrics.add_rag_result(chunks_count=2, top_score=0.12, latency_ms=11.0)
    metrics.add_llm_call(
        model="deepseek-chat",
        input_tokens=120,
        output_tokens=80,
        latency_ms=200.0,
        provider="deepseek",
    )
    metrics.add_tool_call(tool="attack", latency_ms=30.0, success=True)

    with caplog.at_level(logging.INFO):
        metrics.log_summary("player-1")

    assert "step=request_summary" in caplog.text
    assert "first_token_ms=87.6" in caplog.text


def test_to_dict_exposes_first_token_latency() -> None:
    metrics = RequestMetrics(trace_id="trace-3")
    metrics.set_first_token_latency(45.0)
    metrics.mark_stream_success(True)
    metrics.mark_fallback_used()
    metrics.add_tool_call(tool="attack", latency_ms=10.0, success=True)
    metrics.add_tool_call(tool="inspect", latency_ms=5.0, success=False, error="boom")

    payload = metrics.to_dict()

    assert payload["first_token_ms"] == 45.0
    assert payload["stream_success"] is True
    assert payload["fallback_used"] is True
    assert payload["tools"]["success_count"] == 1
    assert payload["tools"]["failure_count"] == 1
