---
name: autoresearch-debug
description: Autonomous bug hunting with the scientific method. Use this whenever the user wants root-cause analysis, broad bug hunting, hypothesis-driven debugging, or says debug/autoresearch the failures.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Investigate bugs iteratively: map symptoms, test one falsifiable hypothesis at a time, preserve typed evidence, and produce reproducible findings until the authorized stop condition.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/debug-workflow.md`. The shared runtime, Git, lifecycle, state, and
delegation rules override conflicting examples in the local workflow.

## Workflow

1. Discover available tools and inspect the reported symptom, current failures,
   repository state, and safe experiment boundary.
2. Create or resume a namespaced campaign when investigation is iterative. Record
   lifecycle and authorization before experiments.
3. Map the error surface before deep testing. Form one falsifiable hypothesis and
   design the smallest non-destructive experiment.
4. Return typed experimental outcomes; preserve disproven and inconclusive
   hypotheses as well as confirmed findings.
5. Require file/line evidence, reproduction, impact, and root cause for confirmed
   bugs. Parent verification is required for delegated findings.
6. If fixes are authorized, hand verified findings to `autoresearch-fix`; otherwise
   remain read-only apart from isolated instrumentation and campaign artifacts.

## Guardrails

- Do not jump to fixes before establishing evidence.
- Do not use destructive Git diagnostics against the user's worktree.
- Do not confuse infrastructure failure with a disproven hypothesis.
- Honor durable stop state before every new experiment.

</process>

<success_criteria>
- [ ] Symptoms and error surface are captured.
- [ ] Hypotheses and experiments are atomic and reproducible.
- [ ] Outcomes are typed and evidence is namespaced and durable.
- [ ] Confirmed bugs include severity, location, reproduction, and root cause.
- [ ] Optional fix handoff contains only parent-verified findings.
</success_criteria>
