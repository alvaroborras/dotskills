#!/usr/bin/env python3
"""Prepare the exact per-backend state directories used by the GEPA jail."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


BACKENDS = ("codex", "opencode")


def selected_backend(value: str | None = None) -> str:
    backend = (value or os.environ.get("GEPA_AGENT_BACKEND") or "codex").lower()
    if backend not in BACKENDS:
        raise ValueError(f"unsupported GEPA_AGENT_BACKEND={backend!r}; expected one of {BACKENDS}")
    return backend


def state_paths(backend: str, home: Path) -> tuple[list[Path], list[Path]]:
    """Return writable and read-only host paths for exactly one supported CLI."""
    backend = selected_backend(backend)
    if backend == "codex":
        return [home / ".codex"], []
    return (
        [
            home / ".config" / "opencode",
            home / ".local" / "share" / "opencode",
            home / ".cache" / "opencode",
        ],
        [home / ".opencode"],
    )


def prepare(backend: str, home: Path | None = None) -> dict[str, list[str]]:
    """Idempotently create writable state and report missing required read-only state."""
    home = (home or Path.home()).resolve()
    writable, read_only = state_paths(backend, home)
    created: list[str] = []
    verified: list[str] = []
    missing: list[str] = []
    for path in writable:
        if not path.exists():
            path.mkdir(parents=True, mode=0o700)
            created.append(str(path))
        elif path.is_dir():
            verified.append(str(path))
        else:
            missing.append(f"not_a_directory:{path}")
    for path in read_only:
        if path.exists():
            verified.append(str(path))
        else:
            missing.append(str(path))
    return {"created": created, "verified": verified, "missing": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=BACKENDS)
    parser.add_argument("--check", action="store_true", help="report state without creating it")
    args = parser.parse_args()
    backend = selected_backend(args.backend)
    if args.check:
        writable, read_only = state_paths(backend, Path.home())
        report = {
            "created": [],
            "verified": [str(path) for path in [*writable, *read_only] if path.exists()],
            "missing": [str(path) for path in [*writable, *read_only] if not path.exists()],
        }
    else:
        report = prepare(backend)
    print(f"backend={backend}")
    for key in ("created", "verified", "missing"):
        for path in report[key]:
            print(f"{key}: {path}")
    return 1 if report["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
