---
name: autoresearch-plan
description: Convert a plain-language improvement goal into a validated autoresearch campaign and metric contract. Use when choosing scope, evidence stages, constraints, comparators, stop policy, or verification commands.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Turn a fuzzy improvement goal into a safe, ready-to-run autoresearch campaign contract with validated scope, typed verification, evidence stages, constraints, and lifecycle policy.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
read `references/plan-workflow.md`. The shared contract wins over conflicting
examples or host-specific vocabulary.

## Workflow

1. Discover available tools and inspect the repository for project-native research
   infrastructure, tests, benchmarks, constraints, and protected work.
2. Capture the goal and resolve modification scope to real paths. Ask only blocking
   questions through an available clarification mechanism.
3. Define the complete metric contract: typed result, direction, aggregation,
   denominator, suites, backends, comparator, thresholds, uncertainty, constraints,
   evidence ladder, and sealed-evaluation policy.
4. Validate parser/harness behavior on the cheapest fixture, including failure
   cases and legitimate zero. Validate configured guards.
5. Select campaign ID, namespaced state location, Git mode, iteration accounting,
   stop/resume behavior, and retention policy.
6. Present a ready-to-use contract. Launch only when the user's request authorizes
   execution; otherwise stop after planning.

## Guardrails

- Never accept a subjective or fail-open metric.
- Never compare incompatible suites, backends, or metric contracts.
- An expensive canonical verifier need not finish during planning if its parser and
  harness can be qualified safely on a fixture.
- Do not mutate project code while planning.

</process>

<success_criteria>
- [ ] Goal, scope, campaign identity, and Git mode are resolved.
- [ ] Metric validity, comparison, constraints, and evidence stages are explicit.
- [ ] Smoke verification and guards are qualified mechanically.
- [ ] Lifecycle, budgets, sealed data, and retention are defined.
- [ ] The final contract can be handed directly to the core autoresearch skill.
</success_criteria>
