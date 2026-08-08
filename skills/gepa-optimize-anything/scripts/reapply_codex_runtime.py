#!/usr/bin/env python3
"""Install the skill-owned Codex runtime loader into the GEPA environment."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "codex_runtime.py"
MODULE_NAME = "gepa_skill_codex_runtime.py"
LOADER_NAME = "gepa_skill_codex_runtime.pth"


def active_python() -> Path:
    configured = os.environ.get("GEPA_SKILL_PYTHON")
    return (
        Path(configured).expanduser()
        if configured
        else ROOT / ".venv" / "bin" / "python"
    )


def purelib(python: Path) -> Path:
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        check=True,
        capture_output=True,
        text=True,
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
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, mode="w", encoding="utf-8", delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def install(site_packages: Path) -> tuple[Path, Path]:
    module = site_packages / MODULE_NAME
    loader = site_packages / LOADER_NAME
    atomic_copy(SOURCE, module)
    atomic_text(
        loader,
        f"import os; os.environ.setdefault('GEPA_SKILL_ROOT', {str(ROOT)!r}); "
        f"import {module.stem}; {module.stem}.install()\n",
    )
    return module, loader


def verify(python: Path) -> None:
    code = "import gepa.oa.sandbox as s; assert s.GEPA_SKILL_CODEX_RUNTIME == 'GEPA_SKILL_CODEX_RUNTIME_V1'"
    subprocess.run(
        [str(python), "-c", code],
        check=True,
        env={**os.environ, "GEPA_SKILL_ROOT": str(ROOT)},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="install or refresh the runtime loader"
    )
    args = parser.parse_args()
    python = active_python()
    if not python.is_file():
        print(f"missing skill interpreter: {python}")
        return 1
    try:
        site_packages = purelib(python)
        module = site_packages / MODULE_NAME
        loader = site_packages / LOADER_NAME
        if args.apply:
            install(site_packages)
            print(f"installed Codex runtime: {module}")
            print(f"installed loader: {loader}")
        elif not module.is_file() or not loader.is_file():
            print(f"runtime loader missing: run {Path(__file__).name} --apply")
            return 1
        verify(python)
        print(f"verified Codex runtime with {python}")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Codex runtime setup failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
