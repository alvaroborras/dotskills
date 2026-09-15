# Harness Discipline

Read `execution-contract.md` and `metric-evidence.md` first.

## Pre-campaign gate

Before candidate edits:

1. identify or build the verifier and canonical reporter;
2. run the harness qualification matrix from `execution-contract.md`;
3. freeze the metric contract and baseline-affecting identities;
4. establish a compatible typed baseline;
5. record measured costs for smoke, screen, independent, and canonical stages.

Harness construction or repair is setup work, not a candidate optimization. If it
changes observable semantics, close the old metric contract and rebaseline.

## Per-candidate gate

Use this order:

1. state one falsifiable hypothesis and expected mechanism;
2. isolate one logical candidate without touching unrelated work;
3. run syntax/build and cheap hard-constraint checks;
4. snapshot candidate and create a run manifest;
5. run smoke, then screen;
6. if the registered gate passes, run independent/canonical evidence;
7. compare only compatible named runs;
8. decide and append the event before selecting the next hypothesis.

Never spend a full run on an unbuilt or smoke-failing candidate. Do not combine a
harness semantic change with a candidate change.

## Noisy measurements

Use paired controls, environment pinning, practical thresholds, and independent
confirmation as specified by the metric contract. Do not keep a tiny positive
point estimate merely because it is positive. Diagnose outliers and workload
families before escalating.

## Composition

Test independently developed components separately and in their smallest combined
fixture before scaling. Attribution requires one logical candidate. If components
interact, record the combined mechanism as a new candidate rather than treating
its metric as either component's result.

## Async runs

Use the capability order and immutable state machine in `execution-contract.md`.
A project-native durable runner is preferred. If only blocking execution exists,
use one blocking call with a sufficient timeout. Do not invent async APIs, poll in
a loop, or delegate canonical waiting and interpretation to a subagent.

## Budget response

- After five non-moving valid candidates, confirm determinism and revisit the
  hypothesis backlog.
- After three meaningful regressions from one direction, stop that direction and
  re-plan.
- Near a finite budget, prefer evidence completion and promotion audits over new
  speculative candidates.
- Infrastructure failures consume recorded resources but do not become fake
  metric observations; honor the campaign's pre-registered retry budget.

## Large files and generated code

Use precise edits, run syntax checks promptly, and prefer extracting independently
testable policy helpers over repeated overlapping edits. Re-read only the region
whose identity changed; immutable snapshots prevent stale-line ambiguity.
