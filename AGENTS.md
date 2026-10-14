# Project Guidelines & Agent Instructions

This document defines the mandatory project-level guidelines, security standards, coding practices, testing policies, and architectural requirements for this repository. Every developer, contributor, and AI coding agent working on this codebase **must strictly adhere** to the instructions outlined below.

---

## 1. Zero-Trust Security & Git Hygiene

This repository is designed to be hosted publicly on GitHub/GitLab. Strict hygiene is enforced:

### 1.1 No Hardcoded Secrets
* **Strict Rule:** Never hardcode API keys, tokens, passwords, private keys, connection strings, or sensitive credentials anywhere in source code, configuration files, commit messages, or test suites.
* **Secret Management:**
  * All secrets must be loaded dynamically at runtime via environment variables or secure secret managers (e.g., `.env` ignored by git, HashiCorp Vault, AWS Secrets Manager, GitHub Secrets in CI/CD).
  * A template file [`.env.example`](file:///.env.example) must be maintained with dummy placeholder values and descriptive comments.
  * Pre-commit hooks (e.g., `gitleaks` or `detect-secrets`) and CI secret scanning are mandatory.

### 1.2 No Local Static Paths
* **Strict Rule:** Never hardcode machine-specific absolute file paths (e.g., `C:\Users\...`, `/home/username/...`, `/tmp/...`).
* **Path Resolution:**
  * All internal file paths must be resolved dynamically relative to the project root using standard path libraries (e.g., Python's `pathlib.Path(__file__).resolve().parents[...]` or Node.js `path.resolve(__dirname, ...)`).
  * Configurable storage, log, or data directories must be controlled via environment variables (e.g., `DATA_DIR`, `LOG_DIR`, `ARTIFACTS_DIR`) with sensible relative defaults (e.g., `./data`, `./logs`).
* **Cross-Platform Compatibility:**
  * Use platform-agnostic path separators (`pathlib.Path` or `os.path.join`). Never assume Windows backslashes (`\`) or Unix forward slashes (`/`) in string concatenation.

---

## 2. LLM Architecture: Primary & Fallback Strategy

The application hosts and benchmarks LLM-powered workloads with and without JEV acceleration:

### 2.1 Provider Hierarchy
1. **Primary LLM:** **Sarvam AI (105B / Sarvam Models)**
   * All benchmark scenarios and user inferences should route to Sarvam AI by default.
   * Connection: REST API / OpenAI-compatible endpoint with configurable timeout, retry count, and streaming token collection.
2. **Fallback LLM:** **OpenAI (`gpt-4o` / `gpt-4o-mini`)**
   * Automatically triggered on Sarvam AI rate limits (`429`), timeouts, server downtime (`5xx`), or network partition.
   * Fallback transitions must emit structured audit events and metrics (`fallback_triggered=True`, `source_provider="sarvam"`, `target_provider="openai"`, `error_code=...`).

### 2.2 Benchmark Tagging & Telemetry
* Every request must record:
  * `route_type`: `with_jev` vs `without_jev`
  * `provider`: `sarvam` vs `openai`
  * `model_name`: Exact model version
  * `time_to_first_token_ms` (TTFT)
  * `inter_token_latency_ms` (ITL)
  * `total_latency_ms`
  * `prompt_tokens` & `completion_tokens`
  * `status_code` & error classification

---

## 3. Role-Based Access Control (RBAC) & Hierarchy

The application enforces a granular, hierarchical RBAC model across APIs and dashboards:

| Role | Hierarchy Level | Capabilities |
| :--- | :---: | :--- |
| **Super Admin** | 4 | System-wide configuration, API key management, user management, full benchmark control, audit logs. |
| **Benchmark Admin** | 3 | Configure and run benchmarks, modify dataset profiles, toggle JEV modes, view all metrics. |
| **Analyst / Auditor** | 2 | Read-only access to completed benchmark runs, metric comparisons, export CSV/JSON reports. |
| **Standard User** | 1 | Execute interactive queries against the LLM gateway, view personal query history. |
| **Service Account** | 1 (Machine) | Token-authenticated programmatic access for automated benchmark stress runners and CI jobs. |

* RBAC checks must be implemented via declarative middleware / dependency injection (e.g., FastAPI dependencies or middleware filters).
* Multi-factor or JWT-based authentication with role claims.

---

## 4. Testing Standards & Quality Gates

Code coverage and end-to-end regression testing are mandatory before merging any PR:

### 4.1 Unit Testing (`pytest`)
* Target minimum **85% code coverage**.
* Mock all external LLM API calls using mock fixtures (`pytest-mock`, `respx`, or `vcrpy`) to prevent real API costs and prevent secret leakage during CI.
* Dedicated unit test suites must verify:
  * RBAC permission matrix (unauthorized access returns `403 Forbidden`).
  * Sarvam AI -> OpenAI fallback switching upon mock failure.
  * Absence of hardcoded static paths (automated static analysis tests).
  * JEV routing layer vs non-JEV direct routing.

### 4.2 Integration & Performance Testing
* Concurrency benchmarks (1, 5, 10, 50, 100 concurrent workers) using Locust or asynchronous runner.
* Latency percentiles calculation: p50, p90, p95, p99.

### 4.3 UI & End-to-End Testing (Selenium / Playwright)
* Automated browser tests for the benchmark UI / dashboard:
  * Admin login and RBAC role view restrictions.
  * Triggering a benchmark run.
  * Real-time metric graph rendering and comparison tables (With JEV vs Without JEV).
  * Report download / export functionality.

---

## 5. Documentation Requirements

Documentation is treated as code and must be kept up to date:
* Any change to an API, model provider, RBAC permission, or benchmark metric must update:
  * [README.md](file:///README.md) - Project overview, installation, and quickstart.
  * [ARCHITECTURE.md](file:///ARCHITECTURE.md) - System architecture, JEV integration diagram, data flow.
  * [BENCHMARK_DESIGN.md](file:///BENCHMARK_DESIGN.md) - Methodology, dataset specification, hardware profile, metrics definitions.
* Docstrings and OpenAPI/Swagger specifications (`/docs`) must accompany all endpoints and classes.

---

## 6. Pre-Commit & CI Validation Checklist

Before committing or pushing changes:
1. `git status` — Ensure no `.env`, credentials, or generated benchmark data files are staged.
2. `pytest tests/unit/` — All unit tests pass.
3. `flake8` / `black` / `ruff` — Code formatted and lint errors resolved.
4. `python scripts/check_secrets_and_paths.py` — Automated scanner detects zero secrets and zero machine-local paths.
