# Antigravity Workspace Rule: Project Standards & Security

## Mission
You are contributing to the JEV vs Non-JEV LLM Benchmarking repository with Sarvam AI 105B as primary and OpenAI as fallback.

## Non-Negotiable Constraints
1. **NO SECRETS IN CODE OR COMMITS:**
   - Never embed API keys, tokens, or credentials in any file.
   - Use environment variables via `src/config.py`.
   - Never remove `.env` from `.gitignore`.
2. **NO MACHINE-SPECIFIC ABSOLUTE PATHS:**
   - Never write `C:\Users\...` or `/home/...` in code or tests.
   - Always derive paths relative to `Path(__file__).resolve()` or read from `config.settings.DATA_DIR`.
3. **PRIMARY & FALLBACK RESILIENCE:**
   - Primary LLM must always be Sarvam AI.
   - Fallback LLM must always be OpenAI.
   - Any failure (HTTP 429, 500, 503, timeout) on Sarvam must gracefully switch to OpenAI fallback and emit audit logs.
4. **ROLE-BASED ACCESS CONTROL (RBAC):**
   - Enforce hierarchy: Super Admin (L4) > Benchmark Admin (L3) > Analyst (L2) > Standard User / Service Account (L1).
   - Protect benchmark execution and configuration endpoints with role checks.
5. **TEST COVERAGE & AUTOMATION:**
   - Unit tests (`pytest`) must mock all LLM providers (zero real API calls in tests).
   - Selenium browser tests must validate the dashboard and RBAC UI protections.
   - Run `scripts/check_secrets_and_paths.py` before committing.
6. **CONTINUOUS DOCUMENTATION:**
   - Any architectural or schema change must update `README.md`, `docs/ARCHITECTURE.md`, `docs/BENCHMARK_DESIGN.md`, and `docs/RBAC_MATRIX.md`.
