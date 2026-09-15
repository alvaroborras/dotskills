---
name: autoresearch-predict
description: Multi-persona analysis before action. Use when the user wants independent expert perspectives, pre-debug prediction, pre-ship review, adversarial debate, or specialist hypotheses.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Generate independent evidence-grounded expert hypotheses, debate disagreements, preserve minority views, and hand ranked priors to empirical workflows without presenting predictions as facts.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/predict-workflow.md`. Shared capability discovery, delegation safety,
state, lifecycle, and context limits override host-specific examples.

## Workflow

1. Resolve goal, scope, depth, evidence boundary, and available independent agents.
2. Build or refresh concise knowledge artifacts from verified repository evidence.
3. Run bounded independent persona passes with explicit read-only contracts and
   output limits; verify workspace integrity afterward.
4. Debate conflicts, run anti-herd checks, and preserve minority hypotheses.
5. Label outputs as priors with confidence and falsifying tests. Hand them to
   debug, security, scenario, fix, ship, or core autoresearch only when requested.

## Guardrails

- Predictions never override empirical typed evidence.
- Do not fabricate independent agents when unavailable.
- Require real file/line evidence for repository claims.
- Keep artifacts namespaced and honor durable stop authorization.

</process>

<success_criteria>
- [ ] Scope, depth, and available capabilities are resolved.
- [ ] Multiple genuinely independent analyses are represented when available.
- [ ] Consensus, disagreement, and anti-herd results remain visible.
- [ ] Ranked hypotheses include falsifying tests and empirical handoff paths.
</success_criteria>
