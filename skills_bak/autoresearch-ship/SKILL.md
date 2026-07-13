---
name: autoresearch-ship
description: Structured shipping workflow for code, releases, deployments, content, marketing, sales, research, or design. Use this whenever the user says ship, deploy, publish, launch, release, or wants a checklist-driven last-mile workflow.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Take an artifact from ready-ish to delivered: identify the shipment type, inventory readiness, generate a mechanical checklist, iteratively close gaps, dry-run, ship, verify, and log the outcome.
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
1. Read `references/ship-workflow.md` before execution and follow its phase structure.
2. If type or mode is missing, inspect the current repo or artifact context first and then ask the single batched ship setup with the current clarification tool.
3. Generate a mechanical checklist, not a vibes-based one. Prefer checks you can actually run.
4. For code shipments, keep using host repo git safety rules and the `gh` CLI for GitHub operations. Only push or create PRs when the user has actually asked to ship.
5. Use bounded preparation loops when checklist items need iterative fixes, then dry-run before any irreversible action unless the chosen mode explicitly skips that gate.

## Guardrails
- Treat irreversible actions carefully and confirm only when a real production, billing, or security boundary is crossed.
- Keep shipment logs and summaries concise and auditable.
- Use rollback paths from the reference when verification fails and rollback is possible.

</process>

<success_criteria>
- [ ] Shipment type and mode are identified.
- [ ] A domain-appropriate checklist is generated and evaluated.
- [ ] Preparation work closes the highest-priority gaps.
- [ ] Dry-run and post-ship verification are completed when applicable.
- [ ] The final shipment is logged with a clear summary.
</success_criteria>
