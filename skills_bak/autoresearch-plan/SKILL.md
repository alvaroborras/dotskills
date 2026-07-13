---
name: autoresearch-plan
description: Convert a plain-language improvement goal into a validated autoresearch configuration. Use this whenever the user wants to set up autoresearch, choose a metric, define scope, or figure out a verify command.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Turn a fuzzy improvement goal into a concrete autoresearch configuration with validated scope, metric, direction, verify command, and optional guard.
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
1. Read `references/plan-workflow.md` before execution and use it as the canonical workflow.
2. Capture the goal or, if missing, ask the batched planning questions with the current clarification tool.
3. Inspect the repo for project type, tooling, likely scopes, and candidate mechanical metrics.
4. Resolve scope globs to real files before accepting them.
5. Build a verify command that returns one parseable number and dry-run it before approval.
6. If a guard is configured, dry-run that too and make sure it passes on the current codebase.
7. Present the final config in a ready-to-use block. If the user wants to launch now, load `autoresearch` and continue with the validated config in context.

## Guardrails
- Never accept a subjective metric.
- Never skip the dry run.
- Prefer fast verification loops over expensive ones when multiple valid metrics exist.

</process>

<success_criteria>
- [ ] Goal is captured or clarified.
- [ ] Scope resolves to real files.
- [ ] Metric is mechanical and direction is clear.
- [ ] Verify command succeeds on a dry run.
- [ ] Optional guard is validated or intentionally omitted.
- [ ] A final config block is presented or handed off to `autoresearch`.
</success_criteria>
