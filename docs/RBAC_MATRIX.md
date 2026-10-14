# Role-Based Access Control (RBAC) Matrix

This document defines the user hierarchy, permission boundaries, and access rules implemented across API routes and the UI dashboard.

---

## 1. Role Hierarchy

```
Level 4: Super Admin
   └── Level 3: Benchmark Admin
          └── Level 2: Analyst / Auditor
                 └── Level 1: Standard User / Service Account
```

---

## 2. Permissions Matrix

| Resource / Action | Standard User (L1) | Service Account (L1) | Analyst (L2) | Benchmark Admin (L3) | Super Admin (L4) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Execute Interactive Query (Sarvam/OpenAI)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **View Personal Query History** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **View Benchmark Dashboards & Reports** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Export Benchmark Datasets (CSV/JSON)** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Trigger Benchmark Suite Execution** | ❌ | ✅ (CLI/CI) | ❌ | ✅ | ✅ |
| **Configure Benchmark Profiles & Datasets** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Toggle JEV Flags / Cache Flushing** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **User & Role Management** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Manage LLM API Credentials & Keys** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **View System Audit Logs** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Enforcement Implementation

* Authentication is stateless using signed **JSON Web Tokens (JWT)** containing:
  ```json
  {
    "sub": "user_id_123",
    "role": "benchmark_admin",
    "level": 3,
    "exp": 1700000000
  }
  ```
* FastAPI route handlers declare permissions using reusable security dependencies:
  ```python
  @router.post("/benchmark/run")
  async def run_benchmark(
      current_user: User = Depends(require_role_level(RoleLevel.BENCHMARK_ADMIN))
  ):
      ...
  ```
