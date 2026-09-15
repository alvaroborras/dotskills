# Runtime and Repository Safety

## Capability discovery

Do not assume tool names, async parameters, agent roles, or clarification APIs.
Inspect the tools exposed by the current environment. If delegation is useful,
list configured agents before selecting one. Map work by capability—read-only
scouting, implementation, review, or research—not by a hardcoded agent name.
If no suitable tool exists, use a safe local alternative or report the blocker.

Tool-like names in older workflow examples are conceptual. Translate them to an
available equivalent; never fabricate successful use of an unavailable tool.
Ask clarification only when a missing decision is genuinely blocking.

## Delegation contract

Each child assignment states goal, exact scope, context, constraints, deliverable,
acceptance criteria, validation, and output cap. Children do not run the canonical
harness, choose experiments, make keep/discard decisions, promote candidates, or
ship final results. Child mutation requires an explicit bounded assignment inside
an isolated campaign workspace; read-only is the default.

For a read-only child:

1. snapshot repository status and hashes for relevant paths;
2. explicitly prohibit edits and project-wide formatters;
3. inspect status and hashes after completion;
4. distrust the report if the workspace changed;
5. restore only changes proven to have been introduced by that child, preserving
   any concurrent user work, and record the violation.

Use one writer per path. Isolate concurrent writers in separate worktrees or
sandboxes. Treat subagent and watcher output as advisory until the parent verifies
its cited files and artifacts.

## Repository preflight

Before mutation record:

- repository root, branch, HEAD, and worktree path;
- tracked, untracked, staged, and ignored in-scope state;
- pre-existing dirty paths and their hashes or patch artifact;
- allowed modification scope;
- selected Git mode.

Do not demand a clean repository when safe isolation is possible.

## Git modes

Select and record one mode:

- `experiment-worktree` (preferred): candidate work occurs in an isolated
  worktree or equivalent sandbox and is promoted explicitly;
- `experiment-branch`: candidate commits occur on a dedicated branch when an
  isolated worktree is unavailable;
- `ledger-only`: no automatic commits; immutable source snapshots and the event
  ledger provide identity and memory.

A request for autoresearch authorizes bounded in-scope candidate edits. It does
not authorize broad staging, pushing, merging, deleting branches, rewriting
history, bypassing hooks, or changing unrelated files.

## Prohibited automatic recovery

Never automatically run destructive reset, clean, broad checkout/restore, delete
a Git lock, bypass hooks, or discard unknown changes. Prefer abandoning an
isolated candidate. If a safe revert conflicts, abort the revert, preserve the
candidate commit/diff, emit `rollback-blocked`, and stop mutation until recovery
is safe. A lock may represent a live process; diagnose ownership rather than
removing it.

## Candidate isolation and promotion

Compile and evaluate a frozen candidate snapshot, not a mutable live source path.
Run syntax/build/smoke checks before creating an experiment commit or expensive
evaluation. Promotion is an explicit parent action after evidence gates pass.
Record the promoted source hash and verify it equals the evaluated source hash.
