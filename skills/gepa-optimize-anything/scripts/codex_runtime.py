#!/usr/bin/env python3
"""Install the Codex bridge for GEPA's subprocess engines.

GEPA's agent engines import a few process helpers by value and construct their
own command lines.  This module patches those call sites without modifying
the installed GEPA package or its package-manager cache.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

RUNTIME_VERSION = "GEPA_SKILL_CODEX_RUNTIME_V1"
AGENTIC_CALLERS = (
    "gepa.oa.engines.autoresearch",
    "gepa.oa.engines.meta_harness",
)
ENTRYPOINT = "gepa-agent"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_EFFORT = "high"
DEFAULT_PARENT_COUNT = 2
DEFAULT_MUTATION_COUNT = 2


def skill_root() -> Path:
    configured = os.environ.get("GEPA_SKILL_ROOT")
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    source = Path(__file__).resolve()
    candidates.extend((source.parents[1], source.parents[3]))
    for candidate in candidates:
        if (candidate / "bin" / ENTRYPOINT).is_file():
            return candidate
    raise RuntimeError("cannot locate the GEPA skill; set GEPA_SKILL_ROOT")


SKILL_ROOT = skill_root()


def shim_path() -> Path:
    return (SKILL_ROOT / "bin" / ENTRYPOINT).resolve()


def codex_path() -> Path:
    configured = os.environ.get("CODEX_BIN")
    value = configured or shutil.which("codex")
    if not value:
        raise RuntimeError("Codex was not found; install it or set CODEX_BIN")
    path = Path(value).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"Codex executable is invalid: {path}")
    return path


def agent_environment(environment: dict[str, str] | None = None) -> dict[str, str]:
    result = dict(environment or os.environ)
    result["GEPA_SKILL_ROOT"] = str(SKILL_ROOT)
    result["PATH"] = f"{shim_path().parent}:{result.get('PATH', '')}"
    return result


def no_process_prefix(*_args: object, **_kwargs: object) -> list[str]:
    """Keep GEPA's legacy prefix hook as a no-op."""
    return []


def permission_args(*_args: object, **_kwargs: object) -> list[str]:
    """Return the non-interactive permission posture consumed by the shim."""
    return ["--permission-mode", "bypassPermissions"]


def require_codex(engine_name: str) -> None:
    if not shim_path().is_file():
        raise RuntimeError(
            f"{engine_name} requires the skill entrypoint at {shim_path()}"
        )
    codex_path()


def preflight_agent_engine(engine_name: str, *, sandbox: bool = False) -> None:
    if sandbox:
        raise RuntimeError(
            f"{engine_name} requested sandbox=True, but this Codex skill deliberately runs without OS confinement"
        )
    require_codex(engine_name)


def _new_default_proposal_strategies() -> tuple[object, object]:
    from gepa.strategies.proposal_sampling import PxNSampling
    from gepa.strategies.proposal_selection import AllImprovements

    return (
        PxNSampling(p=DEFAULT_PARENT_COUNT, n=DEFAULT_MUTATION_COUNT),
        AllImprovements(),
    )


def apply_default_proposal_strategies(config: object) -> None:
    """Use the skill's parallel proposal defaults on a GEPA config."""
    if getattr(config, "engine", None) != "gepa":
        return

    raw_config = getattr(config, "engine_config", None)
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        return

    engine_config = dict(raw_config)
    engine_options = engine_config.get("engine")
    if engine_options is None:
        engine_options = {}
    if isinstance(engine_options, dict):
        engine_options = dict(engine_options)
        sampling, selection = _new_default_proposal_strategies()
        engine_options.setdefault("sampling_strategy", sampling)
        engine_options.setdefault("selection_strategy", selection)
        engine_config["engine"] = engine_options
    else:
        if getattr(engine_options, "sampling_strategy", None) is None:
            sampling, _ = _new_default_proposal_strategies()
            engine_options.sampling_strategy = sampling
        if getattr(engine_options, "selection_strategy", None) is None:
            _, selection = _new_default_proposal_strategies()
            engine_options.selection_strategy = selection
    config.engine_config = engine_config


