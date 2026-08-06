"""Skill-owned, backend-aware GEPA sandbox overlay.

Loaded from a .pth file in the skill virtualenv.  It deliberately replaces
runtime functions instead of editing ``gepa/oa/sandbox.py`` (which uv may
hardlink into its cache).

GEPA agentic engines hardcode an on-PATH agent entry basename and a
``--print`` JSON contract.  This skill supplies that entry as a shim that
always re-execs Codex (default) or OpenCode — never a third-party agent CLI.
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

OVERLAY_VERSION = "GEPA_SKILL_BACKEND_OVERLAY_V4"
# GPT-5.6 family: luna (default), terra, sol. Reasoning via GEPA_REASONING_EFFORT.
DEFAULT_AGENT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "high"
# The skill exposes an explicit backend-neutral entrypoint. Upstream GEPA still
# constructs a legacy token internally; the overlay rewrites that token to the
# absolute Codex/OpenCode entrypoint before subprocess creation. It is never
# resolved on PATH and no Claude Code binary is called.
_ENTRY_BASENAME = "gepa-agent"
_UPSTREAM_ENTRY_BASENAME = "claude"


def _skill_root() -> Path:
    configured = os.environ.get("GEPA_SKILL_ROOT")
    candidates = [Path(configured)] if configured else []
    # Source file lives in ``scripts/``; installed overlay lives in the venv.
    candidates.extend(Path(__file__).resolve().parents[index] for index in (1, 4))
    for candidate in candidates:
        if (candidate / "bin" / _ENTRY_BASENAME).is_file():
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
        raise RuntimeError(
            "GEPA backend selection failed: unsupported backend\n"
            f"  configured: GEPA_AGENT_BACKEND={backend!r}\n"
            f"  supported: {', '.join(BACKENDS)}\n"
            "  fix: export GEPA_AGENT_BACKEND=codex  # or opencode\n"
            "  note: Claude Code and other backends are intentionally rejected"
        )
    return backend


def _resolve_binary(backend: str) -> Path:
    env_name = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
    candidate = os.environ.get(env_name) or shutil.which(backend)
    if not candidate:
        raise RuntimeError(
            f"GEPA {backend} executable resolution failed\n"
            f"  backend: {backend}\n"
            f"  override: {env_name}={os.environ.get(env_name) or '(unset)'}\n"
            f"  PATH lookup: {shutil.which(backend) or '(not found)'}\n"
            f"  fix: set {env_name}=/absolute/path/to/{backend}, or put {backend} on PATH"
        )
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(
            f"GEPA {backend} executable is invalid\n"
            f"  source: {env_name if os.environ.get(env_name) else 'PATH'}\n"
            f"  resolved: {path}\n"
            f"  exists: {path.is_file()}\n"
            f"  executable: {os.access(path, os.X_OK)}\n"
            f"  fix: point {env_name} at an executable {backend} CLI"
        )
    return path


def _shim_path() -> Path:
    return (SKILL_ROOT / "bin" / _ENTRY_BASENAME).resolve()


def _shim_interpreter() -> tuple[Path, Path, Path, Path]:
    shim = _shim_path()
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
        raise RuntimeError(
            "GEPA sandbox backend state is incomplete: missing required backend state\n"
            f"  backend: {backend}\n"
            f"  home: {home}\n"
            f"  missing: {', '.join(map(str, state['missing']))}\n"
            f"  fix: authenticate {backend} outside GEPA so its state exists, then rerun preflight"
        )
    executable = _resolve_binary(backend)
    shim, interpreter_target, runtime_alias_root, runtime_root = _shim_interpreter()
    venv = SKILL_ROOT / ".venv"
    if not venv.is_dir():
        raise RuntimeError(f"skill virtualenv is unavailable: {venv}")
    command_var = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
    narrow_sources = [
        shim.parent, executable, interpreter_target, runtime_alias_root,
        venv, runtime_root, *state["read_only"], *state["writable"], work,
    ]
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
    """Absolute path of the skill shim engines should exec."""
    return str(_shim_path())


def _agent_env(env: dict | None = None) -> dict[str, str]:
    out = dict(env or os.environ)
    backend = selected_backend()
    out["GEPA_AGENT_BACKEND"] = backend
    out.setdefault("GEPA_DEFAULT_MODEL", DEFAULT_AGENT_MODEL)
    out.setdefault("GEPA_REASONING_EFFORT", DEFAULT_REASONING_EFFORT)
    if backend == "codex":
        out.setdefault("GEPA_CODEX_MODEL", out.get("GEPA_DEFAULT_MODEL", DEFAULT_AGENT_MODEL))
    else:
        out.setdefault("GEPA_OPENCODE_MODEL", out.get("GEPA_DEFAULT_MODEL", DEFAULT_AGENT_MODEL))
    # Prefer the skill shim over any other same-basename binary on PATH.
    out["PATH"] = f"{_shim_path().parent}:{out.get('PATH', '')}"
    return out


def _is_shim_path(token: object) -> bool:
    text = str(token)
    if not text:
        return False
    try:
        return Path(text).resolve() == _shim_path()
    except OSError:
        return False


def _is_upstream_entry_token(token: object) -> bool:
    """True for GEPA's legacy internal agent slot, never a runnable backend."""
    text = str(token)
    if text == _UPSTREAM_ENTRY_BASENAME:
        return True
    if text.endswith(f"/{_UPSTREAM_ENTRY_BASENAME}") and not _is_shim_path(text):
        return True
    return False


