#!/usr/bin/env python3
"""Validate the installed autoresearch skill family and behavior fixtures."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SKILLS = (
    "autoresearch",
    "autoresearch-debug",
    "autoresearch-fix",
    "autoresearch-learn",
    "autoresearch-plan",
    "autoresearch-predict",
    "autoresearch-scenario",
    "autoresearch-security",
    "autoresearch-ship",
)
REQUIRED_SHARED = (
    "shared-contract.md",
    "runtime-safety.md",
    "campaign-state.md",
    "metric-evidence.md",
    "execution-contract.md",
    "context-efficiency.md",
)
REQUIRED_SCHEMAS = (
    "campaign.schema.json",
    "event.schema.json",
    "metric-contract.schema.json",
    "run-manifest.schema.json",
    "verification-result.schema.json",
)
BANNED_NORMATIVE_PATTERNS = {
    "destructive git reset": re.compile(r"\bgit\s+reset\b", re.IGNORECASE),
    "destructive git clean": re.compile(r"\bgit\s+clean\b", re.IGNORECASE),
    "broad git checkout": re.compile(r"\bgit\s+checkout\b", re.IGNORECASE),
    "automatic git stash": re.compile(r"\bgit\s+stash\b", re.IGNORECASE),
    "active git bisect": re.compile(r"\bgit\s+bisect\b", re.IGNORECASE),
    "git lock deletion": re.compile(r"\brm\b[^\n]*\.git/index\.lock", re.IGNORECASE),
    "remote tag deletion": re.compile(r"\bgit\s+push\s+--delete\b", re.IGNORECASE),
    "fail-open zero": re.compile(r"(?:return|echo)\s+[\"']?0\.0", re.IGNORECASE),
    "unsupported async bash": re.compile(r"\bbash\s*\(\s*async", re.IGNORECASE),
    "unsupported polling API": re.compile(r"\bjob\s*\(\s*poll", re.IGNORECASE),
    "stale clarification API": re.compile(r"\bAskUserQuestion\b"),
    "stale tool discovery API": re.compile(r"\bToolSearch\b"),
    "stale helper role": re.compile(
        r"\b(?:quick_task|docs-manager|Explore agent|Task tool)\b", re.IGNORECASE
    ),
    "host-specific agent path": re.compile(r"\.claude/(?:skills|commands|scripts)"),
    "host-specific agent name": re.compile(r"\b(?:Claude|Anthropic)\b"),
}
REQUIRED_TERMS = {
    "shared-contract.md": ("NON-NORMATIVE", "STOPPED", "append-only"),
    "runtime-safety.md": ("experiment-worktree", "ledger-only", "read-only child"),
    "campaign-state.md": (
        ".autoresearch/campaigns/<campaign-id>/",
        "authorization_epoch",
        "gc --apply",
    ),
    "metric-evidence.md": ("accepted zero", "noncomparable", "promotion-audit"),
    "execution-contract.md": (
        "manifest.json",
        "canonical reporter",
        "CANCEL_REQUESTED",
    ),
}
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
PROMOTION_STAGES = {"smoke", "screen", "independent", "canonical", "promotion-audit"}
COMPARISON_KEYS = ("contract", "suite", "backend", "harness")


def normative_markdown(skill_root: Path) -> list[Path]:
    paths: list[Path] = []
    for skill in SKILLS:
        directory = skill_root.parent / skill
        paths.extend(directory.rglob("*.md"))
    return sorted(
        path
        for path in paths
        if not path.name.startswith("upstream-")
        and "/tests/fixtures/" not in path.as_posix()
    )


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    try:
        block = text.split("---\n", 2)[1]
    except IndexError:
        return {}
    values: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def validate_result(case: dict[str, Any]) -> bool:
    outcome = case.get("outcome")
    metrics = case.get("metrics")
    if outcome not in VALID_OUTCOMES or outcome != "valid":
        return False
    if not isinstance(metrics, list) or len(metrics) != 1:
        return False
    metric = metrics[0]
    if isinstance(metric, bool):
        return False
    try:
        return math.isfinite(float(metric))
    except (TypeError, ValueError):
        return False


def comparable(case: dict[str, Any]) -> bool:
    candidate = case.get("candidate", {})
    comparator = case.get("comparator", {})
    return all(candidate.get(key) == comparator.get(key) for key in COMPARISON_KEYS)


def promotable(case: dict[str, Any]) -> bool:
    stages = set(case.get("stages", []))
    return (
        PROMOTION_STAGES.issubset(stages)
        and case.get("source_hash") == case.get("promoted_hash")
        and case.get("constraints") is True
    )


def validate_behavior_fixtures(path: Path) -> list[str]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for case in fixture["verification"]:
        actual = "valid" if validate_result(case) else "invalid"
        if actual != case["expected"]:
            errors.append(f"verification scenario failed: {case['name']}")
    for case in fixture["comparisons"]:
        if comparable(case) is not case["expected"]:
            errors.append(f"comparison scenario failed: {case['name']}")
    for case in fixture["lifecycle"]:
        actual = case["state"] == "RUNNING"
        if actual is not case["expected"]:
            errors.append(f"lifecycle scenario failed: {case['name']}")
    for case in fixture["promotion"]:
        if promotable(case) is not case["expected"]:
            errors.append(f"promotion scenario failed: {case['name']}")
    for case in fixture["async_truth"]:
        if case["canonical"] != case["expected"]:
            errors.append(f"async truth scenario failed: {case['name']}")
    for case in fixture["external_actions"]:
        actual = (
            case.get("checklist") is True
            and case.get("explicit") is True
            and bool(case.get("target"))
        )
        if actual is not case["expected"]:
            errors.append(f"external action scenario failed: {case['name']}")
    return errors


def validate_suite(skill_root: Path) -> list[str]:
    errors: list[str] = []
    shared_dir = skill_root / "references"
    for filename in REQUIRED_SHARED:
        path = shared_dir / filename
        if not path.is_file():
            errors.append(f"missing shared reference: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        normalized_text = text.casefold()
        for term in REQUIRED_TERMS.get(filename, ()):
            if term.casefold() not in normalized_text:
                errors.append(f"{path}: missing required term {term!r}")

    for filename in REQUIRED_SCHEMAS:
        path = skill_root / "schemas" / filename
        if not path.is_file():
            errors.append(f"missing schema: {path}")
            continue
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{path}: invalid JSON schema: {error}")
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{path}: unexpected JSON Schema dialect")
        if schema.get("type") != "object" or not schema.get("required"):
            errors.append(f"{path}: schema must define object requirements")

    for skill in SKILLS:
        path = skill_root.parent / skill / "SKILL.md"
        if not path.is_file():
            errors.append(f"missing skill entrypoint: {path}")
            continue
        metadata = frontmatter(path)
        if metadata.get("name") != skill:
            errors.append(f"{path}: frontmatter name mismatch")
        description = metadata.get("description", "")
        if not description or len(description) > 1024:
            errors.append(f"{path}: invalid description")
        if "shared-contract.md" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: does not load shared-contract.md")
        if skill != "autoresearch":
            workflow = (
                skill_root.parent
                / skill
                / "references"
                / f"{skill.removeprefix('autoresearch-')}-workflow.md"
            )
            if not workflow.is_file():
                errors.append(f"missing sibling workflow: {workflow}")
            elif "events.jsonl" not in workflow.read_text(encoding="utf-8"):
                errors.append(f"{workflow}: does not name the authoritative ledger")

    upstream = (shared_dir / "upstream-skill.md", shared_dir / "upstream-command.md")
    for path in upstream:
        if "NON-NORMATIVE" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: vendored reference lacks NON-NORMATIVE banner")

    for path in normative_markdown(skill_root):
        text = path.read_text(encoding="utf-8")
        for name, pattern in BANNED_NORMATIVE_PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{path}:{line}: banned {name}")

    fixture = skill_root / "tests" / "fixtures" / "behavior-cases.json"
    if not fixture.is_file():
        errors.append(f"missing behavior fixture: {fixture}")
    else:
        errors.extend(validate_behavior_fixtures(fixture))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="path to the autoresearch skill directory",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = validate_suite(args.root.resolve())
    if errors:
        print("autoresearch skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"validated {len(SKILLS)} skills and behavior contract fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
