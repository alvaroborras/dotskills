#!/usr/bin/env python3
"""Load GEPA and the Codex bridge into an application's Python runtime."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _skill_site_packages() -> Path:
    candidates = sorted((SKILL_ROOT / ".venv" / "lib").glob("python*/site-packages"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"could not identify the skill site-packages directory: {candidates or '(none)'}"
        )
    return candidates[0]


def bootstrap() -> Path:
    os.environ.setdefault("GEPA_SKILL_ROOT", str(SKILL_ROOT))
    site_packages = _skill_site_packages()
    if str(site_packages) not in sys.path:
        sys.path.append(str(site_packages))
    scripts = str(SKILL_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    runtime = importlib.import_module("codex_runtime")
    runtime.install()
    return site_packages


def main() -> int:
    site_packages = bootstrap()
    import gepa.oa.sandbox as runtime_module

    assert runtime_module.GEPA_SKILL_CODEX_RUNTIME == "GEPA_SKILL_CODEX_RUNTIME_V1"
    print(f"host runtime bootstrapped with {site_packages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
