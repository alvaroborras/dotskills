# Builder Dispatch Reference

Use this when the main skill reaches dispatch or integration.

## Preflight

Run:

```bash
codex --version
```

If the CLI version or environment is new, run one canary `codex exec` before
parallel fan-out. Pin the model explicitly:

```bash
-m gpt-5.5 -c model_reasoning_effort="high"
```

Write prompt blocks to files and pass them through stdin (`-`). Do not pass a
large block as a shell argument.

## Single-Lane Dispatch

```bash
mkdir -p .architect docs/lanes docs/gates
codex exec -C <repo-root> --sandbox workspace-write \
  -m gpt-5.5 -c model_reasoning_effort="high" \
  --json -o .architect/last-run.jsonl \
  - < .architect/dispatch-block.md
```

## Worktree Fan-Out

For 2-4 disjoint lanes:

```bash
git -C <repo-root> worktree add .architect/wt/<slice>-<NN> \
  -b lane/<slice>-<NN> <freeze-sha>

codex exec -C <repo-root>/.architect/wt/<slice>-<NN> --sandbox workspace-write \
  -m gpt-5.5 -c model_reasoning_effort="high" \
  --json -o .architect/wt/<slice>-<NN>.last-run.jsonl \
  - < .architect/wt/<slice>-<NN>.block.md
```

Launch lanes in parallel. Each lane writes only its declared files and its raw
report at `docs/lanes/<slice>-<lane>.md`.

## Same-Lane Follow-Up

Use only within the current lane:

```bash
codex exec resume --last "<rulings or clarification, then proceed>"
```

Never resume across slices.

## Stall Detection

A run is stalled when its `--json` output file has not grown for 15+ minutes
and the last event is an in-progress command. Diagnose the child process under
the Codex process. Kill the narrowest stuck child command, not the full Codex
run. Kill the full run only if it re-enters the same hang or the worktree is
broken; then discard that lane and re-dispatch.

Known fragile areas under `workspace-write`: browser launches, asyncio
subprocess harnesses, and long shell here-doc scripts. If a gate cannot run in
the builder sandbox, the builder must record the exact failure; the architect
runs the gate outside the builder sandbox at judgment time.

## Integration

Builders do not commit. The architect commits and merges:

```bash
git -C <repo-root> checkout -b slice/<name> <freeze-sha>

git -C <repo-root>/.architect/wt/<slice>-<NN> add -A
git -C <repo-root>/.architect/wt/<slice>-<NN> commit -m "lane <NN>: <what>"
git -C <repo-root> merge --no-ff lane/<slice>-<NN>
<run gate smoke checks>

git -C <repo-root> worktree remove .architect/wt/<slice>-<NN>
git -C <repo-root> branch -d lane/<slice>-<NN>
```

A merge conflict means the lane plan was not disjoint. Kill the conflicting
lane and re-spec; do not hand-resolve builder conflicts.

## Builder Block Template

```text
Execute the architect spec below. Operating rules:

PHASE 0 - Before any code: reply with your plan and EVERY disagreement you have
with this spec, with reasons, citing real files in this repo. Silent compliance
is a failure. Silent scope additions are a failure. If you have no
disagreements, state what you checked before concluding the spec is sound.
Verify the named APIs/formats/versions against the live dependencies before
planning around them.

PHASE 1 - Freeze shared contracts (schemas/interfaces) in docs/ first. After
freeze they are read-only for everyone including you. Files under docs/gates/
are read-only at all times; editing them fails the slice regardless of results.

PHASE 2 - Build YOUR LANE ONLY: exactly the files listed in BOUNDARIES. You may
touch no other files. No placeholder implementations. Search the codebase
before implementing. Run the lane gate commands and record verbatim output. Do
NOT commit. Do NOT delete lock files or escalate privileges if git commands
fail; record the exact error and continue. Give every long command an explicit
timeout. If a runtime cannot start under the sandbox, record the exact failure
and route around it; never busy-wait.

When done, write docs/lanes/<slice>-<lane>.md with RAW results only: tables,
numbers, command output, SHAs, and file paths. No interpretation. Every status
claim must be backed by a command result from this run. End with exactly one:
STATUS: COMPLETE | COMPLETE_WITH_CONCERNS (<list>) | BLOCKED (<exact blocker +
what you tried>)

=== OBJECTIVE (and why) ===
...

=== OUTPUT FORMAT ===
...

=== TOOL GUIDANCE (verification commands; verify-against-reality list) ===
...

=== BOUNDARIES (may touch / must not touch / out of scope) ===
...

=== DISAGREEMENT RULINGS (from last session) ===
...

=== ACCEPTANCE GATES (frozen at docs/gates/<slice>.md - read-only) ===
...
```
