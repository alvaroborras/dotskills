---
name: autoresearch-fix
description: Autonomous repair loop for failing tests, types, lint, builds, or debug findings. Use this whenever the user wants to fix everything, repair a broken state iteratively, or reduce error count to zero.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Repair a broken state one verified issue at a time, reducing a typed failure metric to zero without weakening guards or risking unrelated work.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/fix-workflow.md`. Shared repository safety, campaign, verification,
and lifecycle rules override local rollback or tool examples.

## Workflow

1. Discover tools, establish the exact failing baseline, classify infrastructure
   versus product failures, and protect current repository state.
2. Create or resume a namespaced repair campaign with an explicit error-count
   contract, guards, scope, Git mode, budget, and stop policy.
3. Prioritize blockers and fix one concrete cause per candidate. Run syntax/build
   checks before snapshot and evidence.
4. Verify fail closed. A lower error count is valid only when the command completed,
   parsing is unambiguous, and guards did not regress.
5. Promote verified fixes safely; abandon isolated regressions without destructive
   rollback. Record transformed, blocked, and newly exposed errors honestly.
6. Stop automatically when the validated tracked error count reaches zero, the
   budget ends, or durable authorization stops.

## Guardrails

- Do not suppress errors, weaken tests, delete coverage, or introduce escape hatches
  as fake fixes.
- Do not commit unverified candidates to the user's main worktree.
- Do not stage, revert, or mutate unrelated work.

</process>

<success_criteria>
- [ ] Baseline failures and parser semantics are valid.
- [ ] Each candidate addresses one root cause.
- [ ] Typed verification demonstrates improvement and guards remain valid.
- [ ] Regressions are abandoned safely and logged.
- [ ] Completion means a mechanically verified zero or an explicit stopped/blocked state.
</success_criteria>
