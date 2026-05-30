---
name: autoresearch-fix
description: Autonomous repair loop for failing tests, types, lint, builds, or debug findings. Use this whenever the user wants to fix everything, repair a broken state iteratively, or reduce error count to zero.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Take a broken state and iteratively repair it: detect what is broken, prioritize one issue, fix it, verify that the error count dropped, guard against regressions, and repeat until clean or stopped.
</objective>

<process>

## Harness translation
Adapted from Udit Goenka's MIT-licensed autoresearch project. Apply these translations everywhere:
1. When upstream docs say `AskUserQuestion`, use the current environment's clarification tool and batch setup questions exactly as requested.
2. When upstream docs say to switch to another `/autoresearch:...` command, load the sibling skill with the matching name through the current environment's skill-loading mechanism.
3. Ignore any upstream `ToolSearch` instructions or tool-availability notes that do not match the current environment.
4. Use `task` with the `explore` agent for bounded codebase scouting and `task` with `quick_task` for small independent checks. Every subagent assignment must include a line cap and ask for actionable deltas only.
5. Host repo safety rules win over the upstream docs: never revert unrelated user changes, never use destructive git commands unless explicitly requested, and stage only explicit files you changed.

## Source of truth
Read the bundled reference files for this skill before executing. They preserve the upstream autoresearch workflow details that do not fit comfortably in this summary.

## Workflow
1. Read `references/fix-workflow.md` before execution and treat it as the canonical repair workflow.
2. If target, guard, or scope is missing, run the recommended pre-scan and ask the single batched fix setup with the current clarification tool.
3. Detect failures first, then prioritize blockers before polish. Fix exactly one thing per iteration.
4. Commit before verification so you can keep or revert cleanly. Experimental fix commits are explicitly authorized because the user asked for this fix loop.
5. If a guard fails, rework the implementation instead of editing tests or suppressing errors. If debug findings are the source, consume them from the latest debug session or from current context.

## Guardrails
- Do not use escape hatches like `any`, `@ts-ignore`, or deleted tests as fake fixes.
- Do not stage or commit unrelated user work.
- Stop automatically when the tracked error count reaches zero.

</process>

<success_criteria>
- [ ] Failures are detected and prioritized.
- [ ] Each iteration fixes one concrete issue.
- [ ] Verification shows whether the error count improved.
- [ ] Guard checks prevent regressions.
- [ ] The session logs fixes, discards, reworks, and blocked items clearly.
</success_criteria>
