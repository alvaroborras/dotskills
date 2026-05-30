---
name: autoresearch-learn
description: Autonomous codebase learning and documentation generation. Use this whenever the user wants docs from scratch, docs refreshed after changes, a documentation health check, or a quick project summary grounded in the code.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Scout the codebase, understand its structure, generate or update documentation, validate it mechanically, and iterate on documentation issues until the docs match the codebase reality.
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
1. Read `references/learn-workflow.md` before execution and use it as the canonical documentation workflow.
2. If mode or enough context is missing, do the recommended pre-scan and ask the single batched learn setup with the current clarification tool.
3. Translate upstream scout and docs-manager steps into current-environment primitives: use `task` with the `explore` agent for scouting and `task` with `quick_task` for bounded documentation checks. Keep each helper assignment scoped and capped.
4. Honor mode-specific behavior: init, update, check, and summarize have different read/write boundaries.
5. Write generated docs into `docs/` and keep the audit trail in the structured `learn/` output folder.

## Guardrails
- Do not generate generic boilerplate. Adapt docs to the actual repo structure and project type.
- Keep validation mechanical: broken refs, broken links, stale config keys, and oversize docs should all be caught.
- Cap the validation-fix loop at the limit defined in the reference and accept remaining warnings honestly if needed.

</process>

<success_criteria>
- [ ] Project state is scanned and classified.
- [ ] Required docs are created or updated for the selected mode.
- [ ] Validation runs and issues are either fixed or reported clearly.
- [ ] The final docs and learn audit trail reflect the current codebase state.
</success_criteria>
