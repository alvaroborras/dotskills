from __future__ import annotations

import argparse
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import campaign_state


class CampaignStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.contract_path = self.project / "metric.json"
        self.contract_path.write_text(
            json.dumps(
                {
                    "name": "score",
                    "unit": "points",
                    "direction": "higher",
                    "aggregation": "sum",
                    "denominator": 10,
                    "verifier": {"command": ["verify"]},
                    "parser": {"format": "json", "field": "metric"},
                    "suite": {"id": "dev-v1", "input_hash": "inputs-v1"},
                    "backend": "official",
                    "environment": {"workers": 1},
                    "comparator": {"policy": "paired-canonical"},
                    "minimum_improvement": {"absolute": 1, "relative": 0},
                    "noise_policy": {"repetitions": 1},
                    "constraints": {"guards_required": True},
                    "evidence_stages": [
                        "smoke",
                        "screen",
                        "independent",
                        "canonical",
                        "promotion-audit",
                    ],
                    "sealed_policy": {"one_shot": False},
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_campaign(
        self, name: str = "test-campaign", expected_contract_id: str | None = None
    ) -> Path:
        args = argparse.Namespace(
            project_root=str(self.project),
            campaign=name,
            goal="improve score",
            scope="src/**",
            metric_contract=str(self.contract_path),
            metric_contract_id=expected_contract_id,
            git_mode="ledger-only",
            budget_unit="candidate_snapshot",
            iterations=3,
            actor="test",
        )
        return campaign_state.init_campaign(args)

    def result_payload(
        self,
        root: Path,
        run_id: str,
        *,
        candidate_id: str | None = None,
        source_hash: str | None = None,
        metric: float = 10,
        outcome: str = "valid",
        stage: str = "canonical",
    ) -> dict[str, object]:
        contract_id = campaign_state.read_json(root / "campaign.json")[
            "metric_contract_id"
        ]
        payload: dict[str, object] = {
            "schema_version": 1,
            "run_id": run_id,
            "candidate_id": candidate_id or run_id,
            "outcome": outcome,
            "stage": stage,
            "suite": "dev",
            "backend": "official",
            "metric_contract_id": contract_id,
            "harness_hash": "harness-v1",
            "input_hash": "inputs-v1",
            "environment_hash": "env-v1",
            "concurrency_policy": "workers=1",
            "source_hash": source_hash or f"source-{run_id}",
            "coverage": {"expected": 10, "observed": 10, "duplicate_count": 0},
            "guards": {"passed": True},
            "constraints": {"passed": True},
        }
        if stage in {"canonical", "promotion-audit"}:
            payload["resource_key"] = "official-canonical"
        if outcome == "valid":
            payload["metric"] = metric
        return payload

    def register(
        self,
        root: Path,
        run_id: str,
        *,
        stage: str = "screen",
        epoch: int = 1,
        candidate_id: str | None = None,
        source_hash: str | None = None,
        resource_key: str = "official-canonical",
    ) -> dict[str, object]:
        campaign = campaign_state.read_json(root / "campaign.json")
        manifest: dict[str, object] = {
            "schema_version": 1,
            "run_id": run_id,
            "campaign_id": campaign["campaign_id"],
            "authorization_epoch": epoch,
            "experiment_id": f"experiment-{run_id}",
            "evaluation_id": f"evaluation-{run_id}",
            "candidate_id": candidate_id or run_id,
            "stage": stage,
            "suite": "dev",
            "backend": "official",
            "metric_contract_id": campaign["metric_contract_id"],
            "working_directory": str(self.project),
            "command": ["verify"],
            "environment": {},
            "concurrency_policy": "workers=1",
            "worker_count": 1,
            "timeouts": {"wall_seconds": 60},
            "hashes": {
                "source": source_hash or f"source-{run_id}",
                "build": "build-v1",
                "harness": "harness-v1",
                "suite": "suite-v1",
                "inputs": "inputs-v1",
                "configuration": "config-v1",
                "toolchain": "toolchain-v1",
                "environment": "env-v1",
            },
            "expected_outputs": ["result.json"],
            "lifecycle": "QUEUED",
            "artifacts": {},
        }
        if stage in {"canonical", "promotion-audit"}:
            manifest["resource_key"] = resource_key
        return campaign_state.register_run(root, manifest, "test")

    def queue_and_finish(
        self, root: Path, run_id: str, payload: dict[str, object], epoch: int = 1
    ) -> None:
        self.register(
            root,
            run_id,
            stage=str(payload["stage"]),
            epoch=epoch,
            candidate_id=str(payload["candidate_id"]),
            source_hash=str(payload["source_hash"]),
            resource_key=str(payload.get("resource_key", "official-canonical")),
        )
        campaign_state.append_event(
            root,
            "evaluation_finished",
            payload,
            "test",
            event_epoch=epoch,
        )

    def test_namespaces_are_isolated_and_append_only(self) -> None:
        first = self.create_campaign("first")
        second = self.create_campaign("second")
        campaign_state.append_event(
            first,
            "hypothesis_added",
            {"hypothesis": "cache parser", "status": "active"},
            "test",
            event_epoch=1,
        )
        self.assertEqual(len(campaign_state.load_events(first)), 2)
        self.assertEqual(len(campaign_state.load_events(second)), 1)
        self.assertIn("cache parser", (first / "views" / "ideas.md").read_text())
        self.assertNotIn("cache parser", (second / "views" / "ideas.md").read_text())

    def test_stop_blocks_launch_and_quarantines_old_epoch_completion(self) -> None:
        root = self.create_campaign()
        campaign_state.append_event(
            root,
            "stop_requested",
            {"reason": "user", "policy": "cancel-active"},
            "test",
            event_epoch=1,
        )
        with self.assertRaises(PermissionError):
            self.register(root, "late", stage="screen", epoch=1)
        campaign_state.append_event(
            root, "stopped", {"reason": "user"}, "test", event_epoch=1
        )
        authorization = campaign_state.authorize(
            root, "user requested resume", "user", "conversation:test-resume"
        )
        self.assertEqual(authorization["authorization_epoch"], 2)
        late = campaign_state.append_event(
            root,
            "evaluation_finished",
            self.result_payload(root, "stale-completion", outcome="cancelled"),
            "test",
            event_epoch=1,
        )
        self.assertEqual(late["event_type"], "late_evaluation_observed")
        queued = self.register(root, "new-epoch", stage="screen", epoch=2)
        self.assertEqual(queued["authorization_epoch"], 2)
        self.assertEqual(campaign_state.current_state(root)["lifecycle"], "RUNNING")

    def test_terminal_transition_requires_reconciled_runs(self) -> None:
        root = self.create_campaign()
        self.register(root, "active", stage="screen", epoch=1)
        campaign_state.append_event(
            root,
            "stop_requested",
            {"reason": "user", "policy": "cancel-active"},
            "test",
            event_epoch=1,
        )
        with self.assertRaises(PermissionError):
            campaign_state.append_event(
                root, "stopped", {"reason": "user"}, "test", event_epoch=1
            )
        self.queue_terminal_only(root, "active", outcome="cancelled")
        campaign_state.append_event(
            root, "stopped", {"reason": "user"}, "test", event_epoch=1
        )

    def queue_terminal_only(self, root: Path, run_id: str, *, outcome: str) -> None:
        campaign_state.append_event(
            root,
            "evaluation_finished",
            self.result_payload(root, run_id, outcome=outcome, stage="screen"),
            "test",
            event_epoch=1,
        )

    def test_paused_campaign_allows_only_active_run_reconciliation(self) -> None:
        root = self.create_campaign()
        self.register(root, "pause-active", stage="screen")
        campaign_state.append_event(
            root, "paused", {"reason": "operator"}, "test", event_epoch=1
        )
        with self.assertRaises(PermissionError):
            self.register(root, "pause-new", stage="screen")
        self.queue_terminal_only(root, "pause-active", outcome="valid")
        self.assertEqual(campaign_state.current_state(root)["active_run_ids"], [])
        self.assertEqual(
            campaign_state.authorize(
                root, "resume after pause", "user", "conversation:test-pause"
            )["authorization_epoch"],
            2,
        )

    def test_complete_can_be_explicitly_reauthorized(self) -> None:
        root = self.create_campaign()
        campaign_state.append_event(
            root, "completed", {"reason": "budget"}, "test", event_epoch=1
        )
        with self.assertRaises(PermissionError):
            self.register(root, "blocked", stage="screen", epoch=1)
        self.assertEqual(
            campaign_state.authorize(
                root, "new user request", "user", "conversation:test-complete"
            )["authorization_epoch"],
            2,
        )

    def test_canonical_lease_is_shared_across_campaigns(self) -> None:
        first = self.create_campaign("lease-first")
        second = self.create_campaign("lease-second")
        self.register(
            first,
            "canonical-one",
            stage="canonical",
            resource_key="gpu-0-official-suite",
        )
        with self.assertRaises(FileExistsError):
            self.register(
                second,
                "canonical-two",
                stage="canonical",
                resource_key="gpu-0-official-suite",
            )
        result = self.result_payload(first, "canonical-one")
        result["resource_key"] = "gpu-0-official-suite"
        campaign_state.append_event(
            first, "evaluation_finished", result, "test", event_epoch=1
        )
        self.register(
            second,
            "canonical-two",
            stage="canonical",
            resource_key="gpu-0-official-suite",
        )

    def test_promotion_lineage_controls_verified_keep(self) -> None:
        root = self.create_campaign()
        comparator = self.result_payload(
            root,
            "baseline-run",
            candidate_id="baseline",
            source_hash="baseline-source",
            metric=10,
        )
        comparator["role"] = "baseline"
        candidate = self.result_payload(
            root,
            "candidate-run",
            candidate_id="candidate",
            source_hash="candidate-source",
            metric=12,
        )
        self.queue_and_finish(root, "baseline-run", comparator)
        for stage in ("smoke", "screen", "independent"):
            stage_run = f"candidate-{stage}"
            stage_result = self.result_payload(
                root,
                stage_run,
                candidate_id="candidate",
                source_hash="candidate-source",
                metric=12,
                stage=stage,
            )
            self.queue_and_finish(root, stage_run, stage_result)
        self.queue_and_finish(root, "candidate-run", candidate)
        promotion_audit = self.result_payload(
            root,
            "candidate-promotion-audit",
            candidate_id="candidate",
            source_hash="candidate-source",
            metric=12,
            stage="promotion-audit",
        )
        self.queue_and_finish(root, "candidate-promotion-audit", promotion_audit)
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root,
                "promotion_verified",
                {
                    "candidate_run_id": "candidate-run",
                    "comparator_run_id": "candidate-run",
                    "promotion_audit_run_id": "candidate-promotion-audit",
                    "promoted_source_hash": "candidate-source",
                    "coverage_complete": True,
                    "no_duplicate_cases": True,
                    "guards_passed": True,
                    "constraints_passed": True,
                    "reproducible_build": True,
                    "threshold_passed": True,
                    "parent_owned": True,
                },
                "test",
                event_epoch=1,
            )
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root,
                "decision_recorded",
                {
                    "decision": "verified-keep",
                    "candidate_run_id": "candidate-run",
                    "reason": "too early",
                },
                "test",
                event_epoch=1,
            )
        campaign_state.append_event(
            root,
            "promotion_verified",
            {
                "candidate_run_id": "candidate-run",
                "comparator_run_id": "baseline-run",
                "promotion_audit_run_id": "candidate-promotion-audit",
                "promoted_source_hash": "candidate-source",
                "coverage_complete": True,
                "no_duplicate_cases": True,
                "guards_passed": True,
                "constraints_passed": True,
                "reproducible_build": True,
                "threshold_passed": True,
                "parent_owned": True,
            },
            "test",
            event_epoch=1,
        )
        campaign_state.append_event(
            root,
            "decision_recorded",
            {
                "iteration_id": "1",
                "experiment_id": "candidate",
                "decision": "verified-keep",
                "candidate_run_id": "candidate-run",
                "reason": "promotion audit passed",
            },
            "test",
            event_epoch=1,
        )
        state = (root / "views" / "state.md").read_text(encoding="utf-8")
        self.assertIn("baseline: 10 (baseline-run)", state)
        self.assertIn("incumbent: 12 (candidate-run)", state)

    def test_accepted_zero_is_valid_and_failures_cannot_carry_metrics(self) -> None:
        root = self.create_campaign()
        zero = self.result_payload(root, "zero", metric=0, stage="screen")
        self.queue_and_finish(root, "zero", zero)
        self.register(root, "timeout", stage="screen")
        invalid = self.result_payload(
            root, "timeout", metric=0, outcome="wall_timeout", stage="screen"
        )
        invalid["metric"] = 0
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root,
                "evaluation_finished",
                invalid,
                "test",
                event_epoch=1,
            )

    def test_nonfinite_result_fails_closed(self) -> None:
        root = self.create_campaign()
        self.register(root, "nan", stage="screen")
        payload = self.result_payload(root, "nan", metric=float("nan"), stage="screen")
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root, "evaluation_finished", payload, "test", event_epoch=1
            )

    def test_metric_contract_identity_is_derived_and_mismatch_fails(self) -> None:
        root = self.create_campaign()
        campaign = campaign_state.read_json(root / "campaign.json")
        self.assertTrue(campaign["metric_contract_id"].startswith("sha256:"))
        with self.assertRaises(ValueError):
            self.create_campaign(
                "mismatch", expected_contract_id="sha256:not-the-digest"
            )
        self.assertFalse(campaign_state.campaign_dir(self.project, "mismatch").exists())

    def test_legacy_migration_is_atomic_and_rejects_symlinks(self) -> None:
        root = self.create_campaign()
        source = self.project / "autoresearch-state.md"
        source.write_text("legacy\n", encoding="utf-8")
        before = campaign_state.sha256_file(source)
        campaign_state.migrate_legacy(root, self.project, "test")
        self.assertEqual(campaign_state.sha256_file(source), before)
        self.assertEqual((root / "legacy" / source.name).read_text(), "legacy\n")

        other = self.create_campaign("symlink-migration")
        (self.project / "autoresearch-results.tsv").symlink_to(source)
        with self.assertRaises(PermissionError):
            campaign_state.migrate_legacy(other, self.project, "test")
        self.assertFalse((other / "legacy").exists())

    def test_gc_dry_run_hash_checks_and_permanent_retention(self) -> None:
        root = self.create_campaign()
        old = (dt.datetime.now(dt.UTC) - dt.timedelta(days=20)).isoformat()
        disposable = root / "artifacts" / "screen-old"
        disposable.mkdir()
        (disposable / "payload.txt").write_text("large output", encoding="utf-8")
        (disposable / "artifact.json").write_text(
            json.dumps(
                {
                    "retention_class": "screen",
                    "created_at": old,
                    "referenced": False,
                    "active": False,
                    "sha256": campaign_state.sha256_artifact(disposable),
                }
            ),
            encoding="utf-8",
        )
        permanent = root / "artifacts" / "promoted"
        permanent.mkdir()
        (permanent / "artifact.json").write_text(
            json.dumps(
                {
                    "retention_class": "promoted",
                    "created_at": old,
                    "referenced": True,
                    "active": False,
                }
            ),
            encoding="utf-8",
        )
        candidates = campaign_state.gc_candidates(root, dt.datetime.now(dt.UTC))
        self.assertEqual(
            [Path(item["path"]).name for item in candidates], ["screen-old"]
        )
        self.assertTrue(disposable.exists())
        with (
            mock.patch.object(
                campaign_state.shutil, "rmtree", side_effect=OSError("fault")
            ),
            self.assertRaises(OSError),
        ):
            campaign_state.run_gc(root, apply=True)
        self.assertFalse(disposable.exists())
        started = campaign_state.load_events(root)[-1]
        self.assertEqual(started["event_type"], "garbage_collection_delete_committed")
        started_event_id = started["payload"]["started_event_id"]
        quarantine = root / "gc-quarantine" / started_event_id / "screen-old"
        self.assertTrue(quarantine.exists())
        campaign_state.recover_gc(root, started_event_id, "test")
        self.assertTrue(disposable.exists())
        campaign_state.run_gc(root, apply=True)
        self.assertFalse(disposable.exists())
        self.assertTrue(permanent.exists())

    def test_gc_finalize_reconciles_crash_after_committed_deletion(self) -> None:
        root = self.create_campaign("gc-finalize")
        old = (dt.datetime.now(dt.UTC) - dt.timedelta(days=20)).isoformat()
        artifact = root / "artifacts" / "failed-old"
        artifact.mkdir()
        (artifact / "payload.txt").write_text("failed", encoding="utf-8")
        (artifact / "artifact.json").write_text(
            json.dumps(
                {
                    "retention_class": "failed",
                    "created_at": old,
                    "referenced": False,
                    "active": False,
                    "sha256": campaign_state.sha256_artifact(artifact),
                }
            ),
            encoding="utf-8",
        )
        with (
            mock.patch.object(
                campaign_state.shutil, "rmtree", side_effect=OSError("fault")
            ),
            self.assertRaises(OSError),
        ):
            campaign_state.run_gc(root, apply=True)
        committed = campaign_state.load_events(root)[-1]
        started_event_id = committed["payload"]["started_event_id"]
        quarantine_root = root / "gc-quarantine" / started_event_id
        campaign_state.shutil.rmtree(quarantine_root)
        artifact.mkdir()
        with self.assertRaises(PermissionError):
            campaign_state.recover_gc(root, started_event_id, "test", mode="finalize")
        artifact.rmdir()
        finalized = campaign_state.recover_gc(
            root, started_event_id, "test", mode="finalize"
        )
        self.assertEqual(finalized["event_type"], "garbage_collection_finalized")
        self.assertFalse(artifact.exists())

    def test_gc_preserves_ledger_references_and_rejects_symlinks(self) -> None:
        root = self.create_campaign()
        old = (dt.datetime.now(dt.UTC) - dt.timedelta(days=20)).isoformat()
        referenced = root / "artifacts" / "referenced-screen"
        referenced.mkdir()
        (referenced / "payload.txt").write_text("evidence", encoding="utf-8")
        (referenced / "artifact.json").write_text(
            json.dumps(
                {
                    "retention_class": "screen",
                    "created_at": old,
                    "referenced": False,
                    "active": False,
                    "sha256": campaign_state.sha256_artifact(referenced),
                }
            ),
            encoding="utf-8",
        )
        campaign_state.append_event(
            root,
            "hypothesis_added",
            {
                "hypothesis": "retain",
                "artifact": "artifacts/referenced-screen/payload.txt",
            },
            "test",
            event_epoch=1,
        )
        self.assertEqual(
            campaign_state.gc_candidates(root, dt.datetime.now(dt.UTC)), []
        )

        outside = self.project / "outside-artifact"
        outside.mkdir()
        (root / "artifacts" / "linked").symlink_to(outside, target_is_directory=True)
        (outside / "artifact.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(PermissionError):
            campaign_state.gc_candidates(root, dt.datetime.now(dt.UTC))

    def test_malformed_manifest_types_fail_before_queue(self) -> None:
        root = self.create_campaign()
        self.register(root, "template", stage="screen")
        template = campaign_state.read_json(
            root / "runs" / "template" / "manifest.json"
        )
        template.update(
            {
                "run_id": "bad-manifest",
                "experiment_id": "bad-experiment",
                "evaluation_id": "bad-evaluation",
                "candidate_id": "bad-candidate",
            }
        )
        template.pop("concurrency_policy")
        with self.assertRaises(ValueError):
            campaign_state.register_run(root, template, "test")
        template["concurrency_policy"] = "workers=1"
        template["hashes"]["source"] = 123
        with self.assertRaises(ValueError):
            campaign_state.register_run(root, template, "test")
        self.assertFalse((root / "runs" / "bad-manifest").exists())

    def test_malformed_result_objects_fail_before_terminal_event(self) -> None:
        root = self.create_campaign()
        self.register(root, "bad-shape", stage="screen")
        payload = self.result_payload(root, "bad-shape", stage="screen")
        payload["coverage"] = []
        with self.assertRaises(TypeError):
            campaign_state.append_event(
                root, "evaluation_finished", payload, "test", event_epoch=1
            )
        payload = self.result_payload(root, "bad-shape", stage="screen")
        payload["schema_version"] = True
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root, "evaluation_finished", payload, "test", event_epoch=1
            )
        payload = self.result_payload(root, "bad-shape", stage="screen")
        payload["coverage"] = {
            "expected": False,
            "observed": 0,
            "duplicate_count": 0,
        }
        with self.assertRaises(TypeError):
            campaign_state.append_event(
                root, "evaluation_finished", payload, "test", event_epoch=1
            )
        self.assertIn("bad-shape", campaign_state.current_state(root)["active_run_ids"])

    def test_registration_and_migration_roll_back_uncommitted_files(self) -> None:
        root = self.create_campaign()
        with (
            mock.patch.object(
                campaign_state, "append_event_unlocked", side_effect=OSError("fault")
            ),
            self.assertRaises(OSError),
        ):
            self.register(root, "registration-fault", stage="canonical")
        self.assertFalse((root / "runs" / "registration-fault").exists())
        self.assertEqual(
            list((self.project / ".autoresearch" / "locks").glob("canonical-*")), []
        )

        source = self.project / "autoresearch-state.md"
        source.write_text("legacy\n", encoding="utf-8")
        with (
            mock.patch.object(
                campaign_state, "append_event_unlocked", side_effect=OSError("fault")
            ),
            self.assertRaises(OSError),
        ):
            campaign_state.migrate_legacy(root, self.project, "test")
        self.assertFalse((root / "legacy").exists())
        self.assertEqual(source.read_text(encoding="utf-8"), "legacy\n")

    def test_missing_canonical_lease_blocks_terminal_commit(self) -> None:
        root = self.create_campaign()
        self.register(root, "missing-lease", stage="canonical")
        lease = campaign_state.canonical_lease_path(root, "official-canonical")
        lease.unlink()
        before = len(campaign_state.load_events(root))
        with self.assertRaises(FileNotFoundError):
            campaign_state.append_event(
                root,
                "evaluation_finished",
                self.result_payload(root, "missing-lease"),
                "test",
                event_epoch=1,
            )
        self.assertEqual(len(campaign_state.load_events(root)), before)

    def test_old_epoch_evidence_cannot_be_promoted(self) -> None:
        root = self.create_campaign()
        baseline = self.result_payload(
            root,
            "epoch-baseline",
            candidate_id="baseline",
            source_hash="baseline",
            metric=10,
        )
        baseline["role"] = "baseline"
        self.queue_and_finish(root, "epoch-baseline", baseline)
        for stage in ("smoke", "screen", "independent", "canonical", "promotion-audit"):
            run_id = f"epoch-candidate-{stage}"
            result = self.result_payload(
                root,
                run_id,
                candidate_id="candidate",
                source_hash="candidate",
                metric=12,
                stage=stage,
            )
            self.queue_and_finish(root, run_id, result)
        campaign_state.append_event(
            root, "completed", {"reason": "budget"}, "test", event_epoch=1
        )
        campaign_state.authorize(
            root, "new epoch", "user", "conversation:cross-epoch-test"
        )
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root,
                "promotion_verified",
                {
                    "candidate_run_id": "epoch-candidate-canonical",
                    "comparator_run_id": "epoch-baseline",
                    "promotion_audit_run_id": "epoch-candidate-promotion-audit",
                    "promoted_source_hash": "candidate",
                    "coverage_complete": True,
                    "no_duplicate_cases": True,
                    "guards_passed": True,
                    "constraints_passed": True,
                    "reproducible_build": True,
                    "threshold_passed": True,
                    "parent_owned": True,
                },
                "test",
                event_epoch=2,
            )

    def test_manifest_is_sealed_and_tampering_blocks_result(self) -> None:
        root = self.create_campaign()
        self.register(root, "tamper", stage="screen")
        manifest = root / "runs" / "tamper" / "manifest.json"
        self.assertEqual(manifest.stat().st_mode & 0o222, 0)
        manifest.chmod(0o644)
        manifest.write_text(manifest.read_text() + " ", encoding="utf-8")
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root,
                "evaluation_finished",
                self.result_payload(root, "tamper", stage="screen"),
                "test",
                event_epoch=1,
            )

    def test_unknown_events_and_symlinked_campaigns_fail_closed(self) -> None:
        root = self.create_campaign()
        with self.assertRaises(ValueError):
            campaign_state.append_event(
                root, "invented_success", {}, "test", event_epoch=1
            )
        alias = self.project / "campaign-alias"
        alias.symlink_to(root, target_is_directory=True)
        with self.assertRaises((PermissionError, ValueError)):
            campaign_state.append_event(
                alias,
                "hypothesis_added",
                {"hypothesis": "must not follow alias"},
                "test",
                event_epoch=1,
            )

    def test_corrupt_ledger_fails_closed(self) -> None:
        root = self.create_campaign()
        ledger = root / "events.jsonl"
        original = ledger.read_text(encoding="utf-8")
        first = json.loads(original)
        ledger.write_text(original + json.dumps(first) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            campaign_state.load_events(root)

    def test_truncated_ledger_fails_head_receipt(self) -> None:
        root = self.create_campaign("truncated")
        campaign_state.append_event(
            root,
            "hypothesis_added",
            {"hypothesis": "second event"},
            "test",
            event_epoch=1,
        )
        ledger = root / "events.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
        ledger.write_text("".join(lines[:-1]), encoding="utf-8")
        with self.assertRaises(ValueError):
            campaign_state.load_events(root)

    def test_invalid_campaign_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            campaign_state.validate_campaign_id("../escape")


if __name__ == "__main__":
    unittest.main()
