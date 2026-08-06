#!/usr/bin/env python3
"""Load the skill GEPA package and Codex/OpenCode overlay in a host Python.

Use this when an evaluator must run in an application's interpreter (for
example, one that already owns a CUDA-enabled Torch build) instead of the
skill's virtualenv. The skill site-packages directory is appended, never
prepended, so host numerical packages retain priority.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _skill_site_packages() -> Path:
    candidates = sorted((SKILL_ROOT / ".venv" / "lib").glob("python*/site-packages"))
    if len(candidates) != 1:
        raise RuntimeError(
            "GEPA host bootstrap could not identify the skill runtime\n"
            f"  skill_root: {SKILL_ROOT}\n"
            f"  host_python: {sys.executable}\n"
            f"  site_packages_candidates: {candidates or '(none)'}\n"
            "  fix: recreate the skill .venv with Python 3.12 and install gepa[full]"
        )
    return candidates[0]


def _load_overlay() -> ModuleType:
    name = "gepa_skill_backend_sandbox_overlay_host"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = SKILL_ROOT / "scripts" / "backend_sandbox_overlay.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            "GEPA host bootstrap could not load the backend overlay\n"
            f"  overlay: {path}\n"
            f"  exists: {path.is_file()}\n"
            f"  host_python: {sys.executable}\n"
            "  fix: restore scripts/backend_sandbox_overlay.py or reinstall the skill"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bootstrap() -> Path:
    """Install the overlay in this interpreter and return skill site-packages."""
    os.environ.setdefault("GEPA_SKILL_ROOT", str(SKILL_ROOT))
    site_packages = _skill_site_packages()
    site_text = str(site_packages)
    if site_text not in sys.path:
        sys.path.append(site_text)
    try:
        overlay = _load_overlay()
        overlay.install()
    except Exception as exc:
        raise RuntimeError(
            "GEPA host bootstrap failed while installing the Codex/OpenCode overlay\n"
            f"  skill_root: {SKILL_ROOT}\n"
            f"  host_python: {sys.executable}\n"
            f"  skill_site_packages: {site_packages}\n"
            f"  GEPA_AGENT_BACKEND: {os.environ.get('GEPA_AGENT_BACKEND', 'codex')}\n"
            f"  cause: {type(exc).__name__}: {exc}\n"
            "  fix: run scripts/reapply_backend_sandbox.py --apply, then scripts/quick_validate.py"
        ) from exc
    return site_packages


def main() -> int:
    bootstrap()
    from gepa.oa import sandbox
    from gepa.oa.engines import autoresearch, meta_harness

    expected = "GEPA_SKILL_BACKEND_OVERLAY_V4"
    assert sandbox.GEPA_SKILL_BACKEND_OVERLAY == expected
    assert autoresearch.bwrap_prefix is sandbox.bwrap_prefix
    assert meta_harness.bwrap_prefix is sandbox.bwrap_prefix
    print(f"host runtime bootstrapped: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
