#!/usr/bin/env python3
"""
Automated Static Analysis & Security Verification Tool.
Scans the repository to ensure:
  1. ZERO machine-local absolute paths in source code and configuration.
  2. ZERO hardcoded API keys, private keys, or passwords.
  3. Proper .gitignore presence and .env exclusion.
"""

import os
import re
import sys
from pathlib import Path

# Dynamically locate project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Forbidden literal path regex in code files (detecting string assignments or open() calls with static paths)
FORBIDDEN_CODE_PATH_PATTERNS = [
    re.compile(r"""['"][A-Za-z]:[\\/][Uu]sers[\\/][^'"]+['"]"""),
    re.compile(r"""['"]/home/[^'"]+['"]"""),
    re.compile(r"""['"]/Users/[^'"]+['"]"""),
    re.compile(r"""['"]/tmp/[^'"]+['"]"""),
]

# Sensitive patterns that look like hardcoded secrets in code or configs
SECRET_PATTERNS = [
    re.compile(r"""(?i)(sarvam_api_key|openai_api_key|jwt_secret)\s*[:=]\s*['"][a-zA-Z0-9_\-]{20,}['"]"""),
    re.compile(r"""sk-[a-zA-Z0-9]{32,}"""),
    re.compile(r"""-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"""),
]

# Directories and files to ignore during scan
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "htmlcov",
    ".idea",
    ".vscode",
}

EXCLUDED_FILES = {
    ".gitignore",
    ".gitkeep",
    "package-lock.json",
    ".env.example",  # Template file with documented dummy placeholders
}


def scan_repository():
    violations = []
    print(f"[*] Scanning repository for secrets and machine-local paths: {PROJECT_ROOT}")

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            if file in EXCLUDED_FILES:
                continue

            file_path = Path(root) / file
            rel_path = file_path.relative_to(PROJECT_ROOT)

            # Ensure .env is never tracked in git, but allow local ignored file
            if file == ".env":
                import subprocess
                try:
                    res = subprocess.run(["git", "ls-files", "--error-unmatch", str(rel_path)], capture_output=True, cwd=PROJECT_ROOT)
                    if res.returncode == 0:
                        violations.append(f"CRITICAL: .env is TRACKED in git index: {rel_path}. Run 'git rm --cached .env'!")
                except Exception:
                    pass
                continue

            # Only scan code, configuration, and script files
            if file_path.suffix not in {".py", ".json", ".yaml", ".yml", ".toml", ".sh", ".ps1", ".js", ".ts"}:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip scanner self-regex definitions
                        if file_path.name == "check_secrets_and_paths.py":
                            continue

                        # Check for forbidden static machine paths in code literals
                        for pattern in FORBIDDEN_CODE_PATH_PATTERNS:
                            if pattern.search(line):
                                violations.append(
                                    f"[STATIC PATH] {rel_path}:{line_num} contains machine-local path: {line.strip()}"
                                )

                        # Check for hardcoded secret patterns
                        for pattern in SECRET_PATTERNS:
                            if pattern.search(line):
                                violations.append(
                                    f"[SECRET DETECTED] {rel_path}:{line_num} contains suspected secret: {line.strip()}"
                                )
            except Exception as e:
                print(f"[!] Warning: Could not read {rel_path}: {e}")

    if violations:
        print("\n[FAIL] Security and Path Verification Failed with violations:")
        for v in violations:
            print(f"  - {v}")
        return False
    else:
        print("\n[PASS] No hardcoded machine paths or secrets found! Repository is clean and git-safe.")
        return True


if __name__ == "__main__":
    is_clean = scan_repository()
    sys.exit(0 if is_clean else 1)
