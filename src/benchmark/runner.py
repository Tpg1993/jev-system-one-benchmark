import asyncio
import json
import time
from typing import List
from src.config import settings
from src.jev_adapter.adapter import JEVAdapter
from src.benchmark.metrics import calculate_metric_summary, BenchmarkResultSummary


class BenchmarkRunner:
    """
    Executes the System 1 (Jev Decision Model) vs System 2 (Sarvam AI 105B) benchmark.
    Workload: Programmatic decision making, classification, and routing.
    """

    DEFAULT_DECISION_CONTEXT = (
        "Enterprise document and interaction stream: Customer support tickets, "
        "invoice matching, policy compliance verification, and routing rules."
    )

    def __init__(self, adapter: JEVAdapter = None):
        self.adapter = adapter or JEVAdapter()

    def load_prompts(self) -> List[str]:
        prompt_file = settings.BENCHMARK_PROMPT_DATASET_PATH
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [p["prompt"] if isinstance(p, dict) else str(p) for p in data]
        return [
            "Classify this incoming ticket: 'Urgent: Unable to authenticate via SSO on mobile app.'",
            "Evaluate compliance: 'Vendor invoices over $10,000 require dual managerial sign-off.'",
            "Route request: 'Customer requesting cancellation and full annual refund.'",
            "Detect intent: 'Where can I download the SOC 2 Type II compliance report?'",
            "Determine risk score: 'International wire transfer of $75,000 from newly registered account.'",
        ]

    async def _worker_task(
        self,
        prompt: str,
        context: str,
        with_jev: bool,
        results_list: list,
    ):
        try:
            resp = await self.adapter.execute_decision_benchmark(
                context=context,
                question=prompt,
                with_jev=with_jev,
            )
            results_list.append({
                "success": True,
                "total_latency_ms": resp.total_latency_ms,
                "completion_tokens": resp.completion_tokens,
                "prompt_tokens": resp.prompt_tokens,
                "estimated_cost_usd": resp.estimated_cost_usd,
                "jev_active": resp.jev_active,
                "fallback": resp.fallback_triggered,
            })
        except Exception as e:
            results_list.append({"success": False, "error": str(e), "fallback": False})

    async def run_scenario(
        self,
        with_jev: bool,
        concurrency: int,
        iterations: int = 10,
        context: str = "",
    ) -> BenchmarkResultSummary:
        scenario_name = "with_jev" if with_jev else "without_jev"
        prompts = self.load_prompts()
        ctx = context or self.DEFAULT_DECISION_CONTEXT
        results: list = []

        start_time = time.perf_counter()
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_worker(p: str):
            async with semaphore:
                await self._worker_task(p, ctx, with_jev=with_jev, results_list=results)

        tasks = [bounded_worker(prompts[i % len(prompts)]) for i in range(iterations)]
        await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - start_time

        successful = [r for r in results if r.get("success")]
        failed_count = len(results) - len(successful)
        fallback_count = sum(1 for r in successful if r.get("fallback"))

        e2e_vals = [r["total_latency_ms"] for r in successful]
        total_tokens = sum(r.get("completion_tokens", 0) for r in successful)
        total_cost = sum(r.get("estimated_cost_usd", 0) for r in successful)

        dummy_metric = calculate_metric_summary([])
        latency_metric = calculate_metric_summary(e2e_vals)

        return BenchmarkResultSummary(
            scenario=scenario_name,
            concurrency=concurrency,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=failed_count,
            fallback_requests=fallback_count,
            total_duration_sec=total_duration,
            requests_per_second=len(successful) / max(0.001, total_duration),
            token_throughput_per_sec=total_tokens / max(0.001, total_duration),
            total_cost_usd=round(total_cost, 8),
            jev_speculative_tokens_accepted=0,
            ttft_ms=dummy_metric,
            itl_ms=dummy_metric,
            e2e_latency_ms=latency_metric,
            cache_hit_rate_pct=0.0,
        )
