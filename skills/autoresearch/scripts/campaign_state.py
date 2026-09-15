#!/usr/bin/env python3
"""Create and maintain namespaced autoresearch campaign state.

The event ledger is authoritative. Markdown and TSV files under ``views/`` are
regenerated projections. This helper deliberately does not run benchmarks or
make Git changes.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
LIFECYCLES = {"RUNNING", "PAUSED", "STOP_REQUESTED", "STOPPED", "COMPLETE"}
VALID_OUTCOMES = {
    "valid",
    "build_error",
    "crash",
    "cpu_timeout",
    "wall_timeout",
    "parse_error",
    "checker_rejection",
    "infrastructure_error",
    "cancelled",
    "stale",
}
VALID_DECISIONS = {
    "provisional",
    "verified-keep",
    "discard",
    "inconclusive",
    "deferred",
    "superseded",
    "stopped",
}
EVIDENCE_STAGES = {"smoke", "screen", "independent", "canonical", "promotion-audit"}
KNOWN_EVENTS = {
    "campaign_created",
    "authorized",
    "hypothesis_added",
    "candidate_snapshotted",
    "evaluation_queued",
    "evaluation_started",
    "evaluation_finished",
    "late_evaluation_observed",
    "decision_recorded",
    "promotion_started",
    "promotion_verified",
    "stop_requested",
    "stopped",
    "paused",
    "completed",
    "legacy_migrated",
    "garbage_collection_started",
    "garbage_collection_recovered",
    "garbage_collection_delete_committed",
    "garbage_collection_finalized",
}
LAUNCH_EVENTS = {"candidate_snapshotted", "evaluation_queued", "evaluation_started"}
WORK_EVENTS = LAUNCH_EVENTS | {
    "evaluation_finished",
    "decision_recorded",
    "promotion_started",
    "promotion_verified",
}
PROMOTION_EVENTS = {"promotion_started", "promotion_verified"}
RESULT_IDENTITY_FIELDS = {
    "candidate_id",
    "metric_contract_id",
    "suite",
    "backend",
    "harness_hash",
    "input_hash",
    "environment_hash",
    "concurrency_policy",
    "source_hash",
}
PERMANENT_RETENTION = {"permanent", "promoted", "baseline", "comparator", "sealed"}
RETENTION_DAYS = {"screen": 14, "failed": 7, "incomplete": 7}
STORAGE_WARNING_BYTES = 10 * 1024**3
LEGACY_FILES = (
    "autoresearch-results.tsv",
    "autoresearch-state.md",
    "autoresearch-decisions.tsv",
    "autoresearch-ideas.md",
)

JsonObject = dict[str, Any]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def validate_campaign_id(campaign_id: str) -> str:
    if not CAMPAIGN_ID_RE.fullmatch(campaign_id):
        raise ValueError("campaign ID must match [a-z0-9][a-z0-9._-]{0,79}")
    return campaign_id


def campaign_dir(project_root: Path, campaign_id: str) -> Path:
    return (
        project_root.resolve()
        / ".autoresearch"
        / "campaigns"
        / validate_campaign_id(campaign_id)
    )


def metric_contract_id(contract: JsonObject) -> str:
    normalized = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"


def validate_metric_contract(contract: JsonObject) -> None:
    required = {
        "name",
        "unit",
        "direction",
        "aggregation",
        "denominator",
        "verifier",
        "parser",
        "suite",
        "backend",
        "environment",
        "comparator",
        "minimum_improvement",
        "noise_policy",
        "constraints",
        "evidence_stages",
        "sealed_policy",
    }
    missing = sorted(required - contract.keys())
    if missing:
        raise ValueError(f"metric contract missing fields: {', '.join(missing)}")
    if contract["direction"] not in {"higher", "lower"}:
        raise ValueError("metric direction must be 'higher' or 'lower'")
    denominator = contract["denominator"]
    if isinstance(denominator, bool) or not isinstance(denominator, (int, float)):
        raise TypeError("metric denominator must be numeric")
    if not math.isfinite(float(denominator)) or float(denominator) <= 0:
        raise ValueError("metric denominator must be finite and positive")
    threshold = contract["minimum_improvement"]
    if not isinstance(threshold, dict):
        raise TypeError("minimum_improvement must be an object")
    for name in ("absolute", "relative"):
        value = threshold.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"minimum_improvement.{name} must be numeric")
        if not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError(
                f"minimum_improvement.{name} must be finite and nonnegative"
            )
    stages = contract["evidence_stages"]
    if not isinstance(stages, list) or not {
        "smoke",
        "screen",
        "independent",
        "canonical",
        "promotion-audit",
    }.issubset(stages):
        raise ValueError("metric contract must define the complete evidence ladder")


def read_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    if path.name == "campaign.json":
        validate_campaign_record(value)
    return value


def validate_campaign_record(campaign: JsonObject) -> None:
    required = {
        "schema_version",
        "campaign_id",
        "created_at",
        "authorization_epoch",
        "lifecycle",
        "goal",
        "scope",
        "git_mode",
        "iteration_policy",
        "metric_contract_id",
        "metric_contract",
        "artifact_policy",
    }
    missing = sorted(required - campaign.keys())
    if missing:
        raise ValueError(f"campaign record missing fields: {', '.join(missing)}")
    if (
        not isinstance(campaign["schema_version"], int)
        or isinstance(campaign["schema_version"], bool)
        or campaign["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("unsupported campaign schema")
    validate_campaign_id(str(campaign["campaign_id"]))
    if campaign["lifecycle"] not in LIFECYCLES:
        raise ValueError(f"invalid campaign lifecycle: {campaign['lifecycle']}")
    epoch = campaign["authorization_epoch"]
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise ValueError("invalid campaign authorization epoch")
    metric_contract = campaign["metric_contract"]
    if not isinstance(metric_contract, dict):
        raise TypeError("campaign metric contract must be an object")
    validate_metric_contract(metric_contract)
    if campaign["metric_contract_id"] != metric_contract_id(metric_contract):
        raise ValueError("campaign metric contract ID does not match its content")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_campaign_layout(root: Path) -> None:
    if root.is_symlink():
        raise PermissionError(f"campaign root must not be a symlink: {root}")
    if root.parent.name != "campaigns" or root.parent.parent.name != ".autoresearch":
        raise ValueError(f"campaign path is not namespaced correctly: {root}")
    for path in (
        root.parent.parent,
        root.parent,
        root,
        root / "campaign.json",
        root / "events.jsonl",
        root / "ledger-head.json",
        root / "locks",
        root / "views",
        root / "runs",
        root / "artifacts",
        root / "gc-quarantine",
    ):
        if path.exists() and path.is_symlink():
            raise PermissionError(
                f"campaign control path must not be a symlink: {path}"
            )


@contextlib.contextmanager
def campaign_lock(root: Path) -> Iterator[None]:
    validate_campaign_layout(root)
    lock_path = root / "locks" / "campaign.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def load_events(root: Path) -> list[JsonObject]:
    validate_campaign_layout(root)
    ledger = root / "events.jsonl"
    if not ledger.exists():
        return []
    campaign = read_json(root / "campaign.json")
    required = {
        "schema_version",
        "event_id",
        "timestamp",
        "campaign_id",
        "authorization_epoch",
        "event_type",
        "actor",
        "payload",
    }
    events: list[JsonObject] = []
    seen_ids: set[str] = set()
    current_epoch = 1
    for line_number, line in enumerate(
        ledger.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            raise ValueError(f"blank ledger line at {ledger}:{line_number}")
        event = json.loads(line)
        if not isinstance(event, dict):
            raise TypeError(f"invalid event at {ledger}:{line_number}")
        missing = sorted(required - event.keys())
        if missing:
            raise ValueError(
                f"event missing fields at {ledger}:{line_number}: {', '.join(missing)}"
            )
        if (
            not isinstance(event["schema_version"], int)
            or isinstance(event["schema_version"], bool)
            or event["schema_version"] != SCHEMA_VERSION
        ):
            raise ValueError(f"unsupported event schema at {ledger}:{line_number}")
        if event["campaign_id"] != campaign["campaign_id"]:
            raise ValueError(f"wrong campaign ID at {ledger}:{line_number}")
        if event["event_type"] not in KNOWN_EVENTS:
            raise ValueError(f"unknown event type at {ledger}:{line_number}")
        if not isinstance(event["payload"], dict):
            raise TypeError(f"event payload is not an object at {ledger}:{line_number}")
        event_id = str(event["event_id"])
        if event_id in seen_ids:
            raise ValueError(f"duplicate event ID at {ledger}:{line_number}")
        seen_ids.add(event_id)
        epoch = event["authorization_epoch"]
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
            raise ValueError(f"invalid authorization epoch at {ledger}:{line_number}")
        if event["event_type"] == "authorized":
            if epoch != current_epoch + 1:
                raise ValueError(
                    f"nonsequential authorization epoch at {ledger}:{line_number}"
                )
            current_epoch = epoch
        elif epoch != current_epoch:
            raise ValueError(f"stale/future ledger epoch at {ledger}:{line_number}")
        events.append(event)
    if not events or events[0]["event_type"] != "campaign_created":
        raise ValueError(f"ledger does not begin with campaign_created: {ledger}")
    head_path = root / "ledger-head.json"
    if head_path.is_symlink() or not head_path.is_file():
        raise ValueError(f"ledger head is missing or unsafe: {head_path}")
    head = read_json(head_path)
    if (
        not isinstance(head.get("schema_version"), int)
        or isinstance(head.get("schema_version"), bool)
        or head["schema_version"] != SCHEMA_VERSION
        or head.get("event_count") != len(events)
        or head.get("last_event_id") != events[-1]["event_id"]
        or head.get("ledger_sha256") != sha256_file(ledger)
    ):
        raise ValueError(
            f"ledger head mismatch (possible truncation/tampering): {ledger}"
        )
    return events


def current_state(root: Path, events: list[JsonObject] | None = None) -> JsonObject:
    campaign = read_json(root / "campaign.json")
    state: JsonObject = {
        "lifecycle": campaign["lifecycle"],
        "authorization_epoch": campaign["authorization_epoch"],
        "baseline_run_id": None,
        "baseline_metric": None,
        "incumbent_run_id": None,
        "incumbent_metric": None,
        "active_hypothesis": None,
        "active_run_ids": [],
        "stop_policy": None,
        "last_result": None,
        "last_decision": None,
        "next_action": None,
        "stopped_reason": campaign.get("stopped_reason"),
    }
    lifecycle_by_event = {
        "authorized": "RUNNING",
        "paused": "PAUSED",
        "stop_requested": "STOP_REQUESTED",
        "stopped": "STOPPED",
        "completed": "COMPLETE",
    }
    for event in events if events is not None else load_events(root):
        event_type = event.get("event_type")
        payload = event.get("payload") or {}
        if event_type in lifecycle_by_event:
            state["lifecycle"] = lifecycle_by_event[event_type]
            if event_type == "authorized":
                state["authorization_epoch"] = event["authorization_epoch"]
                state["stopped_reason"] = None
            elif event_type == "stop_requested":
                state["stop_policy"] = payload.get("policy")
                state["stopped_reason"] = payload.get("reason")
            elif event_type in {"paused", "stopped", "completed"}:
                state["stopped_reason"] = payload.get("reason")
        elif event_type == "hypothesis_added":
            state["active_hypothesis"] = payload.get("hypothesis")
        elif event_type in {"evaluation_queued", "evaluation_started"}:
            run_id = payload.get("run_id")
            if run_id and run_id not in state["active_run_ids"]:
                state["active_run_ids"].append(run_id)
        elif event_type == "evaluation_finished":
            run_id = payload.get("run_id")
            if run_id in state["active_run_ids"]:
                state["active_run_ids"].remove(run_id)
            state["last_result"] = payload
            if payload.get("role") == "baseline" and payload.get("outcome") == "valid":
                state["baseline_run_id"] = payload.get("run_id")
                state["baseline_metric"] = payload.get("metric")
        elif event_type == "decision_recorded":
            state["last_decision"] = payload
            state["next_action"] = payload.get("next_action")
            if payload.get("decision") == "verified-keep":
                state["incumbent_run_id"] = payload.get("candidate_run_id")
                state["incumbent_metric"] = payload.get("metric")
                state["active_hypothesis"] = None
    return state


def new_event(
    campaign: JsonObject,
    event_type: str,
    payload: JsonObject,
    actor: str,
    *,
    epoch: int | None = None,
) -> JsonObject:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "timestamp": utc_now(),
        "campaign_id": campaign["campaign_id"],
        "authorization_epoch": (
            campaign["authorization_epoch"] if epoch is None else epoch
        ),
        "event_type": event_type,
        "actor": actor,
        "payload": payload,
    }


def append_event_unlocked(root: Path, event: JsonObject) -> None:
    ledger = root / "events.jsonl"
    original_size = ledger.stat().st_size if ledger.exists() else 0
    previous_count = 0
    head_path = root / "ledger-head.json"
    if head_path.exists():
        if head_path.is_symlink():
            raise PermissionError(f"ledger head must not be a symlink: {head_path}")
        previous_count = int(read_json(head_path)["event_count"])
    try:
        with ledger.open("a", encoding="utf-8", newline="") as stream:
            stream.write(
                json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        head = {
            "schema_version": SCHEMA_VERSION,
            "event_count": previous_count + 1,
            "last_event_id": event["event_id"],
            "ledger_sha256": sha256_file(ledger),
            "updated_at": utc_now(),
        }
        atomic_write(head_path, json.dumps(head, indent=2, sort_keys=True) + "\n")
    except Exception:
        with ledger.open("r+b") as stream:
            stream.truncate(original_size)
            stream.flush()
            os.fsync(stream.fileno())
        raise


def canonical_lease_path(root: Path, resource_key: str) -> Path:
    if root.parent.name != "campaigns" or root.parent.parent.name != ".autoresearch":
        raise ValueError(f"campaign path is not namespaced correctly: {root}")
    digest = hashlib.sha256(resource_key.encode()).hexdigest()
    return root.parent.parent / "locks" / f"canonical-{digest}.json"


def acquire_canonical_lease(
    root: Path, payload: JsonObject, campaign_id: str, epoch: int
) -> Path | None:
    if payload.get("stage") not in {"canonical", "promotion-audit"}:
        return None
    resource_key = payload.get("resource_key")
    if not isinstance(resource_key, str) or not resource_key:
        raise ValueError("canonical queue requires a nonempty resource_key")
    lease_path = canonical_lease_path(root, resource_key)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    if lease_path.parent.is_symlink():
        raise PermissionError(
            f"lease directory must not be a symlink: {lease_path.parent}"
        )
    descriptor = os.open(
        lease_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    lease = {
        "campaign_id": campaign_id,
        "authorization_epoch": epoch,
        "run_id": payload["run_id"],
        "resource_key": resource_key,
        "created_at": utc_now(),
    }
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(lease, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        lease_path.unlink(missing_ok=True)
        raise
    return lease_path


def verify_canonical_lease(
    root: Path, payload: JsonObject, campaign_id: str
) -> Path | None:
    if payload.get("stage") not in {"canonical", "promotion-audit"}:
        return None
    resource_key = payload.get("resource_key")
    if not isinstance(resource_key, str) or not resource_key:
        raise ValueError("canonical result lacks resource_key")
    lease_path = canonical_lease_path(root, resource_key)
    if lease_path.is_symlink():
        raise PermissionError(f"canonical lease must not be a symlink: {lease_path}")
    lease = read_json(lease_path)
    if (
        lease.get("campaign_id") != campaign_id
        or lease.get("run_id") != payload["run_id"]
    ):
        raise PermissionError(f"canonical lease is owned by another run: {lease_path}")
    return lease_path


def validate_run_manifest(
    manifest: JsonObject, campaign: JsonObject, state: JsonObject
) -> None:
    required = {
        "schema_version",
        "run_id",
        "campaign_id",
        "authorization_epoch",
        "experiment_id",
        "evaluation_id",
        "candidate_id",
        "stage",
        "suite",
        "backend",
        "metric_contract_id",
        "working_directory",
        "command",
        "environment",
        "concurrency_policy",
        "worker_count",
        "timeouts",
        "hashes",
        "expected_outputs",
        "lifecycle",
        "artifacts",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"run manifest missing fields: {', '.join(missing)}")
    validate_campaign_id(str(manifest["run_id"]))
    if (
        not isinstance(manifest["schema_version"], int)
        or isinstance(manifest["schema_version"], bool)
        or manifest["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("unsupported run manifest schema")
    if manifest["campaign_id"] != campaign["campaign_id"]:
        raise ValueError("run manifest campaign mismatch")
    if manifest["authorization_epoch"] != state["authorization_epoch"]:
        raise PermissionError("run manifest authorization epoch is stale")
    if manifest["metric_contract_id"] != campaign["metric_contract_id"]:
        raise ValueError("run manifest metric contract mismatch")
    if manifest["stage"] not in EVIDENCE_STAGES:
        raise ValueError(f"unknown run stage: {manifest['stage']}")
    if manifest["lifecycle"] != "QUEUED":
        raise ValueError("new run manifest lifecycle must be QUEUED")
    if (
        not isinstance(manifest["command"], list)
        or not manifest["command"]
        or not all(isinstance(argument, str) for argument in manifest["command"])
    ):
        raise TypeError("run command must be a nonempty string argument array")
    if not isinstance(manifest["environment"], dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in manifest["environment"].items()
    ):
        raise TypeError("run environment must map strings to strings")
    if not isinstance(manifest["timeouts"], dict):
        raise TypeError("run timeouts must be an object")
    if not isinstance(manifest["artifacts"], dict):
        raise TypeError("run artifacts must be an object")
    if not isinstance(manifest["expected_outputs"], list) or not all(
        isinstance(output, str) for output in manifest["expected_outputs"]
    ):
        raise TypeError("run expected_outputs must be a string array")
    if (
        not isinstance(manifest["worker_count"], int)
        or isinstance(manifest["worker_count"], bool)
        or manifest["worker_count"] < 1
    ):
        raise ValueError("run worker_count must be a positive integer")
    for field in (
        "experiment_id",
        "evaluation_id",
        "candidate_id",
        "suite",
        "backend",
        "working_directory",
        "concurrency_policy",
    ):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise TypeError(f"run manifest {field} must be a nonempty string")
    required_hashes = {
        "source",
        "build",
        "harness",
        "suite",
        "inputs",
        "configuration",
        "toolchain",
        "environment",
    }
    hashes = manifest["hashes"]
    if not isinstance(hashes, dict) or not all(
        isinstance(hashes.get(key), str) and bool(hashes[key])
        for key in required_hashes
    ):
        raise ValueError("run manifest lacks required nonempty string identity hashes")
    if manifest["stage"] in {"canonical", "promotion-audit"} and not manifest.get(
        "resource_key"
    ):
        raise ValueError("canonical manifest requires resource_key")


def register_run(root: Path, manifest: JsonObject, actor: str) -> JsonObject:
    with campaign_lock(root):
        campaign = read_json(root / "campaign.json")
        events = load_events(root)
        state = current_state(root, events)
        if state["lifecycle"] != "RUNNING":
            raise PermissionError(
                f"run registration forbidden while {state['lifecycle']}"
            )
        validate_run_manifest(manifest, campaign, state)
        run_id = str(manifest["run_id"])
        if run_id in state["active_run_ids"]:
            raise ValueError(f"run already active: {run_id}")
        run_root = root / "runs" / run_id
        if run_root.exists() or run_root.is_symlink():
            raise FileExistsError(f"run directory already exists: {run_root}")
        staging = root / "runs" / f".{run_id}.{uuid.uuid4().hex}.tmp"
        lease_path: Path | None = None
        event_committed = False
        try:
            staging.mkdir()
            content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            atomic_write(staging / "manifest.json", content)
            manifest_hash = sha256_file(staging / "manifest.json")
            atomic_write(staging / "manifest.sha256", manifest_hash + "\n")
            (staging / "manifest.json").chmod(0o444)
            queue_payload: JsonObject = {
                "run_id": run_id,
                "stage": manifest["stage"],
                "manifest_path": f"runs/{run_id}/manifest.json",
                "manifest_hash": manifest_hash,
            }
            if manifest.get("resource_key"):
                queue_payload["resource_key"] = manifest["resource_key"]
            lease_path = acquire_canonical_lease(
                root,
                queue_payload,
                str(campaign["campaign_id"]),
                int(state["authorization_epoch"]),
            )
            os.replace(staging, run_root)
            event = new_event(
                campaign,
                "evaluation_queued",
                queue_payload,
                actor,
                epoch=int(state["authorization_epoch"]),
            )
            append_event_unlocked(root, event)
            event_committed = True
            render_views(root, events + [event])
            return event
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            if not event_committed:
                if run_root.exists() and not run_root.is_symlink():
                    shutil.rmtree(run_root)
                if lease_path is not None:
                    lease_path.unlink(missing_ok=True)
            raise


def validate_event_payload(event_type: str, payload: JsonObject) -> None:
    if event_type == "candidate_snapshotted":
        if not payload.get("candidate_id") or not payload.get("source_hash"):
            raise ValueError("candidate snapshot requires candidate_id and source_hash")
    elif event_type in {"evaluation_queued", "evaluation_started"}:
        required = {"run_id", "stage"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"run event missing fields: {', '.join(missing)}")
        if payload["stage"] not in EVIDENCE_STAGES:
            raise ValueError(f"unknown evidence stage: {payload['stage']}")
    if event_type == "evaluation_finished":
        required = {
            "schema_version",
            "run_id",
            "outcome",
            "stage",
            "coverage",
            "guards",
            "constraints",
        }
        required |= RESULT_IDENTITY_FIELDS
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"evaluation result missing fields: {', '.join(missing)}")
        if (
            not isinstance(payload["schema_version"], int)
            or isinstance(payload["schema_version"], bool)
            or payload["schema_version"] != SCHEMA_VERSION
        ):
            raise ValueError("unsupported verification result schema")
        if payload["stage"] not in EVIDENCE_STAGES:
            raise ValueError(f"unknown evidence stage: {payload['stage']}")
        for field in RESULT_IDENTITY_FIELDS:
            if not isinstance(payload[field], str) or not payload[field]:
                raise TypeError(f"evaluation {field} must be a nonempty string")
        for field in ("coverage", "guards", "constraints"):
            if not isinstance(payload[field], dict):
                raise TypeError(f"evaluation {field} must be an object")
        for field in ("expected", "observed", "duplicate_count"):
            count = payload["coverage"].get(field)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise TypeError(
                    f"evaluation coverage.{field} must be a nonnegative integer"
                )
        for field in ("guards", "constraints"):
            if not isinstance(payload[field].get("passed"), bool):
                raise TypeError(f"evaluation {field}.passed must be boolean")
        if payload["stage"] in {"canonical", "promotion-audit"} and not payload.get(
            "resource_key"
        ):
            raise ValueError("canonical result requires resource_key")
        outcome = payload["outcome"]
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"unknown verification outcome: {outcome}")
        if outcome == "valid":
            metric = payload.get("metric")
            if isinstance(metric, bool) or not isinstance(metric, (int, float)):
                raise TypeError("a valid evaluation requires one numeric metric")
            if not math.isfinite(float(metric)):
                raise ValueError("a valid evaluation metric must be finite")
        elif "metric" in payload:
            raise ValueError("a non-valid evaluation must not contain a metric")
    elif event_type == "decision_recorded":
        decision = payload.get("decision")
        if decision not in VALID_DECISIONS:
            raise ValueError(f"unknown decision: {decision}")
        if not payload.get("reason"):
            raise ValueError("a decision requires a reason")
    elif event_type == "stop_requested":
        if payload.get("policy") not in {"cancel-active", "finish-active"}:
            raise ValueError(
                "stop_requested requires cancel-active or finish-active policy"
            )


def evaluation_by_run(
    events: list[JsonObject], run_id: str, *, epoch: int | None = None
) -> JsonObject:
    matches = [
        event["payload"]
        for event in events
        if event["event_type"] == "evaluation_finished"
        and event["payload"].get("run_id") == run_id
        and (epoch is None or event["authorization_epoch"] == epoch)
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one terminal result for run {run_id}")
    return matches[0]


def validate_promotion(
    payload: JsonObject,
    events: list[JsonObject],
    campaign: JsonObject,
    current_epoch: int,
) -> None:
    required = {
        "candidate_run_id",
        "comparator_run_id",
        "promotion_audit_run_id",
        "promoted_source_hash",
        "coverage_complete",
        "no_duplicate_cases",
        "guards_passed",
        "constraints_passed",
        "reproducible_build",
        "threshold_passed",
        "parent_owned",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"promotion audit missing fields: {', '.join(missing)}")
    run_ids = {
        payload["candidate_run_id"],
        payload["comparator_run_id"],
        payload["promotion_audit_run_id"],
    }
    if len(run_ids) != 3:
        raise ValueError(
            "candidate, comparator, and promotion-audit runs must be distinct"
        )
    candidate = evaluation_by_run(
        events, str(payload["candidate_run_id"]), epoch=current_epoch
    )
    promotion_audit = evaluation_by_run(
        events, str(payload["promotion_audit_run_id"]), epoch=current_epoch
    )
    comparator = evaluation_by_run(
        events, str(payload["comparator_run_id"]), epoch=current_epoch
    )
    if candidate["stage"] != "canonical" or comparator["stage"] != "canonical":
        raise ValueError("candidate and comparator run IDs must name canonical runs")
    if candidate["candidate_id"] == comparator["candidate_id"]:
        raise ValueError("candidate and comparator lineages must be distinct")
    if (
        promotion_audit["stage"] != "promotion-audit"
        or promotion_audit["outcome"] != "valid"
        or promotion_audit["candidate_id"] != candidate["candidate_id"]
        or promotion_audit["source_hash"] != candidate["source_hash"]
    ):
        raise ValueError("promotion-audit run does not match the canonical candidate")
    if comparator.get("role") not in {"baseline", "incumbent", "comparator"}:
        raise ValueError("comparator run lacks baseline/incumbent lineage")
    for result in (candidate, comparator, promotion_audit):
        if result["outcome"] != "valid" or result["stage"] not in {
            "canonical",
            "promotion-audit",
        }:
            raise ValueError(
                "promotion requires valid canonical and promotion-audit evidence"
            )
        if result["metric_contract_id"] != campaign["metric_contract_id"]:
            raise ValueError("promotion result metric contract mismatch")
        coverage = result["coverage"]
        if (
            not isinstance(coverage, dict)
            or coverage.get("expected") != coverage.get("observed")
            or coverage.get("duplicate_count") != 0
            or result["guards"].get("passed") is not True
            or result["constraints"].get("passed") is not True
        ):
            raise ValueError("canonical result coverage, guards, or constraints failed")
    candidate_stages = {
        event["payload"]["stage"]
        for event in events
        if event["event_type"] == "evaluation_finished"
        and event["payload"].get("candidate_id") == candidate["candidate_id"]
        and event["payload"].get("source_hash") == candidate["source_hash"]
        and event["payload"].get("outcome") == "valid"
        and event["authorization_epoch"] == current_epoch
    }
    required_stages = {
        "smoke",
        "screen",
        "independent",
        "canonical",
        "promotion-audit",
    }
    if not required_stages.issubset(candidate_stages):
        missing_stages = sorted(required_stages - candidate_stages)
        raise ValueError(
            f"promotion evidence ladder incomplete: {', '.join(missing_stages)}"
        )
    audit_mismatched = sorted(
        field
        for field in RESULT_IDENTITY_FIELDS
        if candidate[field] != promotion_audit[field]
    )
    if audit_mismatched:
        raise ValueError(
            f"promotion-audit identity mismatch: {', '.join(audit_mismatched)}"
        )
    comparison_fields = RESULT_IDENTITY_FIELDS - {"candidate_id", "source_hash"}
    mismatched = sorted(
        field for field in comparison_fields if candidate[field] != comparator[field]
    )
    if mismatched:
        raise ValueError(f"noncomparable promotion results: {', '.join(mismatched)}")
    candidate_metric = float(candidate["metric"])
    comparator_metric = float(comparator["metric"])
    improvement = (
        candidate_metric - comparator_metric
        if campaign["metric_contract"]["direction"] == "higher"
        else comparator_metric - candidate_metric
    )
    threshold = campaign["metric_contract"]["minimum_improvement"]
    required_absolute = float(threshold.get("absolute", 0))
    required_relative = float(threshold.get("relative", 0))
    relative_improvement = (
        improvement / abs(comparator_metric)
        if comparator_metric != 0
        else (math.inf if improvement > 0 else 0)
    )
    if improvement < required_absolute or relative_improvement < required_relative:
        raise ValueError("candidate does not meet the registered improvement threshold")
    checks = (
        "coverage_complete",
        "no_duplicate_cases",
        "guards_passed",
        "constraints_passed",
        "reproducible_build",
        "threshold_passed",
        "parent_owned",
    )
    if not all(payload.get(check) is True for check in checks):
        raise ValueError("promotion audit checks must all pass")
    if candidate["source_hash"] != payload["promoted_source_hash"]:
        raise ValueError("promoted source hash differs from evaluated candidate")


def validate_verified_keep(
    payload: JsonObject, events: list[JsonObject], current_epoch: int
) -> None:
    candidate_run_id = payload.get("candidate_run_id")
    audits = [
        event
        for event in events
        if event["event_type"] == "promotion_verified"
        and event["payload"].get("candidate_run_id") == candidate_run_id
        and event["authorization_epoch"] == current_epoch
    ]
    if len(audits) != 1:
        raise ValueError("verified-keep requires exactly one completed promotion audit")


def append_event(
    root: Path,
    event_type: str,
    payload: JsonObject,
    actor: str,
    *,
    event_epoch: int | None = None,
) -> JsonObject:
    with campaign_lock(root):
        campaign = read_json(root / "campaign.json")
        events = load_events(root)
        state = current_state(root, events)
        lifecycle = str(state["lifecycle"])
        current_epoch = int(state["authorization_epoch"])
        lease_to_release: Path | None = None
        if event_type not in KNOWN_EVENTS:
            raise ValueError(f"unknown event type: {event_type}")
        if event_type in {
            "authorized",
            "campaign_created",
            "evaluation_queued",
            "late_evaluation_observed",
            "legacy_migrated",
            "garbage_collection_started",
            "garbage_collection_recovered",
            "garbage_collection_delete_committed",
            "garbage_collection_finalized",
        }:
            raise PermissionError(f"cannot append reserved event type: {event_type}")
        validate_event_payload(event_type, payload)
        if event_epoch is None:
            raise ValueError(f"{event_type} requires its originating event epoch")
        if event_epoch != current_epoch:
            if event_type == "evaluation_finished" and event_epoch < current_epoch:
                late = new_event(
                    campaign,
                    "late_evaluation_observed",
                    {
                        "originating_epoch": event_epoch,
                        "observed_type": event_type,
                        "run_id": payload.get("run_id"),
                        "outcome": payload.get("outcome"),
                        "reason": "stale authorization epoch",
                    },
                    actor,
                    epoch=current_epoch,
                )
                append_event_unlocked(root, late)
                render_views(root, events + [late])
                return late
            raise PermissionError(
                f"event epoch {event_epoch}; current epoch is {current_epoch}"
            )
        if event_type in LAUNCH_EVENTS and lifecycle != "RUNNING":
            raise PermissionError(f"{event_type} forbidden while lifecycle={lifecycle}")
        active_runs = set(state["active_run_ids"])
        if event_type == "evaluation_started" and payload["run_id"] not in active_runs:
            raise ValueError(f"run was not queued: {payload['run_id']}")
        if event_type == "evaluation_finished":
            run_id = payload["run_id"]
            if run_id not in active_runs:
                late = new_event(
                    campaign,
                    "late_evaluation_observed",
                    {
                        "originating_epoch": event_epoch,
                        "observed_type": event_type,
                        "run_id": run_id,
                        "outcome": payload["outcome"],
                        "reason": "unknown or already terminal run",
                    },
                    actor,
                    epoch=current_epoch,
                )
                append_event_unlocked(root, late)
                render_views(root, events + [late])
                return late
            if lifecycle == "STOP_REQUESTED":
                policy = state.get("stop_policy")
                if policy == "cancel-active" and payload["outcome"] != "cancelled":
                    raise PermissionError(
                        "stop policy permits only cancellation results"
                    )
            elif lifecycle not in {"RUNNING", "PAUSED"}:
                raise PermissionError(
                    f"evaluation_finished forbidden while lifecycle={lifecycle}"
                )
            queued = [
                event["payload"]
                for event in events
                if event["event_type"] == "evaluation_queued"
                and event["payload"].get("run_id") == run_id
            ]
            if len(queued) != 1:
                raise ValueError(f"expected one queue record for run {run_id}")
            for field in ("stage", "resource_key"):
                if queued[0].get(field) != payload.get(field):
                    raise ValueError(f"run result differs from queue record: {field}")
            manifest_path = root / str(queued[0]["manifest_path"])
            if (
                manifest_path.is_symlink()
                or manifest_path.parent.is_symlink()
                or manifest_path.parent.resolve().parent != (root / "runs").resolve()
                or not manifest_path.is_file()
            ):
                raise PermissionError(
                    f"sealed run manifest is missing or unsafe: {manifest_path}"
                )
            if sha256_file(manifest_path) != queued[0]["manifest_hash"]:
                raise ValueError(f"sealed run manifest hash mismatch: {manifest_path}")
            manifest = read_json(manifest_path)
            identity_pairs = {
                "candidate_id": manifest["candidate_id"],
                "metric_contract_id": manifest["metric_contract_id"],
                "suite": manifest["suite"],
                "backend": manifest["backend"],
                "source_hash": manifest["hashes"]["source"],
                "harness_hash": manifest["hashes"]["harness"],
                "input_hash": manifest["hashes"]["inputs"],
                "environment_hash": manifest["hashes"]["environment"],
                "concurrency_policy": manifest["concurrency_policy"],
            }
            mismatched = sorted(
                field
                for field, expected in identity_pairs.items()
                if payload[field] != expected
            )
            if mismatched:
                raise ValueError(
                    f"run result identity mismatch: {', '.join(mismatched)}"
                )
            if payload["metric_contract_id"] != campaign["metric_contract_id"]:
                raise ValueError("evaluation metric contract mismatch")
            lease_to_release = verify_canonical_lease(
                root, payload, str(campaign["campaign_id"])
            )
        if event_type in PROMOTION_EVENTS:
            if lifecycle != "RUNNING":
                raise PermissionError(
                    f"{event_type} forbidden while lifecycle={lifecycle}"
                )
            if active_runs:
                raise PermissionError("promotion requires all active runs reconciled")
            if event_type == "promotion_verified":
                validate_promotion(payload, events, campaign, current_epoch)
        if event_type == "decision_recorded":
            if lifecycle != "RUNNING":
                raise PermissionError(f"decision forbidden while lifecycle={lifecycle}")
            if payload["decision"] == "verified-keep" and active_runs:
                raise PermissionError(
                    "verified keep requires all active runs reconciled"
                )
            if payload["decision"] == "verified-keep":
                validate_verified_keep(payload, events, current_epoch)
                result = evaluation_by_run(
                    events, str(payload["candidate_run_id"]), epoch=current_epoch
                )
                payload = {**payload, "metric": result["metric"]}
        valid_transitions = {
            "paused": {"RUNNING"},
            "stop_requested": {"RUNNING", "PAUSED"},
            "stopped": {"STOP_REQUESTED"},
            "completed": {"RUNNING"},
        }
        if (
            event_type in valid_transitions
            and lifecycle not in valid_transitions[event_type]
        ):
            raise PermissionError(
                f"invalid lifecycle transition: {lifecycle} -> {event_type}"
            )
        if event_type in {"stopped", "completed"} and active_runs:
            raise PermissionError("cannot enter a terminal lifecycle with active runs")
        event = new_event(campaign, event_type, payload, actor, epoch=current_epoch)
        append_event_unlocked(root, event)
        render_views(root, events + [event])
        if lease_to_release is not None:
            lease_to_release.unlink(missing_ok=True)
    return event


def init_campaign(args: argparse.Namespace) -> Path:
    project_root = Path(args.project_root).resolve()
    root = campaign_dir(project_root, args.campaign)
    autoresearch_root = project_root / ".autoresearch"
    campaigns_root = autoresearch_root / "campaigns"
    for path in (autoresearch_root, campaigns_root):
        if path.exists() and path.is_symlink():
            raise PermissionError(f"state directory must not be a symlink: {path}")
    campaigns_root.mkdir(parents=True, exist_ok=True)
    metric_contract = read_json(Path(args.metric_contract))
    validate_metric_contract(metric_contract)
    computed_contract_id = metric_contract_id(metric_contract)
    if args.metric_contract_id and args.metric_contract_id != computed_contract_id:
        raise ValueError(
            f"metric contract ID mismatch: expected {computed_contract_id}"
        )
    campaign: JsonObject = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": args.campaign,
        "created_at": utc_now(),
        "authorization_epoch": 1,
        "lifecycle": "RUNNING",
        "stopped_reason": None,
        "goal": args.goal,
        "scope": args.scope,
        "git_mode": args.git_mode,
        "iteration_policy": {"unit": args.budget_unit, "limit": args.iterations},
        "metric_contract_id": computed_contract_id,
        "metric_contract": metric_contract,
        "artifact_policy": {
            "screen_days": 14,
            "failed_days": 7,
            "storage_warning_bytes": STORAGE_WARNING_BYTES,
            "apply_requires_explicit_flag": True,
        },
    }
    lock_path = campaigns_root / ".init.lock"
    descriptor = os.open(
        lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    with os.fdopen(descriptor, "a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        if root.exists():
            raise FileExistsError(f"campaign already exists: {root}")
        staging = campaigns_root / f".{args.campaign}.{uuid.uuid4().hex}.tmp"
        try:
            for directory in ("runs", "views", "artifacts", "locks"):
                (staging / directory).mkdir(parents=True, exist_ok=True)
            atomic_write(
                staging / "campaign.json",
                json.dumps(campaign, indent=2, sort_keys=True) + "\n",
            )
            event = new_event(
                campaign, "campaign_created", {"goal": args.goal}, args.actor
            )
            append_event_unlocked(staging, event)
            render_views(staging, [event])
            os.replace(staging, root)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return root


def authorize(
    root: Path, reason: str, actor: str, authorization_ref: str
) -> JsonObject:
    if not reason.strip() or not actor.strip() or not authorization_ref.strip():
        raise ValueError("authorization requires reason, actor, and evidence reference")
    with campaign_lock(root):
        campaign = read_json(root / "campaign.json")
        state = current_state(root)
        if state["lifecycle"] not in {"PAUSED", "STOPPED", "COMPLETE"}:
            raise ValueError(f"cannot create a new epoch from {state['lifecycle']}")
        if state["active_run_ids"]:
            raise PermissionError(
                "cannot reauthorize while prior-epoch runs are active"
            )
        epoch = int(state["authorization_epoch"]) + 1
        event = new_event(
            campaign,
            "authorized",
            {"reason": reason, "authorization_ref": authorization_ref},
            actor,
            epoch=epoch,
        )
        append_event_unlocked(root, event)
        render_views(root, load_events(root))
    return event


def render_current_views(root: Path) -> None:
    with campaign_lock(root):
        render_views(root, load_events(root))


def render_views(root: Path, events: list[JsonObject] | None = None) -> None:
    campaign = read_json(root / "campaign.json")
    ledger = events if events is not None else load_events(root)
    state = current_state(root, ledger)
    state_lines = [
        "# Autoresearch State",
        f"campaign_id: {campaign['campaign_id']}",
        f"metric_contract_id: {campaign['metric_contract_id']}",
        f"lifecycle: {state['lifecycle']}",
        f"authorization_epoch: {state['authorization_epoch']}",
        f"goal: {campaign['goal']}",
        f"scope: {campaign['scope']}",
        f"git_mode: {campaign['git_mode']}",
        f"baseline: {state['baseline_metric']} ({state['baseline_run_id']})",
        f"incumbent: {state['incumbent_metric']} ({state['incumbent_run_id']})",
        f"active_hypothesis: {state['active_hypothesis']}",
        f"active_run_ids: {','.join(state['active_run_ids']) or None}",
        f"last_decision: {state['last_decision']}",
        f"next_action: {state['next_action']}",
        f"stopped_reason: {state['stopped_reason']}",
    ]
    atomic_write(root / "views" / "state.md", "\n".join(state_lines) + "\n")

    result_header = [
        "iteration_id",
        "experiment_id",
        "evaluation_id",
        "stage",
        "suite",
        "backend",
        "candidate_run_id",
        "comparator_run_id",
        "metric",
        "comparator_metric",
        "delta",
        "outcome",
        "guards",
        "constraints",
        "artifact_ref",
    ]
    result_rows = [result_header]
    decision_rows = [
        [
            "iteration_id",
            "experiment_id",
            "decision",
            "candidate_run_id",
            "metric",
            "reason",
            "next_action",
        ]
    ]
    ideas: list[str] = ["# Ideas"]
    for event in ledger:
        payload = event.get("payload") or {}
        if event.get("event_type") == "evaluation_finished":
            result_rows.append([str(payload.get(key, "")) for key in result_header])
        elif event.get("event_type") == "decision_recorded":
            decision_rows.append(
                [str(payload.get(key, "")) for key in decision_rows[0]]
            )
        elif event.get("event_type") == "hypothesis_added":
            status = payload.get("status", "untried")
            ideas.append(f"- [{status}] {payload.get('hypothesis', '')}")
    atomic_write(
        root / "views" / "results.tsv",
        "\n".join("\t".join(row) for row in result_rows) + "\n",
    )
    atomic_write(
        root / "views" / "decisions.tsv",
        "\n".join("\t".join(row) for row in decision_rows) + "\n",
    )
    atomic_write(root / "views" / "ideas.md", "\n".join(ideas) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_legacy(root: Path, project_root: Path, actor: str) -> list[JsonObject]:
    legacy_dir = root / "legacy"
    with campaign_lock(root):
        if legacy_dir.exists():
            raise FileExistsError(f"legacy migration already exists: {legacy_dir}")
        sources = [
            project_root / filename
            for filename in LEGACY_FILES
            if (project_root / filename).exists()
        ]
        if not sources:
            raise FileNotFoundError("no legacy autoresearch state files found")
        for source in sources:
            if source.is_symlink() or not source.is_file():
                raise PermissionError(f"legacy source must be a regular file: {source}")
        staging = root / f".legacy.{uuid.uuid4().hex}.tmp"
        copied: list[JsonObject] = []
        try:
            staging.mkdir()
            for source in sources:
                source_hash = sha256_file(source)
                staged = staging / source.name
                shutil.copy2(source, staged)
                if (
                    sha256_file(source) != source_hash
                    or sha256_file(staged) != source_hash
                ):
                    raise ValueError(
                        f"legacy source changed during migration: {source}"
                    )
                copied.append(
                    {
                        "source": str(source),
                        "copy": str(legacy_dir / source.name),
                        "sha256": source_hash,
                    }
                )
            os.replace(staging, legacy_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        campaign = read_json(root / "campaign.json")
        epoch = int(current_state(root)["authorization_epoch"])
        event = new_event(
            campaign, "legacy_migrated", {"files": copied}, actor, epoch=epoch
        )
        try:
            append_event_unlocked(root, event)
        except Exception:
            shutil.rmtree(legacy_dir)
            raise
        render_views(root, load_events(root))
    return copied


def directory_size(path: Path) -> int:
    total = 0
    for candidate in path.rglob("*"):
        if candidate.is_file() and not candidate.is_symlink():
            total += candidate.stat().st_size
    return total


def sha256_artifact(path: Path) -> str:
    digest = hashlib.sha256()
    for candidate in sorted(path.rglob("*")):
        if candidate.is_symlink():
            raise PermissionError(
                f"artifact content must not be a symlink: {candidate}"
            )
        if not candidate.is_file() or candidate.name == "artifact.json":
            continue
        relative = candidate.relative_to(path).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def nested_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from nested_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from nested_strings(nested)


def protected_artifact_roots(root: Path) -> set[Path]:
    artifacts = (root / "artifacts").resolve()
    protected: set[Path] = set()
    records = [
        event["payload"]
        for event in load_events(root)
        if event["event_type"]
        not in {
            "garbage_collection_started",
            "garbage_collection_recovered",
            "garbage_collection_delete_committed",
            "garbage_collection_finalized",
        }
    ]
    for manifest_path in (root / "runs").glob("*/manifest.json"):
        if manifest_path.is_symlink() or manifest_path.parent.is_symlink():
            raise PermissionError(
                f"run manifest must not be a symlink: {manifest_path}"
            )
        records.append(read_json(manifest_path))
    for record in records:
        for value in nested_strings(record):
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = root / candidate
            resolved = candidate.resolve(strict=False)
            try:
                relative = resolved.relative_to(artifacts)
            except ValueError:
                continue
            if relative.parts:
                protected.add(artifacts / relative.parts[0])
    return protected


def gc_candidates(root: Path, now: dt.datetime) -> list[JsonObject]:
    candidates: list[JsonObject] = []
    artifacts = root / "artifacts"
    if not artifacts.exists():
        return candidates
    if artifacts.is_symlink():
        raise PermissionError(f"artifacts directory must not be a symlink: {artifacts}")
    protected = protected_artifact_roots(root)
    for metadata_path in artifacts.glob("*/artifact.json"):
        artifact_root = metadata_path.parent
        if artifact_root.is_symlink() or metadata_path.is_symlink():
            raise PermissionError(
                f"artifact controls must not be symlinks: {artifact_root}"
            )
        metadata = read_json(metadata_path)
        retention_class = str(metadata.get("retention_class", "permanent"))
        if (
            artifact_root.resolve() in protected
            or retention_class in PERMANENT_RETENTION
            or metadata.get("referenced", True)
            or metadata.get("active", False)
        ):
            continue
        eligible_days = RETENTION_DAYS.get(retention_class)
        if eligible_days is None:
            continue
        content_hash = metadata.get("sha256")
        if not isinstance(content_hash, str) or not content_hash:
            raise ValueError(f"artifact metadata lacks content hash: {metadata_path}")
        if sha256_artifact(artifact_root) != content_hash:
            raise ValueError(f"artifact content hash mismatch: {artifact_root}")
        created_at = parse_utc(str(metadata["created_at"]))
        age_days = (now - created_at).total_seconds() / 86400
        if age_days < eligible_days:
            continue
        candidates.append(
            {
                "path": str(artifact_root),
                "size": directory_size(artifact_root),
                "age_days": round(age_days, 3),
                "retention_class": retention_class,
                "sha256": content_hash,
                "reason": f"unreferenced {retention_class} artifact older than {eligible_days} days",
            }
        )
    return candidates


def run_gc(root: Path, apply: bool) -> JsonObject:
    with campaign_lock(root):
        quarantine_parent = root / "gc-quarantine"
        if quarantine_parent.exists() and any(quarantine_parent.iterdir()):
            raise PermissionError(
                f"unresolved GC quarantine requires explicit recovery: {quarantine_parent}"
            )
        candidates = gc_candidates(root, dt.datetime.now(dt.UTC))
        if apply:
            campaign = read_json(root / "campaign.json")
            epoch = int(current_state(root)["authorization_epoch"])
            artifact_parent = (root / "artifacts").resolve()
            validated_paths: list[Path] = []
            for candidate in candidates:
                path = Path(candidate["path"])
                if (
                    path.is_symlink()
                    or not path.is_dir()
                    or path.parent.resolve() != artifact_parent
                    or path.resolve().parent != artifact_parent
                ):
                    raise ValueError(f"unsafe artifact path: {path}")
                validated_paths.append(path)
            started = new_event(
                campaign,
                "garbage_collection_started",
                {"artifacts": candidates},
                "campaign-state-helper",
                epoch=epoch,
            )
            append_event_unlocked(root, started)
            quarantine_root = quarantine_parent / str(started["event_id"])
            quarantine_root.mkdir(parents=True)
            recovery = [
                {
                    "original": str(path),
                    "quarantine": str(quarantine_root / path.name),
                    "sha256": candidate["sha256"],
                }
                for path, candidate in zip(validated_paths, candidates, strict=True)
            ]
            atomic_write(
                quarantine_root / "recovery.json",
                json.dumps(recovery, indent=2, sort_keys=True) + "\n",
            )
            quarantined: list[tuple[Path, Path]] = []
            try:
                for path, candidate in zip(validated_paths, candidates, strict=True):
                    destination = quarantine_root / path.name
                    os.replace(path, destination)
                    quarantined.append((path, destination))
                    if sha256_artifact(destination) != candidate["sha256"]:
                        raise ValueError(f"artifact changed before quarantine: {path}")
            except Exception:
                for original, destination in reversed(quarantined):
                    if destination.exists() and not original.exists():
                        os.replace(destination, original)
                shutil.rmtree(quarantine_root)
                raise
            committed = new_event(
                campaign,
                "garbage_collection_delete_committed",
                {"started_event_id": started["event_id"], "artifacts": candidates},
                "campaign-state-helper",
                epoch=epoch,
            )
            append_event_unlocked(root, committed)
            shutil.rmtree(quarantine_root)
            finalized = new_event(
                campaign,
                "garbage_collection_finalized",
                {
                    "started_event_id": started["event_id"],
                    "commit_event_id": committed["event_id"],
                    "artifacts": candidates,
                },
                "campaign-state-helper",
                epoch=epoch,
            )
            append_event_unlocked(root, finalized)
            render_views(root, load_events(root))
    campaign_bytes = directory_size(root)
    output = {
        "mode": "apply" if apply else "dry-run",
        "candidate_count": len(candidates),
        "candidate_bytes": sum(int(item["size"]) for item in candidates),
        "campaign_bytes": campaign_bytes,
        "storage_warning": campaign_bytes >= STORAGE_WARNING_BYTES,
        "candidates": candidates,
    }
    return output


def recover_gc(
    root: Path, event_id: str, actor: str, mode: str = "restore"
) -> JsonObject:
    if mode not in {"restore", "finalize"}:
        raise ValueError("GC recovery mode must be restore or finalize")
    with campaign_lock(root):
        try:
            uuid.UUID(event_id)
        except ValueError as error:
            raise ValueError("GC recovery ID must be a UUID") from error
        events = load_events(root)
        started_events = [
            event
            for event in events
            if event["event_id"] == event_id
            and event["event_type"] == "garbage_collection_started"
        ]
        if len(started_events) != 1:
            raise ValueError(f"unknown GC start event: {event_id}")
        has_delete_commit = any(
            event["event_type"] == "garbage_collection_delete_committed"
            and event["payload"].get("started_event_id") == event_id
            for event in events
        )
        has_recovery = any(
            event["event_type"] == "garbage_collection_recovered"
            and event["payload"].get("started_event_id") == event_id
            for event in events
        )
        has_finalization = any(
            event["event_type"] == "garbage_collection_finalized"
            and event["payload"].get("started_event_id") == event_id
            for event in events
        )
        if has_finalization or has_recovery:
            raise ValueError(f"GC operation is already reconciled: {event_id}")
        if mode == "finalize" and not has_delete_commit:
            raise PermissionError("finalize requires a durable GC delete commit")
        quarantine_root = root / "gc-quarantine" / event_id
        recovery_path = quarantine_root / "recovery.json"
        if not quarantine_root.exists():
            if mode != "finalize":
                raise FileNotFoundError(f"GC quarantine is missing: {quarantine_root}")
            artifacts = started_events[0]["payload"].get("artifacts", [])
            artifact_parent = (root / "artifacts").resolve()
            if not isinstance(artifacts, list):
                raise TypeError("GC start event artifacts must be an array")
            for item in artifacts:
                if not isinstance(item, dict) or "path" not in item:
                    raise TypeError("GC start event artifact must name a path")
                original = Path(str(item["path"]))
                if original.parent.resolve() != artifact_parent or original.exists():
                    raise PermissionError(
                        f"cannot finalize while an original artifact exists: {original}"
                    )
            campaign = read_json(root / "campaign.json")
            epoch = int(current_state(root, events)["authorization_epoch"])
            event = new_event(
                campaign,
                "garbage_collection_finalized",
                {
                    "started_event_id": event_id,
                    "recovery_mode": mode,
                    "artifacts": artifacts,
                },
                actor,
                epoch=epoch,
            )
            append_event_unlocked(root, event)
            render_views(root, load_events(root))
            return event
        if recovery_path.exists():
            recovery_data = json.loads(recovery_path.read_text(encoding="utf-8"))
            if not isinstance(recovery_data, list):
                raise TypeError("GC recovery manifest must be an array")
        elif quarantine_root.is_dir() and not any(quarantine_root.iterdir()):
            recovery_data = []
        else:
            raise FileNotFoundError(f"GC recovery manifest is missing: {recovery_path}")
        artifact_parent = (root / "artifacts").resolve()
        items: list[tuple[Path, Path, str]] = []
        for item in recovery_data:
            if not isinstance(item, dict):
                raise TypeError("GC recovery item must be an object")
            original = Path(str(item["original"]))
            quarantined = Path(str(item["quarantine"]))
            expected_hash = str(item["sha256"])
            if (
                original.parent.resolve() != artifact_parent
                or quarantined.parent != quarantine_root
                or original.is_symlink()
                or quarantined.is_symlink()
                or (original.exists() and quarantined.exists())
            ):
                raise PermissionError(f"unsafe GC recovery item: {item}")
            if mode == "restore" and not original.exists() and not quarantined.exists():
                raise FileNotFoundError(
                    f"artifact was already deleted; use finalize recovery: {original}"
                )
            if mode == "finalize" and original.exists():
                raise PermissionError(
                    f"finalize refuses an artifact that was never quarantined: {original}"
                )
            existing = original if original.exists() else quarantined
            if existing.exists() and (
                not existing.is_dir() or sha256_artifact(existing) != expected_hash
            ):
                raise ValueError(f"GC recovery hash mismatch: {existing}")
            items.append((original, quarantined, expected_hash))
        if mode == "restore":
            for original, quarantined, _ in items:
                if quarantined.exists():
                    os.replace(quarantined, original)
            event_type = "garbage_collection_recovered"
        else:
            for _, quarantined, _ in items:
                if quarantined.exists():
                    shutil.rmtree(quarantined)
            event_type = "garbage_collection_finalized"
        if recovery_path.exists():
            recovery_path.unlink()
        quarantine_root.rmdir()
        campaign = read_json(root / "campaign.json")
        epoch = int(current_state(root, events)["authorization_epoch"])
        event = new_event(
            campaign,
            event_type,
            {
                "started_event_id": event_id,
                "recovery_mode": mode,
                "artifacts": recovery_data,
            },
            actor,
            epoch=epoch,
        )
        append_event_unlocked(root, event)
        render_views(root, load_events(root))
        return event


def parse_payload(value: str) -> JsonObject:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a namespaced campaign")
    init.add_argument("--project-root", default=".")
    init.add_argument("--campaign", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--scope", required=True)
    init.add_argument("--metric-contract", required=True)
    init.add_argument(
        "--metric-contract-id",
        help="optional expected sha256:<digest>; mismatch fails initialization",
    )
    init.add_argument(
        "--git-mode",
        choices=("experiment-worktree", "experiment-branch", "ledger-only"),
        default="experiment-worktree",
    )
    init.add_argument("--budget-unit", default="candidate_snapshot")
    init.add_argument("--iterations", type=int)
    init.add_argument("--actor", default="controller")

    register = subparsers.add_parser(
        "register-run", help="seal a run manifest and queue the run"
    )
    register.add_argument("--campaign-dir", required=True)
    register.add_argument("--manifest", required=True)
    register.add_argument("--actor", default="controller")

    append = subparsers.add_parser("append", help="append an event and render views")
    append.add_argument("--campaign-dir", required=True)
    append.add_argument("--event-type", required=True)
    append.add_argument("--payload-json", default="{}")
    append.add_argument("--actor", default="controller")
    append.add_argument(
        "--event-epoch",
        type=int,
        help="authorization epoch in which this event originated",
    )

    render = subparsers.add_parser("render", help="regenerate campaign views")
    render.add_argument("--campaign-dir", required=True)

    authorization = subparsers.add_parser(
        "authorize", help="create a new explicit authorization epoch"
    )
    authorization.add_argument("--campaign-dir", required=True)
    authorization.add_argument("--reason", required=True)
    authorization.add_argument(
        "--authorization-ref",
        required=True,
        help="durable reference to the explicit user request",
    )
    authorization.add_argument("--actor", default="user")

    migrate = subparsers.add_parser(
        "migrate-legacy", help="copy legacy root state into a campaign"
    )
    migrate.add_argument("--campaign-dir", required=True)
    migrate.add_argument("--project-root", default=".")
    migrate.add_argument("--actor", default="controller")

    gc = subparsers.add_parser("gc", help="plan or apply artifact garbage collection")
    gc.add_argument("--campaign-dir", required=True)
    gc.add_argument("--apply", action="store_true")

    recovery = subparsers.add_parser(
        "gc-recover", help="restore a preserved interrupted-GC quarantine"
    )
    recovery.add_argument("--campaign-dir", required=True)
    recovery.add_argument("--event-id", required=True)
    recovery.add_argument("--mode", choices=("restore", "finalize"), default="restore")
    recovery.add_argument("--actor", default="controller")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            print(init_campaign(args))
        elif args.command == "register-run":
            manifest_path = Path(args.manifest)
            if manifest_path.is_symlink():
                raise PermissionError(
                    f"manifest input must not be a symlink: {manifest_path}"
                )
            event = register_run(
                Path(args.campaign_dir).absolute(),
                read_json(manifest_path),
                args.actor,
            )
            print(json.dumps(event, indent=2, sort_keys=True))
        elif args.command == "append":
            event = append_event(
                Path(args.campaign_dir).absolute(),
                args.event_type,
                parse_payload(args.payload_json),
                args.actor,
                event_epoch=args.event_epoch,
            )
            print(json.dumps(event, indent=2, sort_keys=True))
        elif args.command == "render":
            render_current_views(Path(args.campaign_dir).absolute())
        elif args.command == "authorize":
            event = authorize(
                Path(args.campaign_dir).absolute(),
                args.reason,
                args.actor,
                args.authorization_ref,
            )
            print(json.dumps(event, indent=2, sort_keys=True))
        elif args.command == "migrate-legacy":
            copied = migrate_legacy(
                Path(args.campaign_dir).absolute(),
                Path(args.project_root).resolve(),
                args.actor,
            )
            print(json.dumps(copied, indent=2))
        elif args.command == "gc":
            output = run_gc(Path(args.campaign_dir).absolute(), args.apply)
            print(json.dumps(output, indent=2, sort_keys=True))
        elif args.command == "gc-recover":
            event = recover_gc(
                Path(args.campaign_dir).absolute(),
                args.event_id,
                args.actor,
                args.mode,
            )
            print(json.dumps(event, indent=2, sort_keys=True))
        else:  # pragma: no cover - argparse enforces commands
            raise AssertionError(args.command)
    except (OSError, TypeError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
