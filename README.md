# JEV vs Non-JEV LLM Benchmarking Suite

A benchmarking framework comparing an LLM-hosted application **with and without JEV acceleration**, using **Sarvam AI (105B)** as the primary model and **OpenAI (`gpt-4o`)** as the automatic resilient fallback. The framework enforces strict zero-trust git hygiene, zero hardcoded secrets/static paths, 4-tier Role-Based Access Control (RBAC), and automated testing suites (unit tests + Selenium browser E2E tests).

---

## 1. Key Features

- **JEV Acceleration Benchmarking:** Direct comparative performance analysis measuring TTFT, ITL, End-to-End latency, throughput (tokens/sec), and RPS scaling across concurrency tiers (1, 5, 10, 25, 50).
- **Dual-Provider Resilient LLM Gateway:**
  - **Primary:** Sarvam AI (105B / Indic specialized models).
  - **Fallback:** OpenAI (`gpt-4o` / `gpt-4o-mini`) triggered automatically on rate-limits, timeouts, or provider 5xx errors.
- **Hierarchical RBAC (4 Levels):**
  - **Super Admin (Level 4):** Full system configuration, user management, API keys, audit logs.
  - **Benchmark Admin (Level 3):** Trigger comparative benchmark runs, modify datasets and JEV cache profiles.
  - **Analyst / Auditor (Level 2):** Read-only access to completed benchmark runs, metric comparisons, and data exports.
  - **Standard User / Service Account (Level 1):** Interactive queries through the resilient gateway and personal history.
- **Zero-Trust Git & Path Hygiene:**
  - No secrets hardcoded anywhere (enforced via `.env.example`, `.gitignore`, and scanner scripts).
  - No machine-specific static paths (`C:\Users\...` or `/home/...`); all paths are derived dynamically relative to project root.
- **Automated Verification:**
  - Unit tests with 100% mocked external API calls (`pytest`).
  - Selenium browser integration tests (`tests/selenium/`).
  - Automated security and path scanner (`scripts/check_secrets_and_paths.py`).

---

## 2. Project Directory Structure

```text
jev-llm-benchmark/
├── .agents/
│   └── rules/
│       └── project-standards.md      # Antigravity project-level rules
├── docs/
│   ├── ARCHITECTURE.md               # Architecture details, JEV vs non-JEV
│   ├── BENCHMARK_DESIGN.md           # Benchmark methodology & metrics
│   └── RBAC_MATRIX.md                # Roles, hierarchy, and permissions table
├── src/
│   ├── __init__.py
│   ├── config.py                     # Dynamic env loading & relative path resolution
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py                 # User, Role, Token schemas
│   │   └── rbac.py                   # Role hierarchy, dependency injection guards
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                   # LLM Base Provider protocol/interface
│   │   ├── sarvam_client.py          # Primary: Sarvam AI 105B client
│   │   ├── openai_fallback.py        # Fallback: OpenAI client
│   │   └── resilient_gateway.py      # Circuit breaker, retry, fallback dispatcher
│   ├── jev_adapter/
│   │   ├── __init__.py
│   │   └── adapter.py                # JEV acceleration & caching vs baseline pipeline
│   ├── benchmark/
│   │   ├── __init__.py
│   │   ├── metrics.py                # TTFT, ITL, RPS, latency percentiles
│   │   └── runner.py                 # Parallel benchmark worker pool executor
│   └── api/
│       ├── __init__.py
│       └── main.py                   # FastAPI app with RBAC routes and UI dashboard
├── data/
│   ├── sample_prompts.json           # Curated prompt datasets
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── benchmark_results/
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_path_safety.py       # Test no absolute/static local paths in codebase
│   │   ├── test_rbac.py              # Test role hierarchy and permissions
│   │   └── test_llm_fallback.py      # Test Sarvam -> OpenAI fallback logic
│   └── selenium/
│       └── test_dashboard_ui.py      # Selenium automated browser tests
├── scripts/
│   └── check_secrets_and_paths.py    # Automated check for secrets & machine paths
├── .env.example                      # Template with dummy values (git safe)
├── .gitignore                        # Git exclusion rules
├── AGENTS.md                         # Mandatory project guidelines
├── pyproject.toml                    # Tool configs (pytest, ruff)
├── requirements.txt                  # Python dependencies
└── README.md                         # Project documentation
```

---

## 3. Installation & Quickstart

### 3.1 Setup Virtual Environment
```bash
# Create local virtual environment
python -m venv .venv

# Activate on Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Or on Linux/macOS:
source .venv/bin/activate
```

### 3.2 Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables
Copy the template to `.env` and fill in credentials:
```bash
cp .env.example .env
```
*(Never commit `.env` to git!)*

---

### 4.1 Launch with Docker Compose (Recommended: App + JEV Sidecar)
```bash
# Start both the JEV Sidecar Engine (:9000) and the Benchmark App (:8000)
docker compose up --build -d

# View sidecar health
curl http://localhost:9000/health

# Open Benchmark Dashboard in browser: http://localhost:8000
```

### 4.2 Launch Locally with Python (.venv)
```bash
# Run FastAPI server locally
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser to access the Benchmark UI Dashboard or [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger OpenAPI documentation.

### 4.3 Run CLI Comparative Benchmark
```bash
python scripts/run_benchmark.py
```

### 4.4 Run Security & Static Path Scan
```bash
python scripts/check_secrets_and_paths.py
```

### 4.5 Run Test Suites
```bash
# Run all unit tests (mocked, fast, no external calls)
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=src --cov-report=term-missing

# Run Selenium Browser Tests (requires running server or base URL configured)
pytest tests/selenium/ -v -m selenium
```
