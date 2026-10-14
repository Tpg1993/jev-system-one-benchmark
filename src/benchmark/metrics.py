import numpy as np
from typing import List
from pydantic import BaseModel


class MetricSummary(BaseModel):
    sample_count: int
    mean: float
    std_dev: float
    p50: float
    p90: float
    p95: float
    p99: float
    min_val: float
    max_val: float


class BenchmarkResultSummary(BaseModel):
    scenario: str                         # "with_jev" | "without_jev"
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    fallback_requests: int
    total_duration_sec: float
    requests_per_second: float
    token_throughput_per_sec: float

    # Cost tracking
    total_cost_usd: float = 0.0

    # JEV-specific telemetry
    jev_speculative_tokens_accepted: int = 0

    # Latency distributions
    ttft_ms: MetricSummary
    itl_ms: MetricSummary
    e2e_latency_ms: MetricSummary

    # Kept for API compatibility but always 0 (no app-level caching)
    cache_hit_rate_pct: float = 0.0


def calculate_metric_summary(values: List[float]) -> MetricSummary:
    if not values:
        return MetricSummary(
            sample_count=0, mean=0.0, std_dev=0.0, p50=0.0,
            p90=0.0, p95=0.0, p99=0.0, min_val=0.0, max_val=0.0,
        )
    arr = np.array(values, dtype=float)
    return MetricSummary(
        sample_count=len(values),
        mean=float(np.mean(arr)),
        std_dev=float(np.std(arr)),
        p50=float(np.percentile(arr, 50)),
        p90=float(np.percentile(arr, 90)),
        p95=float(np.percentile(arr, 95)),
        p99=float(np.percentile(arr, 99)),
        min_val=float(np.min(arr)),
        max_val=float(np.max(arr)),
    )
