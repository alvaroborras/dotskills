"""Skill-owned, backend-aware GEPA sandbox overlay.

Loaded from a .pth file in the skill virtualenv.  It deliberately replaces
runtime functions instead of editing ``gepa/oa/sandbox.py`` (which uv may
hardlink into its cache).
"""

from __future__ import annotations

import importlib
import os
import shutil
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

OVERLAY_VERSION = "GEPA_SKILL_BACKEND_OVERLAY_V2"


def _skill_root() -> Path:
    configured = os.environ.get("GEPA_SKILL_ROOT")
    candidates = [Path(configured)] if configured else []
    # Source file lives in ``scripts/``; installed overlay lives in the venv.
    candidates.extend(Path(__file__).resolve().parents[index] for index in (1, 4))
    for candidate in candidates:
        if (candidate / "bin" / "claude").is_file():
            return candidate
    raise RuntimeError("cannot locate GEPA skill root; set GEPA_SKILL_ROOT")


SKILL_ROOT = _skill_root()
BACKENDS = ("codex", "opencode")
AGENTIC_CALLERS = (
    "gepa.oa.engines.autoresearch",
    "gepa.oa.engines.meta_harness",
)


def selected_backend(value: str | None = None) -> str:
    backend = (value or os.environ.get("GEPA_AGENT_BACKEND") or "codex").lower()
    if backend not in BACKENDS:
        raise RuntimeError(f"unsupported GEPA_AGENT_BACKEND={backend!r}; expected one of {BACKENDS}")
    return backend


def _resolve_binary(backend: str) -> Path:
    env_name = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
    candidate = os.environ.get(env_name) or shutil.which(backend)
    if not candidate:
        raise RuntimeError(f"{backend} executable not found; set {env_name} or put it on PATH")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"{env_name} does not name an executable file: {path}")
    return path


def _shim_interpreter() -> tuple[Path, Path, Path, Path]:
    shim = (SKILL_ROOT / "bin" / "claude").resolve()
    first = shim.read_text(encoding="utf-8").splitlines()[0]
    if not first.startswith("#!"):
        raise RuntimeError(f"shim has no shebang: {shim}")
    interpreter = Path(first[2:].strip().split()[0])
    if not interpreter.is_file():
        raise RuntimeError(f"shim interpreter is unavailable: {interpreter}")
    # Preserve the first symlink target too.  A venv launcher commonly points
    # at an uv runtime alias (for example ``cpython-3.12``), which itself may
    # link to a versioned runtime.  Binding only the final resolved path leaves
    # the shebang pathname dangling inside bwrap.
    link_target = interpreter
    if interpreter.is_symlink():
        target = os.readlink(interpreter)
        link_target = Path(target) if os.path.isabs(target) else interpreter.parent / target
    resolved = interpreter.resolve()
    # Python may be symlinked outside the venv; mount its resolved runtime root.
    runtime_root = resolved.parent.parent
    if not runtime_root.is_dir():
        raise RuntimeError(f"shim runtime root is unavailable: {runtime_root}")
    return shim, link_target, link_target.parent.parent, runtime_root


def _state_paths(backend: str, home: Path) -> tuple[list[Path], list[Path]]:
    if backend == "codex":
        return [home / ".codex"], []
    return (
        [home / ".config" / "opencode", home / ".local" / "share" / "opencode", home / ".cache" / "opencode"],
        [home / ".opencode"],
    )


def prepare_backend_state(backend: str | None = None, *, home: Path | None = None) -> dict[str, list[Path]]:
    backend = selected_backend(backend)
    home = (home or Path.home()).resolve()
    writable, read_only = _state_paths(backend, home)
    created: list[Path] = []
    for path in writable:
        if not path.exists():
            path.mkdir(parents=True, mode=0o700)
            created.append(path)
        elif not path.is_dir():
            raise RuntimeError(f"required state path is not a directory: {path}")
    missing = [path for path in read_only if not path.exists()]
    return {"created": created, "writable": writable, "read_only": read_only, "missing": missing}


def _bind_args(paths: Iterable[Path], flag: str) -> list[str]:
    args: list[str] = []
    for path in paths:
        if path.exists() or path.is_symlink():
            args.extend([flag, str(path), str(path)])
    return args


def _directory_args(paths: Iterable[Path]) -> list[str]:
    """Create destination parents for exact binds without mounting their trees."""
    directories: set[Path] = set()
    for path in paths:
        parent = path.parent
        while parent != parent.parent and str(parent) != "/":
            directories.add(parent)
            parent = parent.parent
    args: list[str] = []
    for directory in sorted(directories, key=lambda item: len(item.parts)):
        args.extend(["--dir", str(directory)])
    return args