def _rewrite_agent_cmd(cmd: list[str], shim: str) -> list[str]:
    rewritten = list(cmd)
    for index, token in enumerate(rewritten):
        if _is_upstream_entry_token(token):
            rewritten[index] = shim
            break
    return rewritten


def _boxed(title: str, lines: list[str]) -> str:
    width = max(len(title), *(len(line) for line in lines), 40)
    bar = "=" * (width + 4)
    body = "\n".join(f"| {line:<{width}} |" for line in [title, "", *lines])
    return f"{bar}\n{body}\n{bar}"


def require_agent_cli(engine_name: str) -> None:
    """Abort when the skill shim or selected Codex/OpenCode CLI is missing."""
    shim = _shim_path()
    if not shim.is_file():
        print(
            _boxed(
                "GEPA AGENT SHIM NOT FOUND",
                [
                    f"The {engine_name!r} engine needs this skill's agent shim at:",
                    f"  {shim}",
                    "Restore the skill's bin/ entry and put it first on PATH.",
                ],
            ),
            file=sys.stderr,
            flush=True,
        )
        raise RuntimeError(f"the {engine_name!r} engine requires the skill agent shim at {shim}")
    backend = selected_backend()
    try:
        _resolve_binary(backend)
    except RuntimeError as exc:
        print(
            _boxed(
                f"{backend.upper()} CLI NOT FOUND",
                [
                    f"The {engine_name!r} engine runs through {backend.title()} via the skill shim,",
                    f"but {backend!r} is not available.",
                    "",
                    str(exc),
                    "",
                    "Install and authenticate the CLI, or set CODEX_BIN / OPENCODE_BIN.",
                    "Select backend with GEPA_AGENT_BACKEND=codex|opencode (default: codex).",
                ],
            ),
            file=sys.stderr,
            flush=True,
        )
        raise RuntimeError(
            f"the {engine_name!r} engine requires the {backend} CLI (GEPA_AGENT_BACKEND={backend})"
        ) from exc


def require_bwrap(engine_name: str) -> None:
    sandbox = importlib.import_module("gepa.oa.sandbox")
    if sandbox._IS_MACOS or shutil.which("bwrap"):
        return
    print(
        _boxed(
            "SANDBOX UNAVAILABLE: bwrap NOT FOUND",
            [
                "sandbox=True jails the Codex/OpenCode agent subprocess with bubblewrap on",
                "Linux, but no `bwrap` executable is on PATH.",
                "",
                "Install it:",
                "  sudo apt install bubblewrap   (Debian/Ubuntu)",
                "  sudo dnf install bubblewrap   (Fedora/RHEL)",
                "",
                "Or pass OptimizeAnythingConfig(sandbox=False) to run unsandboxed.",
            ],
        ),
        file=sys.stderr,
        flush=True,
    )
    raise RuntimeError(
        f"sandbox=True on the {engine_name!r} engine but `bwrap` (bubblewrap) was not found on PATH; "
        "install bubblewrap or set sandbox=False"
    )


def warn_sandbox_disabled(engine_name: str) -> None:
    print(
        _boxed(
            "SANDBOX DISABLED",
            [
                f"sandbox=False: the {engine_name!r} engine's Codex/OpenCode agent",
                "runs with no OS-level confinement — unrestricted access as this user.",
                "",
                "Set sandbox=True (the default) to confine it to a throwaway",
                "work dir (bwrap on Linux).",
            ],
        ),
        file=sys.stderr,
        flush=True,
    )


