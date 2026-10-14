from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import time

from src.config import settings
from src.auth.models import Role, RoleLevel, User, Token
from src.auth.rbac import (
    get_current_user,
    require_role_level,
    verify_password,
    create_access_token,
    FAKE_USERS_DB,
)
from src.llm.resilient_gateway import ResilientLLMGateway
from src.jev_adapter.adapter import JEVAdapter
from src.benchmark.runner import BenchmarkRunner

app = FastAPI(
    title="JEV vs Non-JEV LLM Benchmark API",
    description="Benchmarking Sarvam AI 105B (Primary) and OpenAI (Fallback) with and without JEV acceleration under hierarchical RBAC.",
    version="1.0.0",
)

gateway = ResilientLLMGateway()
jev_adapter = JEVAdapter(gateway=gateway)
benchmark_runner = BenchmarkRunner(adapter=jev_adapter)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": "jev-benchmark-portal",
        "jev_sidecar_live": await jev_adapter._probe_sidecar(),
    }


# ------------------------------------------------------------------------------
# Request & Response Schemas
# ------------------------------------------------------------------------------
class InferenceRequest(BaseModel):
    prompt: str
    with_jev: bool = True
    temperature: float = 0.7
    max_tokens: int = 512


class BenchmarkTriggerRequest(BaseModel):
    concurrency_levels: list[int] = [1, 5, 10]
    iterations_per_level: int = 4


# ------------------------------------------------------------------------------
# Auth Routes
# ------------------------------------------------------------------------------
@app.post("/api/v1/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = next(
        (u for u in FAKE_USERS_DB.values() if u["username"] == form_data.username or u["email"] == form_data.username),
        None
    )
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User(**user_dict)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "level": user.role_level}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        role_level=user.role_level,
    )


@app.get("/api/v1/auth/me", response_model=User)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


