---
name: architect-loop
description: "Run the Architect Loop in Codex: use Codex as the architect/judge and GPT-5.5 high `codex exec` workers as builders in isolated git worktrees. Use when the user asks to architect, run the loop, dispatch builders, judge builder work, create the next slice, split work into lanes, perform gated multi-agent implementation, or resume a repo that uses docs/HANDOFF.md, docs/gates/, and docs/lanes/."
---

# Architect Loop

Use this for slice-sized repo work where fresh-context builders, frozen gates,
and independent judgment are worth the overhead. Do ordinary small fixes
directly.

Codex in the current session is the ARCHITECT: arbitrate, freeze gates, dispatch
builders, verify raw evidence, integrate, and make kill/continue calls. Builder
lanes are fresh `codex exec` processes pinned to GPT-5.5 with high reasoning.
The repo is the durable memory.

Detailed mechanics live in:

- `references/dispatch.md`: exact `codex exec` commands, worktree fan-out,
  builder block template, integration, stall handling.
- `references/research.md`: optional slice-level research fan-out.
- `references/research-lanes.md`: discovery-scale research lane tactics.
- `references/HANDOFF.template.md`: initial repo handoff template.

## Hard Rules

1. Do not implement while acting as architect. Put required changes in the
   slice spec and dispatch builders, unless the task is too small for the loop.
2. Not in `docs/HANDOFF.md` or a lane report = did not happen. Do not judge
   claims that only exist in chat.
3. Freeze gates before results exist: write `docs/gates/<slice>.md` and commit
   it before dispatch. Quote gates verbatim when judging. Any builder edit under
   `docs/gates/` is an automatic slice FAIL.
4. Nobody grades their own work. Builders report raw evidence only; the
   architect runs gates and reads outputs before giving verdicts.
5. Builder PHASE 0 must surface disagreements with file evidence. Rule on every
   disagreement: ACCEPT, REJECT, or MODIFY plus one line why.
6. Audit every status claim against a tool result from the current session
   before reporting it.
7. Use fresh builder context per lane. Use `codex exec resume --last` only for
   follow-ups inside the current lane, never across slices.
8. Isolate parallel lanes with git worktrees and non-overlapping file-touch
   sets. A conflict or out-of-bounds write is a spec defect.
9. Stop and checkpoint when verification fails without a root cause,
   instructions conflict with project docs, a destructive action is needed, or
   scope grows beyond the frozen slice.

## Procedure

### 0. Ground

Read project instructions in authority order: `AGENTS.md`, `README.md`, then
architecture docs and CI config. Learn exact verification commands.

Run `codex --version` once per environment. For a new CLI/version, do one
canary `codex exec` before fanning out.

Read `docs/HANDOFF.md` and referenced `docs/gates/` files. If missing, create
`docs/HANDOFF.md`, `docs/gates/`, and `docs/lanes/` from
`references/HANDOFF.template.md`, filling only what is derivable and asking for
the rest if needed. Keep the handoff compact: TL;DR, current slice, gates,
open disagreements, decisions, and pointers.

### 1. Arbitrate

For each row in the handoff's Open Disagreements table, write a ruling:
ACCEPT, REJECT, or MODIFY, with one concrete reason. No deferrals.

### 2. Judge Previous Work

For each frozen gate, run the command yourself and compare the raw output to
the gate text:

- PASS: measured exactly and threshold satisfied.
- FAIL: measured exactly and threshold not satisfied, or builder edited gates.
- INVALID: command/output did not measure what the gate specified.

Then read the diff against the slice intent. Gate pass is necessary, not
sufficient. Make one slice-level call: KILL or CONTINUE, with the decisive
reason. For high-risk work involving schemas, APIs, persistence, security, or
critical correctness, run a fresh review pass before the verdict.

### 3. Research When Needed

Skip research unless the slice depends on unfamiliar external APIs/libraries,
a narrow approach choice needs current facts, or the user asks for research.
When needed, follow `references/research.md`: dispatch 3-5 read-only GPT-5.5
researchers, verify load-bearing claims yourself, then write and commit
`docs/prd/<slice>.md` with citations. For broad discovery or technology
selection, use `references/research-lanes.md` to design the lanes.

### 4. Spec The Next Slice

Make the slice one PR-sized unit. The spec must be self-contained:

- Objective and why.
- Output format: raw tables, numbers, commit SHAs, command output paths.
- Tool guidance: exact verification commands and live API/version checks.
- Boundaries: may-touch files, must-not-touch files, out-of-scope items, no
  placeholders, search before implementing, no unrelated refactors.
- Lane plan: 1-4 lanes with checked non-overlapping file-touch sets. Most
  slices are one lane.
- Gates: exact commands and thresholds in `docs/gates/<slice>.md`, committed
  before dispatch.
- Effort call: default builders to GPT-5.5 high. Use another effort only when
  explicitly requested by the human and recorded in the spec.

### 5. Dispatch Builders

Follow `references/dispatch.md` exactly. Write builder blocks to files and pass
them to `codex exec` via stdin (`-`), not shell arguments.

Single lane: dispatch in the main checkout. Multiple lanes: create one
worktree per lane off the freeze commit, then launch all lane builders in
parallel. Builders write raw results to `docs/lanes/<slice>-<lane>.md` and do
not commit.

Use this model pin unless the user explicitly changes it:

```bash
-m gpt-5.5 -c model_reasoning_effort="high"
```

### 6. Post-Flight And Integrate

For each lane, verify:

- Lane report exists and contains raw evidence.
- PHASE 0 disagreements were present or the builder documented what it checked.
- `docs/gates/` is unchanged.
- `git status` only shows declared may-touch files.

Commit each passing lane yourself. Merge passing lane branches sequentially into
`slice/<name>`, running gate smoke checks after each merge. A merge conflict
means the lane plan was not disjoint: kill the conflicting lane and re-spec.

Do not merge to `main` in the same session that dispatched and integrated the
slice. Judgment of the integration branch belongs to the next architect pass.
