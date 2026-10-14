from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FORBIDDEN_CODE_PATH_PATTERNS = [
    re.compile(r"""['"][A-Za-z]:[\\/][Uu]sers[\\/][^'"]+['"]"""),
    re.compile(r"""['"]/home/[^'"]+['"]"""),
    re.compile(r"""['"]/Users/[^'"]+['"]"""),
    re.compile(r"""['"]/tmp/[^'"]+['"]"""),
]

EXCLUDED_FILES = {
    "check_secrets_and_paths.py",
    "test_path_safety.py",
}


def test_no_static_machine_paths_in_source_code():
    """
    Ensure no developer hardcoded machine-specific absolute path strings
    (such as Windows user drives or Unix home mounts) in any source code file.
    """
    violations = []
    src_dir = PROJECT_ROOT / "src"

    for py_file in src_dir.rglob("*.py"):
        if py_file.name in EXCLUDED_FILES:
            continue
        content = py_file.read_text(encoding="utf-8")
        for line_idx, line in enumerate(content.splitlines(), 1):
            for pattern in FORBIDDEN_CODE_PATH_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{py_file.name}:{line_idx} - {line.strip()}")

    assert not violations, f"Static machine paths found in source code: {violations}"
