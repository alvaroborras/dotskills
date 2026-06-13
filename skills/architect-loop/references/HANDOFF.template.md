# HANDOFF - [project name]

Repo memory for the Architect Loop. Builders update raw evidence after each
run; the architect writes rulings and verdicts. Raw evidence only in builder
sections: tables, numbers, SHAs, command output, paths. No interpretation.
Every claim must be backed by a command result from the run that wrote it.

Not in this file or a referenced lane report = did not happen.

## TL;DR

- Goal: [one sentence]
- Last slice: [name] - [PASS/FAIL/pending judgment]
- Next action: [exact command or decision needed]

## Project Goal

[One paragraph. What this is and what done means.]

## Verification Gate

```bash
[install / test / lint / typecheck / build commands]
```

## Frozen Contracts

[Links to docs files holding frozen schemas/interfaces. Read-only after freeze.]

## Current Slice

- Spec: [link or one-line summary]
- Gates: docs/gates/[slice].md, frozen at commit [sha]
- Lanes: [1 | N disjoint lanes; reports in docs/lanes/[slice]-[lane].md]
- Effort: high - [why]

| Gate | Command | Threshold | Raw result | Architect verdict |
|------|---------|-----------|------------|-------------------|
|      |         |           |            | PASS/FAIL/INVALID |

## Raw Results

[Latest builder raw results or links to lane reports.]

## Open Disagreements

| # | Builder position | Spec position | Evidence | Ruling |
|---|------------------|---------------|----------|--------|
|   |                  |               |          | ACCEPT/REJECT/MODIFY - why |

## Decisions Log

| Date | Decision | Why |
|------|----------|-----|

## Next Slice

[Proposal or pending decision.]

## Session Log

| Date | Role | Slice | Commits | Gates P/F | Notes |
|------|------|-------|---------|-----------|-------|
