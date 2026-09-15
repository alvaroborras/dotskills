---
name: autoresearch-scenario
description: Scenario-driven exploration of use cases, edge cases, failures, and threat paths. Use when mapping journeys, generating test cases, or asking what could go wrong.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Explore a seed scenario across relevant dimensions, retaining concrete deduplicated situations and expanding high-value edge, failure, and threat paths.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/scenario-workflow.md`. Shared state, lifecycle, capability, delegation,
and evidence rules override host-specific examples.

## Workflow

1. Resolve seed scenario, domain, scope, actors, constraints, and coverage metric.
2. Create a namespaced campaign for iterative exploration and register dimension,
   deduplication, classification, budget, and stop policies.
3. Generate one concrete situation per iteration with actor, trigger, flow,
   expected outcome, and observable evidence.
4. Classify before retaining, rotate dimensions, and expand high-value cases into
   edge cases, failures, or threat paths.
5. Hand empirically testable cases to debug or security workflows when requested.

## Guardrails

- Reject vague or duplicate scenarios.
- Do not score quantity as coverage without dimension accounting.
- Predictions remain hypothetical until tested.
- Honor namespaced state and durable stop authorization.

</process>

<success_criteria>
- [ ] Seed, dimensions, classification, and coverage metric are explicit.
- [ ] Retained scenarios are concrete and deduplicated.
- [ ] Coverage includes non-happy paths and high-value expansions.
- [ ] Empirical handoffs preserve assumptions and expected outcomes.
</success_criteria>