def preflight_agent_engine(engine_name: str, *, sandbox: bool) -> None:
    require_agent_cli(engine_name)
    if sandbox:
        require_bwrap(engine_name)
    else:
        warn_sandbox_disabled(engine_name)


def _patch_engine_agent_binary(caller: ModuleType) -> None:
    """Force agentic engines to exec the skill shim (Codex/OpenCode backend)."""
    shim = agent_cli_name()

    # Upstream symbol name is fixed by the GEPA package.
    starter = getattr(caller, "_start_claude_process", None)
    if starter is not None and not getattr(starter, "_gepa_skill_agent_patched", False):
        def _start(cmd, work_dir, env, __starter=starter, __shim=shim):  # type: ignore[no-untyped-def]
            rewritten = list(cmd)
            if any(_is_upstream_entry_token(token) for token in rewritten):
                rewritten = _rewrite_agent_cmd(rewritten, __shim)
                env = _agent_env(env)
            return __starter(rewritten, work_dir, env)

        _start._gepa_skill_agent_patched = True  # type: ignore[attr-defined]
        caller._start_claude_process = _start  # type: ignore[attr-defined]

    # meta_harness (and any similar caller) builds cmd inline then subprocess.run.
    subproc = getattr(caller, "subprocess", None)
    if subproc is not None and hasattr(subproc, "run") and not getattr(subproc.run, "_gepa_skill_agent_patched", False):
        original_run = subproc.run

        def _run(cmd, *args, __original=original_run, __shim=shim, **kwargs):  # type: ignore[no-untyped-def]
            # Only rewrite upstream bare-name / foreign-binary launches. Direct
            # invocations of this skill's shim (tests, nested probes) keep their
            # caller env untouched — important because this patches the shared
            # stdlib subprocess module via the engine's `import subprocess`.
            if isinstance(cmd, (list, tuple)) and any(_is_upstream_entry_token(token) for token in cmd):
                cmd = _rewrite_agent_cmd(list(cmd), __shim)
                kwargs["env"] = _agent_env(kwargs.get("env"))
            return __original(cmd, *args, **kwargs)

        _run._gepa_skill_agent_patched = True  # type: ignore[attr-defined]
        subproc.run = _run  # type: ignore[assignment]


def _patch_autoresearch_defaults(caller: ModuleType) -> None:
    """Disable session-resume loops; Codex/OpenCode shim has no --resume bridge."""
    engine_cls = getattr(caller, "AutoResearchEngine", None)
    if engine_cls is None or getattr(engine_cls, "_gepa_skill_init_patched", False):
        return
    original_init = engine_cls.__init__

    def _init(self, config, __original=original_init):  # type: ignore[no-untyped-def]
        __original(self, config)
        # Upstream default ralph=True uses --resume; the shim consumes that flag
        # without forwarding it, so multi-turn resume would silently no-op.
        self.ralph = False

    _init._gepa_skill_agent_patched = True  # type: ignore[attr-defined]
    engine_cls.__init__ = _init  # type: ignore[method-assign]
    engine_cls._gepa_skill_init_patched = True  # type: ignore[attr-defined]


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
    module.require_claude_cli = require_agent_cli
    module.require_bwrap = require_bwrap
    module.warn_sandbox_disabled = warn_sandbox_disabled
    module.preflight_claude_engine = preflight_agent_engine
    module.GEPA_SKILL_BACKEND_OVERLAY = OVERLAY_VERSION

    callers: list[str] = []
    for module_name in AGENTIC_CALLERS:
        caller = importlib.import_module(module_name)
        if not hasattr(caller, "bwrap_prefix"):
            raise RuntimeError(f"incompatible GEPA caller API; {module_name} has no bwrap_prefix")
        caller.bwrap_prefix = bwrap_prefix
        if hasattr(caller, "preflight_claude_engine"):
            caller.preflight_claude_engine = preflight_agent_engine
        if hasattr(caller, "require_claude_cli"):
            caller.require_claude_cli = require_agent_cli
        _patch_engine_agent_binary(caller)
        if module_name.endswith("autoresearch"):
            _patch_autoresearch_defaults(caller)
        callers.append(module_name)

    stale = [
        module_name
        for module_name in callers
        if importlib.import_module(module_name).bwrap_prefix is not bwrap_prefix
    ]
    if stale:
        raise RuntimeError(f"failed to patch GEPA caller aliases: {', '.join(stale)}")
