#!/usr/bin/env python3
"""
CLI Benchmark Runner — Jev System One Decision Model vs Sarvam AI 105B Generative LLM
Compares:
  - Without Jev: Traditional System 2 Generative LLM (Autoregressive, generates tokens, high cost)
  - With Jev   : TypeSafe AI System 1 Decision Model (Non-autoregressive, 0 tokens, calibrated probabilities)
"""
import argparse
import asyncio
import json
import logging
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tabulate import tabulate
from src.config import settings
from src.benchmark.runner import BenchmarkRunner
from src.benchmark.visualizer import generate_linkedin_benchmark_chart

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_cli")


async def main():
    parser = argparse.ArgumentParser(description="Run Jev System One vs Sarvam 105B LLM Benchmark")
    parser.add_argument("--concurrency", type=str, default="1,5,10", help="Concurrency tiers (default: 1,5,10)")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per tier (default: 3)")
    args = parser.parse_args()

    concurrency_levels = [int(c.strip()) for c in args.concurrency.split(",") if c.strip()]
    iterations = args.iterations

    print("\n" + "="*80)
    print("  Jev (System 1 Decision Model) vs Sarvam AI 105B (System 2 Generative LLM)")
    print(f"  Tiers: {concurrency_levels} | Iterations per tier: {iterations}")
    print("  Classification, Routing, & Decision Workload Benchmark")
    print("="*80 + "\n")

    runner = BenchmarkRunner()
    table_data = []

    chart_data = {
        "concurrency": concurrency_levels,
        "e2e_without": [],
        "e2e_with": [],
        "cost_without_1k": [],
        "cost_with_1k": [],
    }

    for c in concurrency_levels:
        print(f"  [*] Running tier c={c} ({iterations} decision tasks per scenario)...")

        res_without = await runner.run_scenario(with_jev=False, concurrency=c, iterations=iterations)
        res_with = await runner.run_scenario(with_jev=True, concurrency=c, iterations=iterations)

        latency_gain_x = round(res_without.e2e_latency_ms.p50 / max(0.1, res_with.e2e_latency_ms.p50), 2)
        cost_saving_pct = round((1 - res_with.total_cost_usd / max(1e-10, res_without.total_cost_usd)) * 100, 1)

        chart_data["e2e_without"].append(round(res_without.e2e_latency_ms.p50, 1))
        chart_data["e2e_with"].append(round(res_with.e2e_latency_ms.p50, 1))

        # Extrapolate to cost per 1,000 decisions
        cost_1k_without = round((res_without.total_cost_usd / max(1, res_without.successful_requests)) * 1000, 2)
        cost_1k_with = round((res_with.total_cost_usd / max(1, res_with.successful_requests)) * 1000, 4)
        chart_data["cost_without_1k"].append(cost_1k_without)
        chart_data["cost_with_1k"].append(cost_1k_with)

        table_data.extend([
            [f"c={c}", "Without Jev (105B LLM)",
             f"{res_without.e2e_latency_ms.p50:.1f} ms",
             f"{res_without.total_requests * 5} tokens",
             f"${res_without.total_cost_usd:.6f}",
             "Autoregressive text generation"],
            [f"c={c}", "With Jev (System 1 Model)",
             f"{res_with.e2e_latency_ms.p50:.1f} ms",
             "0 tokens (Typed)",
             f"${res_with.total_cost_usd:.6f}",
             f"-{cost_saving_pct}% cost | {latency_gain_x}x speed | Calibrated probabilities"],
            ["", "", "", "", "", ""],
        ])

    headers = ["Concurrency", "Architecture", "Latency p50", "Tokens Generated", "Total Cost $", "Decision Performance"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="github") + "\n")

    results_file = settings.RESULTS_DIR / "live_benchmark_run.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({"concurrency_levels": concurrency_levels, "data": chart_data}, f, indent=2)

    chart_file = generate_linkedin_benchmark_chart(data=chart_data)
    print(f"  [+] Results saved: {results_file}")
    print(f"  [+] Infographic updated: {chart_file}\n")


if __name__ == "__main__":
    asyncio.run(main())