def bwrap_prefix(work_dir: str | Path, *, extra_writable=None, backend=None, home=None) -> list[str]:
    """Return a narrow bwrap command that can execute the bundled shim."""
    sandbox = importlib.import_module("gepa.oa.sandbox")
    if sandbox._IS_MACOS:
        return []
    backend = selected_backend(backend)
    home = (Path(home) if home else Path.home()).resolve()
    work = Path(work_dir).resolve()
    state = prepare_backend_state(backend, home=home)
    if state["missing"]:
        raise RuntimeError("missing required backend state: " + ", ".join(map(str, state["missing"])))
    executable = _resolve_binary(backend)
    shim, interpreter_target, runtime_alias_root, runtime_root = _shim_interpreter()
    venv = SKILL_ROOT / ".venv"
    if not venv.is_dir():
        raise RuntimeError(f"skill virtualenv is unavailable: {venv}")
    command_var = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
    narrow_sources = [shim.parent, executable, interpreter_target, runtime_alias_root, venv, runtime_root, *state["read_only"], *state["writable"], work]
    args = [
        "bwrap", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        *sandbox._system_bind_args(), *sandbox._etc_bind_args(),
        *_directory_args(narrow_sources),
        # bwrap needs the shim's containing directory to make its absolute
        # pathname resolvable.  That directory is the skill's one-file ``bin``
        # directory, not a user state tree.
        *_bind_args([shim.parent, executable, interpreter_target, runtime_alias_root, venv, runtime_root], "--ro-bind"),
        *_bind_args(state["read_only"], "--ro-bind"),
        *_bind_args(state["writable"], "--bind"),
        "--bind", str(work), str(work), "--unshare-uts", "--hostname", "sandbox",
        "--setenv", "HOME", str(home), "--setenv", "GEPA_AGENT_BACKEND", backend,
        "--setenv", command_var, str(executable),
        "--setenv", "PATH", f"{shim.parent}:/usr/local/bin:/usr/bin:/bin",
        "--chdir", str(work),
    ]
    for path in extra_writable or ():
        args.extend(_bind_args([Path(path).resolve()], "--bind"))
    # A selected CLI can live below any writable mount: selected backend state,
    # the work directory, or a caller-supplied writable tree. This must be the
    # final bind so no later writable ancestor can make the executable
    # replaceable inside the jail.
    args.extend(_bind_args([executable], "--ro-bind"))
    return args


def agent_cli_name() -> str:
    """Return the on-PATH name engines should exec.

    GEPA upstream hardcodes ``claude``.  This skill never runs native Claude:
    engines must invoke the skill shim (still named ``claude`` only as a PATH
    compatibility entry) which immediately re-execs Codex or OpenCode based on
    ``GEPA_AGENT_BACKEND``.  Prefer the absolute shim path so a random
    system ``claude`` cannot win the PATH race.
    """
    return str((SKILL_ROOT / "bin" / "claude").resolve())


def _agent_env(env: dict | None = None) -> dict[str, str]:
    out = dict(env or os.environ)
    out.setdefault("GEPA_AGENT_BACKEND", selected_backend())
    out.setdefault("GEPA_DEFAULT_MODEL", "gpt-5.6-luna")
    if selected_backend() == "codex":
        out.setdefault("GEPA_CODEX_MODEL", out.get("GEPA_DEFAULT_MODEL", "gpt-5.6-luna"))
    else:
        out.setdefault("GEPA_OPENCODE_MODEL", out.get("GEPA_DEFAULT_MODEL", "gpt-5.6-luna"))
    return out


def _rewrite_agent_cmd(cmd: list[str], shim: str) -> list[str]:
    rewritten = list(cmd)
    for index, token in enumerate(rewritten):
        if token == "claude" or str(token).endswith("/claude"):
            rewritten[index] = shim
            break
    return rewritten


def _patch_engine_agent_binary(caller: ModuleType) -> None:
    """Force agentic engines to exec the skill shim (Codex/OpenCode backend)."""
    shim = agent_cli_name()

    starter = getattr(caller, "_start_claude_process", None)
    if starter is not None and not getattr(starter, "_gepa_skill_agent_patched", False):
        def _start(cmd, work_dir, env, __starter=starter, __shim=shim):  # type: ignore[no-untyped-def]
            return __starter(_rewrite_agent_cmd(cmd, __shim), work_dir, _agent_env(env))

        _start._gepa_skill_agent_patched = True  # type: ignore[attr-defined]
        caller._start_claude_process = _start  # type: ignore[attr-defined]

    # meta_harness (and any similar caller) builds cmd inline then subprocess.run.
    subproc = getattr(caller, "subprocess", None)
    if subproc is not None and hasattr(subproc, "run") and not getattr(subproc.run, "_gepa_skill_agent_patched", False):
        original_run = subproc.run

        def _run(cmd, *args, __original=original_run, __shim=shim, **kwargs):  # type: ignore[no-untyped-def]
            if isinstance(cmd, (list, tuple)) and any(
                token == "claude" or str(token).endswith("/claude") for token in cmd
            ):
                cmd = _rewrite_agent_cmd(list(cmd), __shim)
                env = kwargs.get("env")
                kwargs["env"] = _agent_env(env)
            return __original(cmd, *args, **kwargs)

        _run._gepa_skill_agent_patched = True  # type: ignore[attr-defined]
        subproc.run = _run  # type: ignore[assignment]


def install(module: ModuleType | None = None) -> None:
    """Install the replacement in sandbox and every by-value engine import."""
    module = module or importlib.import_module("gepa.oa.sandbox")
    required = ("_IS_MACOS", "_system_bind_args", "_etc_bind_args", "bwrap_prefix")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"incompatible GEPA sandbox API; missing {', '.join(missing)}")
    module.bwrap_prefix = bwrap_prefix
    module.prepare_backend_state = prepare_backend_state
    module._agent_backend = selected_backend
    module.GEPA_SKILL_BACKEND_OVERLAY = OVERLAY_VERSION
    callers: list[str] = []
    for module_name in AGENTIC_CALLERS:
        caller = importlib.import_module(module_name)
        if not hasattr(caller, "bwrap_prefix"):
            raise RuntimeError(f"incompatible GEPA caller API; {module_name} has no bwrap_prefix")
        caller.bwrap_prefix = bwrap_prefix
        _patch_engine_agent_binary(caller)
        callers.append(module_name)
    stale = [
        module_name
        for module_name in callers
        if importlib.import_module(module_name).bwrap_prefix is not bwrap_prefix
    ]
    if stale:
        raise RuntimeError(f"failed to patch GEPA caller aliases: {', '.join(stale)}")
