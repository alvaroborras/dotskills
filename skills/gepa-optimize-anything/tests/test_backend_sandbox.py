"""Regression coverage for the narrow, executable GEPA bwrap overlay."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
OVERLAY = ROOT / "scripts" / "backend_sandbox_overlay.py"
REAPPLY = ROOT / "scripts" / "reapply_backend_sandbox.py"
PREFLIGHT = ROOT / "scripts" / "preflight.py"
# Explicit backend-neutral entrypoint; the legacy upstream slot is rewritten.
AGENT_ENTRY = "gepa-agent"
SHIM = ROOT / "bin" / AGENT_ENTRY


def load_overlay():
    spec = importlib.util.spec_from_file_location("skill_overlay_test", OVERLAY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reapply():
    spec = importlib.util.spec_from_file_location("skill_reapply_test", REAPPLY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_preflight():
    spec = importlib.util.spec_from_file_location("skill_preflight_test", PREFLIGHT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PREFLIGHT.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class BackendSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.overlay = load_overlay()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.work = self.root / "work"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.work.mkdir()
        self.bin.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fake_cli(self, name: str, event: dict) -> Path:
        executable = self.bin / name
        executable.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps(event) + "'\n")
        executable.chmod(0o755)
        return executable

    def _nested_fake_cli(self, relative: str, event: dict) -> Path:
        executable = self.home / relative
        return self._fake_cli_at(executable, event)

    @staticmethod
    def _fake_cli_at(executable: Path, event: dict) -> Path:
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps(event) + "'\n")
        executable.chmod(0o755)
        return executable

    def _capturing_codex(self, arguments: Path, stdin: Path) -> Path:
        executable = self.bin / "codex"
        events = [
            {"item": {"type": "agent_message", "text": "agent reply"}},
            {"type": "response.output_text.done", "text": "final reply"},
        ]
        executable.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$@\" > {shlex.quote(str(arguments))}\n"
            f"cat > {shlex.quote(str(stdin))}\n"
            + "".join(f"printf '%s\\n' {shlex.quote(json.dumps(event))}\n" for event in events),
        )
        executable.chmod(0o755)
        return executable

    def _args(self, backend: str, executable: Path) -> list[str]:
        env_name = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
        old = os.environ.get(env_name)
        os.environ[env_name] = str(executable)
        try:
            return self.overlay.bwrap_prefix(self.work, backend=backend, home=self.home)
        finally:
            if old is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = old

    def test_codex_mounts_only_codex_state_and_exact_cli(self) -> None:
        executable = self._fake_cli("codex", {"type": "response.output_text.done", "text": "mock"})
        args = self._args("codex", executable)
        text = " ".join(args)
        self.assertIn(str(self.home / ".codex"), text)
        self.assertIn(str(executable.resolve()), text)
        for forbidden in (".opencode", ".config/opencode", ".local/share/opencode", ".cache/opencode"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn(str(self.home / ".local"), args)
        self.assertNotIn(str(self.home / ".cache"), args)

    def test_opencode_mounts_its_three_state_dirs_and_no_codex_state(self) -> None:
        (self.home / ".opencode").mkdir()
        executable = self._fake_cli("opencode", {"type": "text", "text": "mock"})
        args = self._args("opencode", executable)
        text = " ".join(args)
        for relative in (".config/opencode", ".local/share/opencode", ".cache/opencode", ".opencode"):
            self.assertIn(str(self.home / relative), text)
        self.assertNotIn(str(self.home / ".codex"), text)

    def test_unsupported_backend_fails_closed(self) -> None:
        for backend in ("native", "claude"):
            with self.subTest(backend=backend), self.assertRaisesRegex(RuntimeError, "unsupported"):
                self.overlay.selected_backend(backend)

    def test_upstream_legacy_command_is_rewritten_to_neutral_entrypoint(self) -> None:
        rewritten = self.overlay._rewrite_agent_cmd(
            ["claude", "--print", "probe"],
            str(SHIM),
        )
        self.assertEqual(rewritten, [str(SHIM), "--print", "probe"])
        self.assertNotIn("claude", rewritten)

    def test_shim_fails_closed_for_unknown_backends(self) -> None:
        for backend in ("native", "unknown", "claude"):
            completed = subprocess.run(
                [str(SHIM), "--print", "no-model-call"],
                env={
                    **os.environ,
                    "GEPA_AGENT_BACKEND": backend,
                    "CODEX_BIN": "/bin/false",
                    "OPENCODE_BIN": "/bin/false",
                },
                capture_output=True,
                check=False,
                text=True,
            )
            with self.subTest(backend=backend):
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn("unsupported GEPA_AGENT_BACKEND", completed.stderr)
                self.assertIn("[GEPA_AGENT_ERROR]", completed.stderr)
                self.assertIn("stage: backend-selection", completed.stderr)
                self.assertIn("prompt: redacted", completed.stderr)
                self.assertIn("how_to_fix:", completed.stderr)

    def test_backend_failure_reports_safe_actionable_configuration(self) -> None:
        secret_prompt = "do-not-echo-this-prompt"
        completed = subprocess.run(
            [str(SHIM), "--print", secret_prompt],
            cwd=self.work,
            env={
                **os.environ,
                "GEPA_AGENT_BACKEND": "codex",
                "CODEX_BIN": "/bin/false",
                "GEPA_CODEX_MODEL": "terra",
                "GEPA_REASONING_EFFORT": "xhigh",
            },
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("[GEPA_AGENT_ERROR]", completed.stderr)
        self.assertIn("stage: backend-execution", completed.stderr)
        self.assertIn("backend: 'codex'", completed.stderr)
        self.assertIn("executable: /bin/false", completed.stderr)
        self.assertIn("model: gpt-5.6-terra", completed.stderr)
        self.assertIn("reasoning_effort: xhigh", completed.stderr)
        self.assertIn("prompt: redacted", completed.stderr)
        self.assertNotIn(secret_prompt, completed.stderr)
        self.assertIn("how_to_fix:", completed.stderr)

    def test_codex_shim_consumes_upstream_flags_and_emits_result_envelope(self) -> None:
        arguments = self.root / "codex-argv.txt"
        stdin = self.root / "codex-stdin.txt"
        executable = self._capturing_codex(arguments, stdin)
        prompt = "Read program.md and write best_candidate.txt"
        completed = subprocess.run(
            [
                str(SHIM),
                "--print",
                "--output-format", "json",
                "--model", "sonnet",
                "--system-prompt", "Base system instruction",
                "--append-system-prompt", "Extra system instruction",
                "--max-turns", "3",
                "--max-budget-usd", "0.01",
                "--effort", "high",
                "--session-id", "agent-session-id",
                "--disallowedTools=WebFetch,WebSearch",
                "--permission-mode", "bypassPermissions",
                prompt,
            ],
            cwd=self.work,
            env={
                **os.environ,
                "GEPA_AGENT_BACKEND": "codex",
                "CODEX_BIN": str(executable),
                "GEPA_CODEX_MODEL": "terra",
                # Overlay-style default; CLI --effort high must win.
                "GEPA_REASONING_EFFORT": "medium",
            },
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(
            arguments.read_text().splitlines(),
            [
                "exec", "--json", "--dangerously-bypass-approvals-and-sandbox",
                "-C", str(self.work), "--model", "gpt-5.6-terra",
                "-c", "model_reasoning_effort=high", "-",
            ],
        )
        self.assertEqual(
            stdin.read_text(),
            "Base system instruction\n\nExtra system instruction\n\n" + prompt,
        )
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "type": "result", "result": "agent replyfinal reply",
                "is_error": False, "total_cost_usd": 0.0, "usage": {},
            },
        )

    def test_reapply_breaks_installed_hardlink_without_writing_cache_fixture(self) -> None:
        reapply = load_reapply()
        cache = self.root / "uv-cache" / "sandbox.py"
        target = self.root / "site-packages" / "gepa" / "oa" / "sandbox.py"
        cache.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        clean = "def bwrap_prefix():\n    return []\n"
        cache.write_text(clean)
        os.link(cache, target)
        cache_inode = cache.stat().st_ino
        reapply.install(target.parents[2])
        self.assertEqual(cache.read_text(), clean)
        self.assertEqual(cache.stat().st_ino, cache_inode)
        self.assertNotEqual(target.stat().st_ino, cache_inode)
        self.assertTrue((target.parents[2] / reapply.OVERLAY_NAME).is_file())

    def test_missing_opencode_runtime_fails_before_bwrap(self) -> None:
        executable = self._fake_cli("opencode", {"type": "text", "text": "mock"})
        with self.assertRaisesRegex(RuntimeError, "missing required backend state"):
            self._args("opencode", executable)

    def test_exact_executable_rebind_is_the_final_bind_after_all_writable_mounts(self) -> None:
        executable = self._nested_fake_cli(".codex/bin/codex", {"type": "response.output_text.done", "text": "mock"})
        extra = self.root / "extra"
        extra.mkdir()
        old = os.environ.get("CODEX_BIN")
        os.environ["CODEX_BIN"] = str(executable)
        try:
            args = self.overlay.bwrap_prefix(self.work, backend="codex", home=self.home, extra_writable=[extra])
        finally:
            if old is None:
                os.environ.pop("CODEX_BIN", None)
            else:
                os.environ["CODEX_BIN"] = old
        bind_indices = [index for index, value in enumerate(args) if value in {"--bind", "--ro-bind"}]
        last_bind = bind_indices[-1]
        self.assertEqual(args[last_bind:last_bind + 3], ["--ro-bind", str(executable.resolve()), str(executable.resolve())])

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap unavailable")
    def test_bwrap_rebinds_executables_below_work_and_extra_writable_ancestors(self) -> None:
        code = (
            "from pathlib import Path; import subprocess, sys; "
            "from gepa.oa.sandbox import bwrap_prefix; "
            "backend=sys.argv[3]; command_var='CODEX_BIN' if backend == 'codex' else 'OPENCODE_BIN'; "
            "extra=[Path(sys.argv[4])] if sys.argv[4] else []; "
            "a=bwrap_prefix(sys.argv[1], backend=backend, home=Path(sys.argv[2]), extra_writable=extra); "
            f"r=subprocess.run(a+['sh','-c',f'test ! -w \"${{command_var}}\" && command -v {AGENT_ENTRY} && {AGENT_ENTRY} --print probe'],capture_output=True,text=True); "
            "print(r.stdout, end=''); print(r.stderr, end='', file=sys.stderr); raise SystemExit(r.returncode)"
        )
        for backend in ("codex", "opencode"):
            if backend == "opencode":
                (self.home / ".opencode").mkdir()
            for ancestor_kind, ancestor in (("work", self.work), ("extra", self.root / "extra")):
                ancestor.mkdir(exist_ok=True)
                executable = self._fake_cli_at(
                    ancestor / "nested" / "bin" / backend,
                    {"type": "response.output_text.done" if backend == "codex" else "text", "text": f"mock-{backend}-{ancestor_kind}"},
                )
                env_name = "CODEX_BIN" if backend == "codex" else "OPENCODE_BIN"
                env = {**os.environ, "GEPA_SKILL_ROOT": str(ROOT), env_name: str(executable)}
                completed = subprocess.run(
                    [str(PYTHON), "-c", code, str(self.work), str(self.home), backend, str(ancestor) if ancestor_kind == "extra" else ""],
                    env=env,
                    capture_output=True,
                    check=False,
                    text=True,
                )
                with self.subTest(backend=backend, ancestor=ancestor_kind):
                    self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                    self.assertIn(f"/{AGENT_ENTRY}", completed.stdout)
                    self.assertIn(f"mock-{backend}-{ancestor_kind}", completed.stdout)

    def test_fresh_interpreter_rebinds_both_real_agentic_callers(self) -> None:
        code = (
            "from gepa.oa import sandbox; from gepa.oa.engines import autoresearch, meta_harness; "
            "assert sandbox.GEPA_SKILL_BACKEND_OVERLAY == 'GEPA_SKILL_BACKEND_OVERLAY_V4'; "
            "assert sandbox.bwrap_prefix.__module__ == 'gepa_skill_backend_sandbox_overlay'; "
            "assert autoresearch.bwrap_prefix is sandbox.bwrap_prefix; "
            "assert meta_harness.bwrap_prefix is sandbox.bwrap_prefix; "
            "assert sandbox.preflight_claude_engine.__name__ == 'preflight_agent_engine'; "
            "print('caller aliases patched')"
        )
        completed = subprocess.run(
            [str(PYTHON), "-c", code],
            env={**os.environ, "GEPA_SKILL_ROOT": str(ROOT)},
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("caller aliases patched", completed.stdout)

    def test_preflight_reports_selected_backend_without_cross_backend_state(self) -> None:
        executable = self._fake_cli("codex", {"type": "response.output_text.done", "text": "mock"})
        env = {
            **os.environ,
            "HOME": str(self.home),
            "GEPA_AGENT_BACKEND": "codex",
            "CODEX_BIN": str(executable),
            "PATH": f"{ROOT / 'bin'}:{os.environ['PATH']}",
        }
        completed = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts/preflight.py"), "--engine", "meta_harness"],
            env=env,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertNotIn(".opencode", completed.stdout)
        self.assertIn("Codex sandbox state", completed.stdout)

    def test_preflight_delegates_from_an_arbitrary_python_launcher(self) -> None:
        """A non-skill launcher forwards its args/environment in one hop."""
        launcher = next(
            (
                Path(candidate)
                for candidate in (shutil.which("python3"), shutil.which("python"), "/usr/bin/python3")
                if candidate
                and Path(candidate).is_file()
                and not Path(candidate).samefile(PYTHON)
            ),
            None,
        )
        if launcher is None:
            launcher = self.root / "python-outside-skill"
            launcher.symlink_to(PYTHON)
        (self.home / ".opencode").mkdir()
        executable = self._fake_cli("opencode", {"type": "text", "text": "mock"})
        env = {
            **os.environ,
            "HOME": str(self.home),
            "GEPA_AGENT_BACKEND": "opencode",
            "OPENCODE_BIN": str(executable),
            "PATH": f"{ROOT / 'bin'}:{os.environ['PATH']}",
        }
        completed = subprocess.run(
            [str(launcher), str(ROOT / "scripts/preflight.py"), "--engine", "meta_harness"],
            env=env,
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stderr.count("delegating preflight to skill runtime"), 1)
        self.assertIn("Opencode CLI on PATH (required by meta_harness)", completed.stdout)
        self.assertNotIn("`jq` on PATH", completed.stdout)
        self.assertIn("All preflight checks passed", completed.stdout)

    def test_preflight_rejects_an_invalid_runtime_handoff_marker(self) -> None:
        completed = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts/preflight.py"), "--engine", "meta_harness"],
            env={**os.environ, "_GEPA_SKILL_PREFLIGHT_RUNTIME": "not-the-skill-runtime"},
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("invalid preflight runtime handoff marker", completed.stderr)

    def test_preflight_handoff_sets_validated_marker_and_preserves_environment_and_args(self) -> None:
        """The one-hop exec keeps caller context while adding its private marker."""
        preflight = load_preflight()
        sentinel = "preserve-me"
        observed: dict[str, object] = {}

        class Handoff(Exception):
            pass

        def capture(path, argv, environment):
            observed.update(path=path, argv=argv, environment=environment)
            raise Handoff

        expected = preflight._skill_python().absolute()
        prior_marker = os.environ.pop(preflight._RUNTIME_MARKER, None)
        previous_argv = sys.argv
        try:
            os.environ["GEPA_PREFLIGHT_TEST_SENTINEL"] = sentinel
            sys.argv = [str(PREFLIGHT), "--engine", "meta_harness"]
            with (
                patch.object(preflight.sys, "executable", str(self.root / "outside-python")),
                patch.object(preflight.os, "execve", side_effect=capture),
                redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(Handoff):
                    preflight._run_in_skill_runtime()
        finally:
            sys.argv = previous_argv
            os.environ.pop("GEPA_PREFLIGHT_TEST_SENTINEL", None)
            if prior_marker is not None:
                os.environ[preflight._RUNTIME_MARKER] = prior_marker
        self.assertEqual(observed["path"], str(expected))
        self.assertEqual(observed["argv"], [str(expected), str(PREFLIGHT), "--engine", "meta_harness"])
        environment = observed["environment"]
        self.assertEqual(environment[preflight._RUNTIME_MARKER], str(expected))
        self.assertEqual(environment["GEPA_PREFLIGHT_TEST_SENTINEL"], sentinel)


if __name__ == "__main__":
    unittest.main()