def _patch_config_defaults() -> None:
    module = importlib.import_module("gepa.oa.config")
    config_cls = module.OptimizeAnythingConfig
    original = config_cls.__init__
    if getattr(original, "_gepa_codex_defaults_wrapped", False):
        return

    def init(self: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        original(self, *args, **kwargs)
        apply_default_proposal_strategies(self)

    init.__name__ = getattr(original, "__name__", "__init__")
    init.__doc__ = getattr(original, "__doc__", None)
    init._gepa_codex_defaults_wrapped = True  # type: ignore[attr-defined]
    config_cls.__init__ = init


def _rewrite_meta_paths(value: str) -> str:
    if "skills/" not in value or "gepa-optimize-anything-meta-harness" not in value:
        return value
    return re.sub(r"\.[^/\s]+/skills/", ".codex/skills/", value)


def rewrite_command(command: object) -> tuple[object, dict[str, str] | None]:
    if not isinstance(command, (list, tuple)) or "--print" not in command:
        return command, None
    rewritten = [
        _rewrite_meta_paths(str(item)) if isinstance(item, str) else item
        for item in command
    ]
    rewritten[0] = str(shim_path())
    return type(command)(rewritten), agent_environment()


def _intercept(
    command: object, kwargs: dict[str, object]
) -> tuple[object, dict[str, object]]:
    rewritten, environment = rewrite_command(command)
    if environment is None:
        return command, kwargs
    updated = dict(kwargs)
    supplied = updated.get("env")
    base = (
        None
        if not isinstance(supplied, dict)
        else {str(key): str(value) for key, value in supplied.items()}
    )
    updated["env"] = agent_environment(base)
    return rewritten, updated


@contextlib.contextmanager
def _subprocess_bridge(method: str) -> Iterator[None]:
    original = getattr(subprocess, method)

    def bridged(command: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        command, kwargs = _intercept(command, kwargs)
        return original(command, *args, **kwargs)

    setattr(subprocess, method, bridged)
    try:
        yield
    finally:
        setattr(subprocess, method, original)


def _wrap_method_with_bridge(cls: type, method_name: str, process_method: str) -> None:
    method = getattr(cls, method_name)
    if getattr(method, "_gepa_codex_wrapped", False):
        return

    def wrapped(self: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        with _subprocess_bridge(process_method):
            return method(self, *args, **kwargs)

    wrapped.__name__ = getattr(method, "__name__", method_name)
    wrapped.__doc__ = getattr(method, "__doc__", None)
    wrapped._gepa_codex_wrapped = True  # type: ignore[attr-defined]
    setattr(cls, method_name, wrapped)


def _patch_agentic_module(module: ModuleType) -> None:
    if hasattr(module, "_run_proposer"):
        function = module._run_proposer
        if not getattr(function, "_gepa_codex_wrapped", False):

            def wrapped(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                with _subprocess_bridge("run"):
                    return function(*args, **kwargs)

            wrapped.__name__ = function.__name__
            wrapped.__doc__ = function.__doc__
            wrapped._gepa_codex_wrapped = True  # type: ignore[attr-defined]
            module._run_proposer = wrapped

    engine_cls = getattr(module, "AutoResearchEngine", None)
    if engine_cls is not None:
        for name in dir(engine_cls):
            if not name.startswith("_run_"):
                continue
            method = getattr(engine_cls, name, None)
            if not callable(method):
                continue
            try:
                parameters = inspect.signature(method).parameters
            except (TypeError, ValueError):
                continue
            if {"work_dir", "prompt"}.issubset(parameters):
                _wrap_method_with_bridge(engine_cls, name, "Popen")
                break

        original_init = getattr(engine_cls, "__init__", None)
        if original_init is not None and not getattr(
            original_init, "_gepa_codex_init_wrapped", False
        ):

            def init(self: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                original_init(self, *args, **kwargs)
                if hasattr(self, "ralph"):
                    self.ralph = False

            init._gepa_codex_init_wrapped = True  # type: ignore[attr-defined]
            engine_cls.__init__ = init  # type: ignore[method-assign]


def _relocate_generated_skill(work_dir: Path) -> None:
    destination = work_dir / ".codex" / "skills"
    for child in list(work_dir.iterdir()):
        if not child.is_dir() or child.name == ".codex":
            continue
        source = child / "skills" / "gepa-optimize-anything-meta-harness"
        if not source.is_dir():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(source), str(target))
        try:
            (child / "skills").rmdir()
            child.rmdir()
        except OSError:
            pass


def _patch_meta_materializer(module: ModuleType) -> None:
    original = getattr(module, "_materialize_sandbox", None)
    if original is None or getattr(original, "_gepa_codex_wrapped", False):
        return

    def materialize(work_dir: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        result = original(work_dir, *args, **kwargs)
        _relocate_generated_skill(Path(work_dir))
        return result

    materialize.__name__ = original.__name__
    materialize.__doc__ = original.__doc__
    materialize._gepa_codex_wrapped = True  # type: ignore[attr-defined]
    module._materialize_sandbox = materialize


def _patch_legacy_aliases(
    caller: ModuleType,
    old_permission: list[object],
    old_preflight: list[object],
) -> None:
    for name, value in list(vars(caller).items()):
        if any(value is candidate for candidate in old_permission):
            setattr(caller, name, permission_args)
        elif any(value is candidate for candidate in old_preflight):
            setattr(caller, name, preflight_agent_engine)
    if hasattr(caller, "bwrap_prefix"):
        caller.bwrap_prefix = no_process_prefix


def install() -> None:
    _patch_config_defaults()
    runtime_module = importlib.import_module("gepa.oa.sandbox")
    old_permission = [
        value
        for name, value in vars(runtime_module).items()
        if name.endswith("_permission_args") and callable(value)
    ]
    old_preflight = [
        value
        for name, value in vars(runtime_module).items()
        if name.startswith("preflight_")
        and name.endswith("_engine")
        and callable(value)
    ]
    runtime_module.bwrap_prefix = no_process_prefix
    runtime_module.GEPA_SKILL_CODEX_RUNTIME = RUNTIME_VERSION
    for name in list(vars(runtime_module)):
        if name.endswith("_permission_args"):
            setattr(runtime_module, name, permission_args)
        elif name.startswith("preflight_") and name.endswith("_engine"):
            setattr(runtime_module, name, preflight_agent_engine)

    for module_name in AGENTIC_CALLERS:
        caller = importlib.import_module(module_name)
        _patch_legacy_aliases(caller, old_permission, old_preflight)
        _patch_agentic_module(caller)
        if module_name.endswith("meta_harness"):
            _patch_meta_materializer(caller)

    runtime_module.GEPA_SKILL_CODEX_RUNTIME = RUNTIME_VERSION


if __name__ == "__main__":
    install()
    print(RUNTIME_VERSION)
