# 🚀 Quickstart & Operations Guide: JEV LLM Acceleration Benchmark

A production-ready benchmarking platform comparing **TypeSafe AI's Jev (System 1 Decision Model)** against **Sarvam AI 105B (System 2 Generative LLM)** with resilient **OpenAI (GPT-4o)** fallback and hierarchical Role-Based Access Control (RBAC).

---

## 📋 System Prerequisites

Ensure you have the following installed on your machine:
* **Python 3.10+** (Python 3.12 recommended)
* **Docker Desktop** (optional, recommended for sidecar container mode)
* **Git**

---

## ⚡ 1. Initial Setup & Virtual Environment

Clone the repository and initialize your isolated virtual environment:

### Linux / macOS
```bash
git clone <your-repository-url>
cd <project-folder>

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)
```powershell
git clone <your-repository-url>
cd <project-folder>

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🔐 2. Secret Configuration (.env)

The codebase strictly adheres to **Zero-Trust Security**. Never commit secrets or credentials.

Copy the template file to create your local `.env`:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` and configure your credentials:

```ini
# Primary LLM: Sarvam AI
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_BASE_URL=https://api.sarvam.ai/v1
SARVAM_MODEL_NAME=sarvam-105b-conversations

# Fallback LLM: OpenAI (Used on 429, 5xx, or network timeout)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o

# Security & RBAC Secret
JWT_SECRET_KEY=your_secure_random_hex_string_here
INIT_ADMIN_EMAIL=admin@example.com
INIT_ADMIN_PASSWORD=your_initial_admin_password
```

> [!NOTE]
> Generate a strong 512-bit JWT secret using Python:
> `python -c "import secrets; print(secrets.token_hex(64))"`

---

## 🐳 3. Running the JEV Acceleration Engine (Docker)

To run the JEV sidecar container with Docker Desktop active:

```bash
# Build and launch JEV engine in background
docker compose up -d --build jev-engine

# Verify JEV container is healthy
curl http://localhost:9000/health
```

Expected health output:
```json
{"status":"healthy","service":"jev-acceleration-engine","known_prefixes":0}
```

> [!TIP]
> **Hybrid Flexibility:** If Docker is not running, the application automatically falls back to an in-memory mathematical inference simulation so you can still test without Docker.

---

## 🌐 4. Launching the Web Portal & API Server

Start the FastAPI application and live benchmark dashboard:

```bash
# Linux / macOS
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload

# Windows (PowerShell)
.\.venv\Scripts\uvicorn.exe src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access Points:
- 📊 **Benchmark Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📖 **Interactive OpenAPI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 🩺 **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📈 5. Running the Multi-Tier Benchmark

Execute the automated multi-concurrency benchmark script across concurrency tiers (`c=1, 5, 10`):

```bash
# Run benchmark across tiers (default: c=1,5,10 with 3 iterations each)
python scripts/run_benchmark.py --concurrency 1,5,10 --iterations 3
```

### What this produces:
1. **Console Summary Table:** Markdown-formatted comparison of TTFT, ITL, E2E Latency, Throughput (Tokens/s), and Cost.
2. **Raw Telemetry JSON:** Saved to `benchmark_results/live_benchmark_run.json`.
3. **Publication Infographic Image:** Generated at `benchmark_results/jev_benchmark_comparison.png`.

---

## 🎨 6. Generating LinkedIn Infographics & Posts

To re-generate or customize the publication visualizer:

```bash
python src/benchmark/visualizer.py
```

- **Infographic Chart:** `benchmark_results/jev_benchmark_comparison.png`
- **Next-Gen Hero Visual:** `benchmark_results/jev_linkedin_hero.jpg`
- **Draft LinkedIn Text:** `benchmark_results/linkedin_post.md`

---

## 🛡️ 7. Role-Based Access Control (RBAC) Matrix

Authentication uses stateless JWT bearer tokens with four hierarchical permission levels:

| Role | Level | Accessible Endpoints & Capabilities |
| :--- | :---: | :--- |
| **Super Admin** | 4 | System configuration, user administration (`/api/v1/admin/users`), full benchmark control. |
| **Benchmark Admin** | 3 | Trigger concurrent stress benchmarks (`/api/v1/benchmark/run`), modify parameters. |
| **Analyst / Auditor** | 2 | View completed benchmark runs, download JSON/CSV telemetry reports. |
| **Standard User** | 1 | Execute single interactive inferences (`/api/v1/inference`), view personal query history. |

### Default Test Users:
* `admin@example.com` / `admin_user` (Super Admin, Level 4)
* `bench_admin` (Benchmark Admin, Level 3)
* `analyst_user` (Analyst, Level 2)
* `standard_user` (Standard User, Level 1)

---

## 🧪 8. Testing & Security Quality Gates

Run the mandatory test suite before committing changes:

```bash
# 1. Run unit test suite (RBAC, Fallback, Path Safety)
pytest tests/unit/ -v

# 2. Run automated static analysis for secrets and local paths
python scripts/check_secrets_and_paths.py
```

Both checks must pass (`[PASS]` and `0 errors`) to maintain repo hygiene.
