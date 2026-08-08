from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import codex_runtime


class CodexBridgeTests(unittest.TestCase):
    def test_gepa_config_gets_parallel_proposal_defaults(self) -> None:
        try:
            from gepa.optimize_anything import OptimizeAnythingConfig
            from gepa.strategies.proposal_sampling import PxNSampling
            from gepa.strategies.proposal_selection import AllImprovements
        except ImportError:
            self.skipTest("the optional GEPA runtime is not installed")

        codex_runtime._patch_config_defaults()
        config = OptimizeAnythingConfig()
        engine_options = config.engine_config["engine"]
        sampling = engine_options["sampling_strategy"]
        self.assertIsInstance(sampling, PxNSampling)
        self.assertEqual((sampling.p, sampling.n), (2, 2))
        self.assertIsInstance(engine_options["selection_strategy"], AllImprovements)

    def test_explicit_gepa_proposal_strategies_are_preserved(self) -> None:
        try:
            from gepa.optimize_anything import OptimizeAnythingConfig
            from gepa.strategies.proposal_sampling import SameParentSampling
            from gepa.strategies.proposal_selection import BestImprovement
        except ImportError:
            self.skipTest("the optional GEPA runtime is not installed")

        codex_runtime._patch_config_defaults()
        sampling = SameParentSampling(n=3)
        selection = BestImprovement()
        config = OptimizeAnythingConfig(
            engine_config={
                "engine": {
                    "sampling_strategy": sampling,
                    "selection_strategy": selection,
                }
            }
        )
        engine_options = config.engine_config["engine"]
        self.assertIs(engine_options["sampling_strategy"], sampling)
        self.assertIs(engine_options["selection_strategy"], selection)

    def test_command_rewrites_to_absolute_skill_entrypoint(self) -> None:
        command, environment = codex_runtime.rewrite_command(
            [
                "legacy-agent",
                "--print",
                "Read .hidden/skills/gepa-optimize-anything-meta-harness/SKILL.md",
            ]
        )
        self.assertEqual(
            Path(command[0]).resolve(), (ROOT / "bin" / "gepa-agent").resolve()
        )
        self.assertIn(
            ".codex/skills/gepa-optimize-anything-meta-harness/SKILL.md", command[-1]
        )
        self.assertEqual(environment["GEPA_SKILL_ROOT"], str(ROOT))

    def test_non_agent_commands_are_unchanged(self) -> None:
        command, environment = codex_runtime.rewrite_command(["printf", "hello"])
        self.assertEqual(command, ["printf", "hello"])
        self.assertIsNone(environment)

    def test_no_process_prefix_and_permission_arguments(self) -> None:
        self.assertEqual(codex_runtime.no_process_prefix("work"), [])
        self.assertEqual(
            codex_runtime.permission_args(), ["--permission-mode", "bypassPermissions"]
        )

    def test_shim_invokes_codex_and_normalizes_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            argv_file = root / "argv.json"
            fake = root / "fake-codex.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                f"pathlib.Path({str(argv_file)!r}).write_text(json.dumps(sys.argv[1:]))\n"
                "print(json.dumps({'type': 'response.output_text.done', 'text': 'improved candidate'}))\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            environment = {
                **os.environ,
                "CODEX_BIN": str(fake),
                "GEPA_CODEX_MODEL": "gpt-test",
                "GEPA_REASONING_EFFORT": "medium",
            }
            result = subprocess.run(
                [
                    str(ROOT / "bin" / "gepa-agent"),
                    "--print",
                    "--output-format",
                    "json",
                    "--model",
                    "ignored",
                    "--session-id",
                    "session",
                    "--permission-mode",
                    "bypassPermissions",
                    "--effort",
                    "low",
                    "improve the candidate",
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            envelope = json.loads(result.stdout)
            self.assertEqual(envelope["type"], "result")
            self.assertEqual(envelope["result"], "improved candidate")
            invoked = json.loads(argv_file.read_text(encoding="utf-8"))
            self.assertEqual(invoked[0:2], ["exec", "--json"])
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", invoked)
            self.assertIn("gpt-test", invoked)
            self.assertIn("model_reasoning_effort=medium", invoked)


if __name__ == "__main__":
    unittest.main()
