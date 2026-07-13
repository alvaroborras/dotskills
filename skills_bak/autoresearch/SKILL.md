---
name: autoresearch
description: Autonomous goal-directed iteration for measurable improvements. Use this whenever the user wants an autoresearch loop, repeated modify -> verify -> keep/discard cycles, bounded or unbounded experiments, or says to work autonomously toward a numeric metric.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Run an autonomous improvement loop against a mechanical metric: review state, make one focused change, verify, keep or discard, log the result, and repeat until the user interrupts or the configured iteration limit is reached.
</objective>

<process>

## Harness translation
Adapted from Udit Goenka's MIT-licensed autoresearch project. Apply these translations everywhere:

1. When upstream docs say `AskUserQuestion`, use the current environment's clarification tool (for example, `ask` or `question`) and batch setup questions exactly as requested.
2. When upstream docs say to switch to another `/autoresearch:...` command, load the sibling skill with the matching name through the current environment's skill-loading mechanism.
3. Ignore any upstream `ToolSearch` instructions or tool-availability notes that do not match the current environment.
4. Use `task` with the `explore` agent for bounded codebase scouting and `task` with `quick_task` for small independent checks or disjoint one-file edits. Every subagent assignment must include a line cap and ask for actionable deltas only.
5. Host repo safety rules win over the upstream docs: never revert unrelated user changes, never use destructive git commands unless explicitly requested, and stage only explicit files you changed.

## Source of truth
Read the bundled reference files for this skill before executing. They preserve the upstream autoresearch workflow details that do not fit comfortably in this summary.
## Workflow
1. Read `references/upstream-skill.md`, `references/upstream-command.md`, `references/core-principles.md`, `references/results-logging.md`, `references/autonomous-loop-protocol.md`, `references/harness-discipline.md`, and `references/context-efficiency.md` before acting.
2. If the request is actually about planning, debugging, fixing, security, shipping, scenario exploration, prediction, or documentation, load the matching sibling skill instead of forcing the core loop.
3. If Goal, Scope, Metric, Direction, or Verify is missing, scan the repo for smart defaults and use the two batched clarification rounds described in the upstream skill.
4. Validate preconditions carefully in a dirty repo: avoid unrelated changes, create or reuse a safe branch when needed, and only stage files that belong to the experiment.
5. Create or update `autoresearch-results.tsv`, `autoresearch-state.md`, `autoresearch-decisions.tsv`, and `autoresearch-ideas.md`, establish a baseline, and follow the loop: review -> choose one change -> modify -> commit -> async verify -> decide -> log -> repeat.
6. Read recent git history, recent results, and durable state files every iteration. Git is the audit trail; the state files are the compact working memory. Use both before choosing the next experiment.
7. Treat experimental commits created inside this loop as explicitly authorized because the user asked for autoresearch. Do not stage or commit unrelated work.
8. Use bounded iterations only when configured. Otherwise continue until the user interrupts; do not ask whether to keep going.

## Context-efficient execution
- Prefer `@tintinweb/pi-tasks` when available for structured async experiment tasks: create the benchmark task, execute it in the background, do independent analysis while it runs, then retrieve output once with blocking output retrieval.
- If pi-tasks is unavailable, use `bash(async: true)` for long harness runs and call `job(poll: [...])` only once when the result is needed. Do not poll in a loop.
- Keep the main agent responsible for the keep/discard decision. Subagents may scout, inspect diffs, or analyze outputs, but they do not run the canonical harness or decide whether an experiment stays.
- Store durable loop context in files, not conversation: `autoresearch-state.md` for current facts, `autoresearch-decisions.tsv` for iteration decisions, and `autoresearch-ideas.md` for the hypothesis backlog and graveyard.
- Reference large logs with artifact paths instead of pasting them. Carry only the active hypothesis, current metric, and next action in the conversation.

## Guardrails
- Prefer explicit `git add <files>` over broad staging commands.
- Prefer `git revert` over destructive rollback commands when discarding an experiment.
- Keep output compact: brief progress summaries and a final result, not raw command spam.

</process>

<success_criteria>
- [ ] Required config is captured or collected interactively.
- [ ] Baseline metric is recorded in `autoresearch-results.tsv` and `autoresearch-state.md`.
- [ ] Each iteration makes one logical change, verifies it mechanically, and logs the outcome in both the results log and decision log.
- [ ] Git history, durable state files, and recent results inform the next experiment.
- [ ] Long harness runs use pi-tasks or async bash without polling loops.
- [ ] The loop keeps improvements, discards regressions, and respects the configured stop condition.
</success_criteria>