# ------------------------------------------------------------------------------
# Inference Route (User Level 1+)
# ------------------------------------------------------------------------------
@app.post("/api/v1/inference")
async def execute_inference(
    request: InferenceRequest,
    current_user: User = Depends(require_role_level(RoleLevel.USER)),
):
    """
    Execute single prompt inference through JEV adapter (with or without JEV).
    Accessible to all authenticated users (Level 1+).
    """
    response = await jev_adapter.execute_request(
        prompt=request.prompt,
        with_jev=request.with_jev,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return {
        "status": "success",
        "caller": current_user.username,
        "caller_role": current_user.role,
        "result": response,
    }


# ------------------------------------------------------------------------------
# Auto-Run & Live Comparative Benchmark Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/v1/benchmark/auto-run")
async def auto_run_benchmark():
    """
    Automatically executes a comparative benchmark between With-JEV and Without-JEV
    and returns metrics immediately on application load.
    """
    res_without = await benchmark_runner.run_scenario(with_jev=False, concurrency=1, iterations=3)
    res_with = await benchmark_runner.run_scenario(with_jev=True, concurrency=1, iterations=3)

    # Compute core decision metrics
    latency_speedup = round(res_without.e2e_latency_ms.p50 / max(0.1, res_with.e2e_latency_ms.p50), 2)
    cost_reduction = round((1 - res_with.total_cost_usd / max(1e-10, res_without.total_cost_usd)) * 100, 1)

    return {
        "status": "success",
        "timestamp": time.time(),
        "primary_model": settings.SARVAM_MODEL_NAME,
        "fallback_model": settings.OPENAI_MODEL_NAME,
        "jev_mode_enabled": settings.JEV_ENABLED,
        "speedup_summary": {
            "latency_speedup_x": f"{latency_speedup}x",
            "cost_reduction_pct": f"{cost_reduction}%",
        },
        "without_jev": res_without.model_dump(),
        "with_jev": res_with.model_dump(),
    }


@app.post("/api/v1/benchmark/run")
async def trigger_benchmark(
    request: BenchmarkTriggerRequest,
    current_user: User = Depends(require_role_level(RoleLevel.BENCHMARK_ADMIN)),
):
    """
    Trigger benchmark comparing With-JEV vs Without-JEV across concurrency levels.
    Requires Benchmark Admin (Level 3+) or Super Admin (Level 4).
    """
    comparison_results = []
    for c in request.concurrency_levels:
        res_without = await benchmark_runner.run_scenario(
            with_jev=False, concurrency=c, iterations=request.iterations_per_level
        )
        res_with = await benchmark_runner.run_scenario(
            with_jev=True, concurrency=c, iterations=request.iterations_per_level
        )
        comparison_results.append({
            "concurrency": c,
            "without_jev": res_without.model_dump(),
            "with_jev": res_with.model_dump(),
            "ttft_speedup": round(res_without.ttft_ms.p50 / max(0.1, res_with.ttft_ms.p50), 2),
            "e2e_speedup": round(res_without.e2e_latency_ms.p50 / max(0.1, res_with.e2e_latency_ms.p50), 2),
        })

    return {
        "status": "completed",
        "executed_by": current_user.username,
        "results": comparison_results,
    }


@app.get("/api/v1/benchmark/reports")
async def get_benchmark_reports(
    current_user: User = Depends(require_role_level(RoleLevel.ANALYST)),
):
    return {
        "status": "success",
        "viewer": current_user.username,
        "viewer_role": current_user.role,
        "available_reports": ["benchmark_run_latest.json"],
    }


@app.get("/api/v1/admin/users")
async def list_users(
    current_user: User = Depends(require_role_level(RoleLevel.SUPER_ADMIN)),
):
    return {
        "status": "success",
        "total_users": len(FAKE_USERS_DB),
        "users": [
            {"id": u["id"], "email": u["email"], "username": u["username"], "role": u["role"]}
            for u in FAKE_USERS_DB.values()
        ],
    }


# ------------------------------------------------------------------------------
# Frontend Dashboard (Automatically Loads & Displays Benchmark Comparison)
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JEV LLM Benchmark Portal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --surface: #111827;
            --surface-border: #1f2937;
            --surface-hover: #1e293b;
            --primary: #38bdf8;
            --primary-glow: rgba(56, 189, 248, 0.2);
            --accent-jev: #10b981;
            --accent-nonjev: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 2.5rem;
            line-height: 1.5;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--surface-border);
            margin-bottom: 2rem;
        }
        .brand { display: flex; align-items: center; gap: 0.75rem; }
        .brand h1 { font-size: 1.5rem; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #0f172a;
            border: 1px solid var(--surface-border);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.825rem;
            color: var(--text-muted);
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; }

        .banner {
            background: linear-gradient(135deg, rgba(56,189,248,0.1), rgba(99,102,241,0.08));
            border: 1px solid rgba(56,189,248,0.25);
            border-radius: 12px;
            padding: 1.25rem 1.75rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .banner-text h2 { font-size: 1.15rem; font-weight: 700; color: #bae6fd; }
        .banner-text p { font-size: 0.9rem; color: #94a3b8; }
        .btn {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: white;
            font-weight: 600;
            border: none;
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3);
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(2, 132, 199, 0.45); }
        .btn-secondary {
            background: #1e293b;
            border: 1px solid var(--surface-border);
            color: #cbd5e1;
            box-shadow: none;
        }
        .btn-secondary:hover { background: #334155; }

        /* Metric Comparison Cards Grid */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }
        .card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 1.25rem;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: rgba(56,189,248,0.4); }
        .card-header { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
        
        .side-by-side {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-top: 0.5rem;
        }
        .val-box {
            padding: 0.75rem;
            border-radius: 8px;
            background: #0b1120;
            border: 1px solid #1e293b;
        }
        .val-label { font-size: 0.75rem; color: #64748b; font-weight: 500; }
        .val-num { font-size: 1.4rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
        .val-num.non-jev { color: var(--accent-nonjev); }
        .val-num.jev { color: var(--accent-jev); }
        .speedup-badge {
            margin-top: 0.75rem;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            font-size: 0.8rem;
            font-weight: 700;
        }

        /* Side-by-Side Visual Comparison Section */
        .visual-comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        @media (max-width: 900px) { .visual-comparison { grid-template-columns: 1fr; } }
        
        .scenario-panel {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 1.5rem;
        }
        .panel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.25rem;
            font-size: 1.1rem;
            font-weight: 700;
        }
        .panel-title .badge {
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-baseline { background: rgba(244, 63, 94, 0.15); color: #fb7185; }
        .badge-jev { background: rgba(16, 185, 129, 0.15); color: #34d399; }

        .bar-container { margin-bottom: 1rem; }
        .bar-label { display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-bottom: 0.25rem; }
        .bar-track { height: 10px; background: #0f172a; border-radius: 5px; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 5px; transition: width 0.8s ease; }

        /* Interactive Playground */
        .interactive-section {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .interactive-form { display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap; }
        input[type="text"], select {
            background: #090d16;
            border: 1px solid var(--surface-border);
            color: white;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.9rem;
        }
        input[type="text"]:focus, select:focus { outline: none; border-color: var(--primary); }
        .prompt-input { flex: 1; min-width: 280px; }

        pre {
            background: #050811;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            max-height: 250px;
            overflow: auto;
        }
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="dot"></div>
            <h1 id="app-title">JEV Comparative Benchmark Portal</h1>
        </div>
        <div class="status-pill">
            <span>Primary: <strong>Sarvam AI (105B)</strong></span>
            <span>|</span>
            <span>Fallback: <strong>OpenAI (GPT-4o)</strong></span>
            <span>|</span>
            <span id="current-role" class="speedup-badge" style="background:#1e293b; color:#38bdf8;">Role: Benchmark Admin (L3)</span>
        </div>
    </header>

    <div class="banner">
        <div class="banner-text">
            <h2>⚡ Automated Comparative Benchmark Engine</h2>
            <p id="benchmark-status">Loading live comparison metrics between <strong>Without JEV</strong> (baseline) and <strong>With JEV</strong> (accelerated)...</p>
        </div>
        <div style="display:flex; gap:0.5rem;">
            <button id="run-benchmark-btn" class="btn" onclick="executeFullBenchmark()">Run Full Benchmark</button>
            <button class="btn btn-secondary" onclick="loadAutoBenchmark()">Refresh</button>
        </div>
    </div>

    <!-- 4 Key Metric Comparison Cards -->
    <div class="metric-grid">
        <div class="card" id="ttft-card">
            <div class="card-header">Time to First Token (TTFT)</div>
            <div class="side-by-side">
                <div class="val-box">
                    <div class="val-label">Without JEV</div>
                    <div id="ttft-without" class="val-num non-jev">-- ms</div>
                </div>
                <div class="val-box">
                    <div class="val-label">With JEV</div>
                    <div id="ttft-with" class="val-num jev">-- ms</div>
                </div>
            </div>
            <div id="ttft-speedup" class="speedup-badge">🚀 Calculating...</div>
        </div>

        <div class="card" id="e2e-card">
            <div class="card-header">End-to-End Latency (p50)</div>
            <div class="side-by-side">
                <div class="val-box">
                    <div class="val-label">Without JEV</div>
                    <div id="e2e-without" class="val-num non-jev">-- ms</div>
                </div>
                <div class="val-box">
                    <div class="val-label">With JEV</div>
                    <div id="e2e-with" class="val-num jev">-- ms</div>
                </div>
            </div>
            <div id="e2e-speedup" class="speedup-badge">⚡ Calculating...</div>
        </div>

        <div class="card" id="throughput-card">
            <div class="card-header">Token Generation Throughput</div>
            <div class="side-by-side">
                <div class="val-box">
                    <div class="val-label">Without JEV</div>
                    <div id="tp-without" class="val-num non-jev">-- t/s</div>
                </div>
                <div class="val-box">
                    <div class="val-label">With JEV</div>
                    <div id="tp-with" class="val-num jev">-- t/s</div>
                </div>
            </div>
            <div id="tp-speedup" class="speedup-badge">🔥 Calculating...</div>
        </div>

        <div class="card" id="rps-card">
            <div class="card-header">Requests Per Second (RPS)</div>
            <div class="side-by-side">
                <div class="val-box">
                    <div class="val-label">Without JEV</div>
                    <div id="rps-without" class="val-num non-jev">--</div>
                </div>
                <div class="val-box">
                    <div class="val-label">With JEV</div>
                    <div id="rps-with" class="val-num jev">--</div>
                </div>
            </div>
            <div id="cache-hit-pill" class="speedup-badge">🎯 Cache Hit: --%</div>
        </div>
    </div>

    <!-- Visual Scenario Comparison Side-by-Side -->
    <div class="visual-comparison">
        <div class="scenario-panel">
            <div class="panel-title">
                <span>Scenario A: Without JEV (Baseline)</span>
                <span class="badge badge-baseline">Baseline</span>
            </div>
            <p style="color:#94a3b8; font-size:0.85rem; margin-bottom: 1rem;">Direct pipeline to Sarvam AI 105B. Full prompt recomputation, cold TTFT, standard upstream latency.</p>
            <div class="bar-container">
                <div class="bar-label"><span>TTFT Latency</span><span id="bar-val-ttft-without">250 ms</span></div>
                <div class="bar-track"><div id="bar-fill-ttft-without" class="bar-fill" style="width: 85%; background: var(--accent-nonjev);"></div></div>
            </div>
            <div class="bar-container">
                <div class="bar-label"><span>E2E Request Latency</span><span id="bar-val-e2e-without">490 ms</span></div>
                <div class="bar-track"><div id="bar-fill-e2e-without" class="bar-fill" style="width: 90%; background: var(--accent-nonjev);"></div></div>
            </div>
        </div>

        <div class="scenario-panel">
            <div class="panel-title">
                <span>Scenario B: With JEV (Accelerated)</span>
                <span class="badge badge-jev">Accelerated</span>
            </div>
            <p style="color:#94a3b8; font-size:0.85rem; margin-bottom: 1rem;">JEV Layer active: KV-cache reuse, prefix-tree prompt matching, and persistent connection multiplexing.</p>
            <div class="bar-container">
                <div class="bar-label"><span>TTFT Latency</span><span id="bar-val-ttft-with">35 ms</span></div>
                <div class="bar-track"><div id="bar-fill-ttft-with" class="bar-fill" style="width: 15%; background: var(--accent-jev);"></div></div>
            </div>
            <div class="bar-container">
                <div class="bar-label"><span>E2E Request Latency</span><span id="bar-val-e2e-with">95 ms</span></div>
                <div class="bar-track"><div id="bar-fill-e2e-with" class="bar-fill" style="width: 20%; background: var(--accent-jev);"></div></div>
            </div>
        </div>
    </div>

    <!-- Live Interactive Test Runner -->
    <div class="interactive-section">
        <h3 style="font-size:1.1rem; font-weight:700;">🧪 Live Interactive Query Tester</h3>
        <p style="color:#94a3b8; font-size:0.85rem;">Send a query through the resilient gateway and observe JEV optimization headers and token telemetry.</p>
        
        <div class="interactive-form">
            <input type="text" id="prompt-input" class="prompt-input" placeholder="Type prompt here..." value="Explain quantum superposition and its importance in quantum algorithms.">
            <select id="jev-select">
                <option value="true">With JEV Acceleration</option>
                <option value="false">Without JEV (Baseline)</option>
            </select>
            <button id="send-query-btn" class="btn" onclick="sendTestQuery()">Execute Query</button>
        </div>

        <pre id="query-result">Query telemetry and output will appear here...</pre>
    </div>

    <!-- Auth Credentials Panel (For testing RBAC roles) -->
    <div class="interactive-section" style="background:#0c1220;">
        <h3 style="font-size:1rem; font-weight:700; color:#cbd5e1;">🔐 Hierarchical RBAC Session Controls</h3>
        <div style="display:flex; gap:0.75rem; align-items:center; margin-top:0.75rem; flex-wrap:wrap;">
            <input type="text" id="username-input" value="benchmark@example.com" placeholder="Email / Username" style="width:220px;">
            <input type="password" id="password-input" value="BenchPass123!" placeholder="Password" style="width:180px;">
            <button id="login-btn" class="btn btn-secondary" onclick="manualLogin()">Switch Role</button>
            <span style="font-size:0.8rem; color:#64748b;">(Pre-loaded with Level 3 Benchmark Admin session)</span>
        </div>
    </div>

    <script>
        let authToken = "";

        // Auto-login as Benchmark Admin on startup so all interactive features are ready immediately
        async function ensureAuth() {
            try {
                const body = new URLSearchParams({ username: "benchmark@example.com", password: "BenchPass123!" });
                const res = await fetch("/api/v1/auth/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
                if (res.ok) {
                    const data = await res.json();
                    authToken = data.access_token;
                    document.getElementById("current-role").innerText = "Role: " + data.role + " (L" + data.role_level + ")";
                }
            } catch (err) {
                console.warn("Auth initialization skipped:", err);
            }
        }

        // Automatically load and display comparative benchmark on application start
        async function loadAutoBenchmark() {
            document.getElementById("benchmark-status").innerHTML = '<span class="spinner"></span> Running automated comparative benchmark (With vs Without JEV)...';
            try {
                const res = await fetch("/api/v1/benchmark/auto-run");
                const data = await res.json();
                
                if (data.status === "success") {
                    const w = data.with_jev;
                    const wo = data.without_jev;

                    // Update Metrics
                    document.getElementById("ttft-without").innerText = wo.ttft_ms.p50.toFixed(1) + " ms";
                    document.getElementById("ttft-with").innerText = w.ttft_ms.p50.toFixed(1) + " ms";
                    document.getElementById("ttft-speedup").innerText = "🚀 " + data.speedup_summary.ttft_speedup_x + " Faster TTFT";

                    document.getElementById("e2e-without").innerText = wo.e2e_latency_ms.p50.toFixed(1) + " ms";
                    document.getElementById("e2e-with").innerText = w.e2e_latency_ms.p50.toFixed(1) + " ms";
                    document.getElementById("e2e-speedup").innerText = "⚡ " + data.speedup_summary.e2e_speedup_x + " Faster E2E";

                    document.getElementById("tp-without").innerText = wo.token_throughput_per_sec.toFixed(1) + " t/s";
                    document.getElementById("tp-with").innerText = w.token_throughput_per_sec.toFixed(1) + " t/s";
                    document.getElementById("tp-speedup").innerText = "🔥 " + data.speedup_summary.throughput_gain_x + " Throughput Gain";

                    document.getElementById("rps-without").innerText = wo.requests_per_second.toFixed(1) + " RPS";
                    document.getElementById("rps-with").innerText = w.requests_per_second.toFixed(1) + " RPS";
                    document.getElementById("cache-hit-pill").innerText = "🎯 JEV Cache Hit: " + w.cache_hit_rate_pct.toFixed(0) + "%";

                    // Update Visual Bars
                    document.getElementById("bar-val-ttft-without").innerText = wo.ttft_ms.p50.toFixed(0) + " ms";
                    document.getElementById("bar-val-ttft-with").innerText = w.ttft_ms.p50.toFixed(0) + " ms";
                    document.getElementById("bar-val-e2e-without").innerText = wo.e2e_latency_ms.p50.toFixed(0) + " ms";
                    document.getElementById("bar-val-e2e-with").innerText = w.e2e_latency_ms.p50.toFixed(0) + " ms";

                    const maxE2E = Math.max(wo.e2e_latency_ms.p50, w.e2e_latency_ms.p50, 1);
                    document.getElementById("bar-fill-e2e-without").style.width = Math.min(100, Math.round((wo.e2e_latency_ms.p50 / maxE2E) * 100)) + "%";
                    document.getElementById("bar-fill-e2e-with").style.width = Math.max(8, Math.round((w.e2e_latency_ms.p50 / maxE2E) * 100)) + "%";

                    document.getElementById("benchmark-status").innerHTML = "✅ Live comparative benchmark loaded successfully! Primary: <strong>" + data.primary_model + "</strong> | JEV Acceleration: <strong>Active</strong>.";
                }
            } catch (err) {
                document.getElementById("benchmark-status").innerText = "Failed to auto-load benchmark: " + err;
            }
        }

        async function executeFullBenchmark() {
            if (!authToken) await ensureAuth();
            document.getElementById("benchmark-status").innerHTML = '<span class="spinner"></span> Running multi-concurrency stress benchmark...';
            try {
                const res = await fetch("/api/v1/benchmark/run", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
                    body: JSON.stringify({ concurrency_levels: [1, 5], iterations_per_level: 4 })
                });
                const data = await res.json();
                document.getElementById("benchmark-status").innerHTML = "✅ Multi-concurrency benchmark completed across tiers (c=1, c=5)!";
                await loadAutoBenchmark();
            } catch (err) {
                document.getElementById("benchmark-status").innerText = "Error: " + err;
            }
        }

        async function sendTestQuery() {
            if (!authToken) await ensureAuth();
            const prompt = document.getElementById("prompt-input").value;
            const with_jev = document.getElementById("jev-select").value === "true";
            document.getElementById("query-result").innerText = "Executing query (with_jev=" + with_jev + ")...";

            try {
                const res = await fetch("/api/v1/inference", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
                    body: JSON.stringify({ prompt, with_jev })
                });
                const data = await res.json();
                document.getElementById("query-result").innerText = JSON.stringify(data, null, 2);
            } catch (err) {
                document.getElementById("query-result").innerText = "Error executing query: " + err;
            }
        }

        async function manualLogin() {
            const u = document.getElementById("username-input").value;
            const p = document.getElementById("password-input").value;
            const body = new URLSearchParams({ username: u, password: p });
            const res = await fetch("/api/v1/auth/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
            if (res.ok) {
                const data = await res.json();
                authToken = data.access_token;
                document.getElementById("current-role").innerText = "Role: " + data.role + " (L" + data.role_level + ")";
                alert("Logged in as " + data.role);
            } else {
                alert("Login failed!");
            }
        }

        // Automatic bootstrap on window load
        window.addEventListener("DOMContentLoaded", async () => {
            await ensureAuth();
            await loadAutoBenchmark();
        });
    </script>
</body>
</html>
"""
