# Benchmark Design & Methodology

This document outlines the experimental design, testing metrics, statistical methodology, and datasets used to compare the LLM-hosted application **with JEV** vs. **without JEV**.

---

## 1. Benchmarking Metrics

| Metric | Symbol / Unit | Description | Importance |
| :--- | :---: | :--- | :--- |
| **Time to First Token** | **TTFT** (ms) | Time elapsed from sending the request until the first generated token arrives. | Measures responsiveness and prompt processing latency. |
| **Inter-Token Latency** | **ITL** (ms) | Average time elapsed between consecutive generated tokens. | Measures generation fluency and decode phase throughput. |
| **Total Request Latency** | **E2E** (ms) | Total elapsed wall-clock time from request initiation to completion. | Core user-perceived latency metric. |
| **Throughput** | **Tokens / sec** | Total completion tokens generated divided by generation time. | System capacity indicator. |
| **Requests Per Second** | **RPS** | Number of completed requests processed per second under load. | Concurrency scaling metric. |
| **Error / Fallback Rate** | **%** | Percentage of requests that errored or triggered fallback to OpenAI. | System reliability & provider stability. |
| **Cache Hit Ratio** | **%** (JEV) | Ratio of requests or prefix tokens satisfied by the JEV cache. | Quantifies JEV acceleration efficacy. |

---

## 2. Benchmark Concurrency Matrix

Each benchmark run executes across tiered concurrency profiles:

1. **Single Stream (c=1):** Baseline latency profile (pure TTFT and single-stream throughput).
2. **Light Load (c=5):** Typical interactive multi-user scenario.
3. **Medium Load (c=10, c=25):** Stressed concurrency, tests queueing delays.
4. **Peak Stress (c=50, c=100):** System saturation point, tests graceful degradation and fallback triggering.

---

## 3. Workload Datasets

Datasets are located in the dynamic directory `data/`:
* **Dataset A (Short Prompt, Short Completion):** Typical interactive Q&A (100–300 input tokens, ~100 output tokens).
* **Dataset B (Long Prompt, Short Completion):** Retrieval-Augmented Generation / summarization (1k–4k input tokens, ~150 output tokens). *Ideal for evaluating JEV prefix-caching benefits.*
* **Dataset C (Medium Prompt, Long Completion):** Code generation / structured document generation (500 input tokens, ~800 output tokens).
* **Dataset D (Multilingual / Indic Corpora):** Sarvam AI specialized evaluation set (Hindi, Marathi, Tamil, Telugu, Kannada, Bengali, and English).

---

## 4. Test Isolation & Statistical Validity

To ensure scientific rigor:
1. **Warmup Requests:** 5 warmup requests precede each recorded test to warm caches and connection pools.
2. **Sample Size:** Minimum 30 iterations per concurrency level to ensure statistical significance.
3. **Statistical Aggregation:** Metrics report **p50 (median)**, **p90**, **p95**, **p99**, and Standard Deviation, rather than simple arithmetic mean.
4. **Environment Tagging:** Every run records system hardware, JEV configuration flags, and active provider version.
