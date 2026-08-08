#!/usr/bin/env python3
"""Fail-fast checks for a Codex-backed optimize_anything run."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MARKER = "GEPA_SKILL_CODEX_RUNTIME_V1"
RUNTIME_HANDOFF = "_GEPA_CODEX_PREFLIGHT_RUNTIME"
DEFAULT_LM_BY_ENGINE = {"gepa": "openai/gpt-5.1", "best_of_n": "openai/gpt-5.1"}
OK, BAD = "\033[32mOK\033[0m", "\033[31mFAIL\033[0m"
problems: list[str] = []


def check(label: str, ok: bool, fix: str = "") -> None:
    print(f"  [{OK if ok else BAD}] {label}")
    if not ok:
        problems.append(f"{label} — {fix}" if fix else label)


def _skill_python() -> Path:
    return SKILL_ROOT / ".venv" / "bin" / "python"


def _handoff_to_skill_runtime() -> None:
    expected = _skill_python().absolute()
    active = Path(sys.executable).absolute()
    marker = os.environ.get(RUNTIME_HANDOFF)
    if active == expected:
        return
    if marker:
        raise RuntimeError(
            f"runtime handoff did not enter {expected}; active interpreter is {active}"
        )
    if not expected.is_file():
        return
    environment = os.environ.copy()
    environment[RUNTIME_HANDOFF] = str(expected)
    os.execve(
        str(expected),
        [str(expected), str(Path(__file__).resolve()), *sys.argv[1:]],
        environment,
    )


try:
    _handoff_to_skill_runtime()
except RuntimeError as exc:
    print(f"preflight runtime setup failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import codex_runtime


def _creds_for(model: str) -> tuple[bool, str]:
    has_aws = bool(
        os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        or os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
    )
    if "bedrock" in model:
        return has_aws, "export AWS credentials"
    if model.startswith(("openai/", "gpt-")) or "gpt-5" in model:
        return bool(os.environ.get("OPENAI_API_KEY")), "export OPENAI_API_KEY"
    return bool(
        os.environ.get("OPENAI_API_KEY") or has_aws
    ), "export the configured provider credentials"


def _report() -> int:
    print()
    if problems:
        print(f"\033[31m{len(problems)} blocker(s):\033[0m")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\033[32mAll preflight checks passed.\033[0m")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--engine",
        default="gepa",
        choices=["gepa", "best_of_n", "autoresearch", "meta_harness"],
    )
    parser.add_argument(
        "--test-lm", action="store_true", help="make one live reflection-LM call"
    )
    args = parser.parse_args()
    print("== optimize_anything Codex preflight ==")

    try:
        import gepa
        from gepa.optimize_anything import (  # noqa: F401
            OptimizeAnythingConfig,
            optimize_anything,
        )

        codex_runtime.install()

        check(
            f"import gepa ({getattr(gepa, '__version__', '?')}) + optimize_anything",
            True,
        )
        default_config = OptimizeAnythingConfig()
        check(
            "GEPA default sandbox flag is disabled",
            getattr(default_config, "sandbox", None) is False,
            "install the pinned pre-confinement GEPA revision",
        )
        from gepa.strategies.proposal_sampling import PxNSampling
        from gepa.strategies.proposal_selection import AllImprovements

        engine_options = default_config.engine_config.get("engine", {})
        sampling = engine_options.get("sampling_strategy")
        selection = engine_options.get("selection_strategy")
        check("PxNSampling is available", isinstance(sampling, PxNSampling))
        check("AllImprovements is available", isinstance(selection, AllImprovements))
        check(
            "default proposal width is PxNSampling(p=2, n=2)",
            isinstance(sampling, PxNSampling)
            and sampling.p == codex_runtime.DEFAULT_PARENT_COUNT
            and sampling.n == codex_runtime.DEFAULT_MUTATION_COUNT,
            "use the pinned GEPA revision and reapply the Codex runtime",
        )
    except Exception as exc:  # noqa: BLE001 - preflight must report import failures
        check(
            "import gepa + optimize_anything",
            False,
            "install the pinned 'gepa[full]' dependency",
        )
        print(f"      {exc}")
        return _report()

    try:
        import gepa.oa.sandbox as runtime_module

        check(
            "Codex runtime bridge installed",
            runtime_module.GEPA_SKILL_CODEX_RUNTIME == RUNTIME_MARKER,
        )
    except Exception as exc:  # noqa: BLE001 - preflight must report bridge failures
        check("Codex runtime bridge installed", False, str(exc))

    if args.engine in ("gepa", "best_of_n"):
        model = (
            os.environ.get("GEPA_REFLECTION_LM") or DEFAULT_LM_BY_ENGINE[args.engine]
        )
        ok, fix = _creds_for(model)
        check(f"LLM credentials present for '{model}'", ok, fix)

    if args.engine in ("autoresearch", "meta_harness"):
        try:
            executable = codex_runtime.codex_path()
            check(f"Codex executable available ({executable})", True)
        except RuntimeError as exc:
            check("Codex executable available", False, str(exc))
        check(
            "bundled Codex entrypoint exists",
            codex_runtime.shim_path().is_file(),
            str(codex_runtime.shim_path()),
        )
        if args.engine == "autoresearch":
            check(
                "jq is available for eval.sh",
                shutil.which("jq") is not None,
                "install jq",
            )

    if args.test_lm and args.engine in ("gepa", "best_of_n"):
        target = (
            os.environ.get("GEPA_REFLECTION_LM") or DEFAULT_LM_BY_ENGINE[args.engine]
        )
        try:
            from gepa.lm import LM

            check(
                f"reflection LM round-trip ({target})",
                bool(LM(target)("Reply with the single word: ok")),
            )
        except Exception as exc:  # noqa: BLE001 - live provider errors are diagnostics
            check(f"reflection LM round-trip ({target})", False, str(exc)[:160])
    return _report()


if __name__ == "__main__":
    raise SystemExit(main())
