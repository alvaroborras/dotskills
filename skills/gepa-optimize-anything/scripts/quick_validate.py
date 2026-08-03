#!/usr/bin/env python3
"""Fast, no-network validation for the installed GEPA agent sandbox overlay."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"


def run(command: list[str]) -> int:
    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    checks = [
        [str(PYTHON), "scripts/reapply_backend_sandbox.py"],
        [str(PYTHON), "-m", "unittest", "discover", "-s", "tests", "-p", "test_backend_sandbox.py"],
        [str(PYTHON), "scripts/preflight.py", "--engine", "autoresearch"],
    ]
    for command in checks:
        if run(command):
            return 1
    print("quick validation passed (no optimizer or backend model call was made)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
