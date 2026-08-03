#!/usr/bin/env python3
"""Pre-flight checks for an optimize_anything run (gepa package) — fail fast before a long job.

    python preflight.py                      # checks gepa + reflection-LM creds
    python preflight.py --engine autoresearch  # also checks Codex/OpenCode shim + jq
    GEPA_REFLECTION_LM=openai/gpt-5.1 python preflight.py --test-lm

Exit code 0 = all good; non-zero = at least one blocker.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_MARKER = "_GEPA_SKILL_PREFLIGHT_RUNTIME"
# Basename GEPA engines resolve on PATH (upstream hardcode); skill ships the shim here.
_AGENT_ENTRY = "claude"


def _skill_python() -> Path:
    """Return the venv launcher without resolving its shared base runtime."""
    scripts = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return SKILL_ROOT / ".venv" / scripts / executable


def _run_in_skill_runtime() -> None:
    """Re-exec under the venv that owns the GEPA sandbox overlay.

    This script is often launched by an application's Python (for example,
    ``python /path/to/skill/scripts/preflight.py``).  That interpreter can
    import a different GEPA installation, which has neither this skill's
    ``.pth`` overlay nor the patched-by-value agentic engine aliases.  The
    preflight must validate the same runtime an agentic skill invocation uses,
    rather than reporting a misleading failure for the caller's environment.
    """
    # Do not resolve either path: venv launchers are symlinks to shared uv
    # runtimes, and samefile()/resolve() would incorrectly treat a different
    # venv using that runtime as the skill venv.
    active = Path(sys.executable).absolute()
    expected = _skill_python().absolute()
    marker = os.environ.get(_RUNTIME_MARKER)
    if active == expected:
        if marker and marker != str(expected):
            raise RuntimeError("invalid preflight runtime handoff marker")
        return
    if marker:
        if marker != str(expected):
            raise RuntimeError("invalid preflight runtime handoff marker")
        raise RuntimeError(
            "preflight runtime handoff did not enter the skill interpreter "
            f"(active: {active}; expected: {expected})"
        )
    if not expected.is_file():
        raise RuntimeError(f"missing skill interpreter: {expected}")
    print(f"delegating preflight to skill runtime: {expected}", file=sys.stderr, flush=True)
    environment = os.environ.copy()
    environment[_RUNTIME_MARKER] = str(expected)
    os.execve(str(expected), [str(expected), str(Path(__file__).resolve()), *sys.argv[1:]], environment)


try:
    _run_in_skill_runtime()
except RuntimeError as exc:
    print(f"preflight runtime setup failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

from backend_state import prepare, selected_backend

OK, BAD = "\033[32mOK\033[0m", "\033[31mFAIL\033[0m"
problems: list[str] = []

# In-process engines: gepa reflection default; best_of_n should set model explicitly.
DEFAULT_LM_BY_ENGINE = {"gepa": "openai/gpt-5.1", "best_of_n": "openai/gpt-5.1"}


def check(label: str, ok: bool, fix: str = "") -> None:
    print(f"  [{OK if ok else BAD}] {label}")
    if not ok:
        problems.append(f"{label} — {fix}" if fix else label)


def _creds_for(lm: str) -> tuple[bool, str]:
    """Best-effort provider-credential check for a LiteLLM model id."""
    has_aws = bool(
        os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        or os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
    )
    if "bedrock" in lm:
        return has_aws, "export AWS creds (AWS_BEARER_TOKEN_BEDROCK / AWS_ACCESS_KEY_ID / AWS_PROFILE)"
    if lm.startswith("openai/") or lm.startswith("gpt-") or "gpt-5" in lm:
        return bool(os.environ.get("OPENAI_API_KEY")), "export OPENAI_API_KEY"
    if lm.startswith("anthropic/") or "claude" in lm:
        return bool(os.environ.get("ANTHROPIC_API_KEY")) or has_aws, "export ANTHROPIC_API_KEY (or AWS creds)"
    any_key = bool(
        os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or has_aws
    )
    return any_key, "export your LiteLLM provider's API key"


def _configured_cli(backend: str) -> str | None:
    variable = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
    candidate = os.environ.get(variable) or shutil.which(backend)
    return str(Path(candidate).expanduser()) if candidate else None


def _probe_shim_in_bwrap(backend: str) -> tuple[bool, str]:
    """Prove bwrap can resolve and execute the shim without invoking an LLM."""
    try:
        from gepa.oa.sandbox import bwrap_prefix

        result = subprocess.run(
            [*bwrap_prefix(Path.cwd(), backend=backend), _AGENT_ENTRY, "--unsupported-probe"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    # The shim exits 2 before selecting/running any backend for unsupported
    # arguments. That exact failure proves both PATH resolution and shebang
    # interpreter availability without consuming model tokens.
    reached_shim = result.returncode == 2 and "only supports --print mode" in result.stderr
    return reached_shim, (result.stderr or result.stdout).strip()[-300:]


def _verify_agentic_caller_aliases() -> tuple[bool, str]:
    """Ensure engines did not retain the upstream bwrap function by value."""
    try:
        from gepa.oa import sandbox
        from gepa.oa.engines import autoresearch, meta_harness

        ok = (
            autoresearch.bwrap_prefix is sandbox.bwrap_prefix
            and meta_harness.bwrap_prefix is sandbox.bwrap_prefix
            and sandbox.bwrap_prefix.__module__ == "gepa_skill_backend_sandbox_overlay"
            and getattr(sandbox, "GEPA_SKILL_BACKEND_OVERLAY", "") >= "GEPA_SKILL_BACKEND_OVERLAY_V3"
        )
        return ok, "" if ok else "agentic engine retained an unpatched bwrap_prefix alias"
    except (ImportError, AttributeError) as exc:
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="gepa",
                    choices=["gepa", "best_of_n", "autoresearch", "meta_harness"])
    ap.add_argument("--test-lm", action="store_true",
                    help="make a 1-call round-trip to the reflection LM (costs a few tokens)")
    a = ap.parse_args()

    print("== optimize_anything preflight ==")

    # 1) import + the correct API surface
    try:
        import gepa  # noqa
        from gepa.optimize_anything import OptimizeAnythingConfig, optimize_anything  # noqa
        check(f"import gepa ({getattr(gepa, '__version__', '?')}) + optimize_anything", True)
    except Exception as e:  # noqa
        check("import gepa + optimize_anything", False, "pip install 'gepa[full]'")
        print(f"      {e}")
        return _report()

    # 2) LM credentials (in-process engines that call an LLM directly)
    lm = os.environ.get("GEPA_REFLECTION_LM", "")
    if a.engine in ("gepa", "best_of_n"):
        effective_lm = lm or DEFAULT_LM_BY_ENGINE[a.engine]
        if not lm:
            print(f"      GEPA_REFLECTION_LM unset -> engine default '{effective_lm}'")
        ok, fix = _creds_for(effective_lm)
        check(f"LLM creds present for '{effective_lm}'", ok, fix)

    # 3) agentic engines use the bundled Codex/OpenCode shim only.
    if a.engine in ("autoresearch", "meta_harness"):
        skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shim = os.path.join(skill_root, "bin", _AGENT_ENTRY)
        try:
            backend = selected_backend()
            state = prepare(backend)
        except (OSError, ValueError) as exc:
            backend = os.environ.get("GEPA_AGENT_BACKEND", "codex").lower()
            state = {"created": [], "verified": [], "missing": [str(exc)]}
        for path in state["created"]:
            print(f"      prepared {path}")
        for path in state["verified"]:
            print(f"      verified {path}")
        check(
            f"{backend.title()} sandbox state has no missing bind sources",
            not state["missing"],
            "; ".join(state["missing"]) or "prepare backend state before sandboxing",
        )
        executable = _configured_cli(backend)
        check(f"{backend.title()} CLI on PATH (required by {a.engine})", bool(executable),
              f"install {backend.title()} and authenticate a provider")
        check("bundled Codex/OpenCode agent shim", os.path.isfile(shim),
              f"restore {shim}")
        if not os.path.isdir(os.path.join(skill_root, ".venv")):
            check("skill virtualenv present", False,
                  f"create {skill_root}/.venv and pip install 'gepa[full]', then reapply overlay")
        aliases_ok, aliases_detail = _verify_agentic_caller_aliases()
        check("AutoResearch/MetaHarness use the installed sandbox overlay", aliases_ok, aliases_detail)
        if a.engine == "autoresearch":
            check("`jq` on PATH (used by the generated eval.sh)", bool(shutil.which("jq")),
                  "install jq")
        if sys.platform.startswith("linux"):
            check("`bwrap` on PATH (default sandbox=True jails agent with bubblewrap)",
                  bool(shutil.which("bwrap")),
                  "sudo apt/dnf install bubblewrap, or pass sandbox=False (runs unconfined)")
            if shutil.which("bwrap") and executable:
                ok, detail = _probe_shim_in_bwrap(backend)
                check("bundled shim resolves and executes inside bwrap (no backend call)", ok, detail)

    # 4) optional live LM round-trip
    if a.test_lm and a.engine in ("gepa", "best_of_n"):
        target = lm or DEFAULT_LM_BY_ENGINE[a.engine]
        try:
            from gepa.lm import LM
            out = LM(target)("Reply with the single word: ok")
            check(f"LM 1-call round-trip ({target})", bool(out),
                  "LM returned empty; check model id / creds / region")
        except Exception as e:  # noqa
            check(f"LM 1-call round-trip ({target})", False, str(e)[:160])

    return _report()


def _report() -> int:
    print()
    if problems:
        print(f"\033[31m{len(problems)} blocker(s):\033[0m")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\033[32mAll preflight checks passed.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
