#!/usr/bin/env python3
"""Install and verify the non-invasive GEPA sandbox overlay after a venv refresh.

Unlike the retired patcher, this never edits ``gepa/oa/sandbox.py``.  uv can
hardlink that file to its package cache, so source rewriting risks modifying a
shared cache.  The installer uses a .pth-loaded, skill-owned monkeypatch.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLAY_SOURCE = ROOT / "scripts" / "backend_sandbox_overlay.py"
OVERLAY_NAME = "gepa_skill_backend_sandbox_overlay.py"
PTH_NAME = "gepa_skill_backend_sandbox_overlay.pth"


def active_python() -> Path:
    configured = os.environ.get("GEPA_SKILL_PYTHON")
    # Keep the venv launcher path intact: resolving its symlink before startup
    # causes Python to select the base interpreter's site-packages.
    return Path(configured).expanduser() if configured else ROOT / ".venv" / "bin" / "python"


def purelib(python: Path) -> Path:
    result = subprocess.run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        check=True, capture_output=True, text=True,
    )
    return Path(result.stdout.strip()).resolve()


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_text(destination: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(dir=destination.parent, mode="w", encoding="utf-8", delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def install(site_packages: Path) -> tuple[Path, Path, Path]:
    upstream = site_packages / "gepa" / "oa" / "sandbox.py"
    if not upstream.is_file():
        raise RuntimeError(f"GEPA sandbox module not found: {upstream}")
    # If a former installation directly patched a hardlink, sever only the
    # venv entry before doing anything else.  The cache is never opened for write.
    if upstream.stat().st_nlink > 1:
        atomic_copy(upstream, upstream)
    overlay = site_packages / OVERLAY_NAME
    pth = site_packages / PTH_NAME
    atomic_copy(OVERLAY_SOURCE, overlay)
    atomic_text(pth, f"import {overlay.stem}; {overlay.stem}.install()\n")
    return upstream, overlay, pth


def verify(python: Path, site_packages: Path) -> None:
    code = """
import gepa.oa.sandbox as sandbox
import gepa.oa.engines.autoresearch as autoresearch
import gepa.oa.engines.meta_harness as meta_harness
assert sandbox.GEPA_SKILL_BACKEND_OVERLAY == 'GEPA_SKILL_BACKEND_OVERLAY_V2'
assert sandbox.bwrap_prefix.__module__ == 'gepa_skill_backend_sandbox_overlay'
assert autoresearch.bwrap_prefix is sandbox.bwrap_prefix
assert meta_harness.bwrap_prefix is sandbox.bwrap_prefix
assert autoresearch.bwrap_prefix.__module__ == 'gepa_skill_backend_sandbox_overlay'
assert meta_harness.bwrap_prefix.__module__ == 'gepa_skill_backend_sandbox_overlay'
try:
    sandbox._agent_backend('claude')
except RuntimeError:
    pass
else:
    raise AssertionError('unsupported backend was accepted')
print(sandbox.__file__)
"""
    env = {**os.environ, "GEPA_SKILL_ROOT": str(ROOT)}
    result = subprocess.run([str(python), "-c", code], env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    if not (site_packages / OVERLAY_NAME).is_file():
        raise RuntimeError("overlay file disappeared during verification")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="install/update the overlay")
    args = parser.parse_args()
    python = active_python()
    if not python.is_file():
        print(f"missing skill interpreter: {python}")
        return 1
    try:
        site_packages = purelib(python)
        expected = [site_packages / OVERLAY_NAME, site_packages / PTH_NAME]
        if not args.apply and not all(path.is_file() for path in expected):
            print(f"overlay missing: run {Path(__file__).name} --apply")
            return 1
        if args.apply:
            upstream, overlay, pth = install(site_packages)
            print(f"installed overlay: {overlay}")
            print(f"installed loader: {pth}")
            print(f"preserved upstream source: {upstream}")
        verify(python, site_packages)
        print(f"verified dynamic overlay with {python}")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"overlay verification failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
