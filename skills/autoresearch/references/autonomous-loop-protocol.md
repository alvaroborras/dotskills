# Autonomous Improvement Loop

Read `shared-contract.md` and its required references before this protocol.

## Modes

- **Bounded:** stop when the registered budget unit reaches its limit.
- **Unbounded:** continue while lifecycle is `RUNNING` and the goal remains
  actionable; do not ask whether to continue.

Both modes obey durable stop authorization. Goal achievement may transition to
`COMPLETE`; a user interruption transitions through `STOP_REQUESTED` to `STOPPED`.

## Phase 0 — Resolve the campaign contract

Capture or infer safely:

- goal and allowed modification scope;
- primary metric, direction, verifier, parser, aggregation, denominator;
- suites, backends, comparator policy, thresholds, uncertainty;
- guards and hard correctness/resource/size constraints;
- smoke, screen, independent, canonical, and promotion stages;
- Git mode, iteration budget semantics, stop policy, and retention policy.

Discover available tools and agents. Inspect repository status and protect existing
work. If critical product, authorization, metric, or destructive-action decisions
remain unresolved, ask a compact clarification batch. Otherwise proceed.

Create a new namespaced campaign or resume one only after validating lifecycle,
authorization epoch, metric contract, repository identity, and active runs. Legacy
root state is not silently adopted.

## Phase 1 — Qualify and baseline

Qualify the harness using `execution-contract.md`. Create an immutable baseline run
manifest and obtain a typed valid result. A failed baseline blocks optimization;
fix setup separately and repeat qualification. Record baseline and generated views.

## Phase 2 — Review compact memory

At each iteration read only:

- campaign identity, lifecycle, authorization, budget, and compact state view;
- verified incumbent and exact comparator manifest;
- recent decisions and relevant graveyard entries;
- source/tests needed for the next hypothesis.

Before mutation re-check lifecycle. Choose one hypothesis that is not a duplicate,
or state what materially differs from a failed predecessor.

## Phase 3 — Isolate one candidate

Use the configured safe Git mode. Make one logical in-scope change. Run syntax,
build, and cheap constraints before snapshotting. Repair syntax in place within the
registered pre-snapshot policy; a materially different mechanism is a new
candidate. Never hide errors by weakening tests, suppressing diagnostics, changing
the metric, or editing the harness in the same candidate.

Freeze the candidate source/build identity and append `candidate_snapshotted`.
This is the default point at which an iteration budget is consumed.

## Phase 4 — Evaluate by stages

For every stage:

1. verify lifecycle still authorizes launch;
2. acquire required campaign/canonical lease;
3. create immutable run manifest with candidate and comparator identities;
4. execute through the safest available mechanism;
5. retrieve once and run the canonical reporter;
6. validate semantic completion, typed outcomes, coverage, guards, constraints,
   and artifacts;
7. append the evaluation event.

Stop escalation at the first failed gate. Non-valid outcomes are recorded by type
and never enter numeric comparison. A valid accepted zero may enter comparison.

## Phase 5 — Compare evidence

Compute delta only against the named compatible comparator. Apply metric direction,
fixed denominator, practical thresholds, paired/noise policy, and guard/constraint
results.

- Smoke/screen pass: `provisional`; continue only if escalation is authorized.
- Independent/canonical disagreement: `inconclusive` or `discard`.
- Metric gain with guard/constraint failure: `discard` or rework as a new candidate.
- Below-threshold gain: `deferred`, `inconclusive`, or discard per contract.
- Canonical pass: run the promotion audit; it is not yet verified merely because
  the aggregate improved.

## Phase 6 — Decide and promote safely

The parent/controller owns the decision.

For `verified-keep`, complete every promotion-audit item in `metric-evidence.md`,
then promote the exact evaluated source through the configured Git mode. Verify
post-promotion source hash and rebuild identity. Mark a previous incumbent
`superseded` when appropriate.

For discard, abandon the isolated candidate or perform only a safe targeted revert.
If safe rollback cannot be completed, append `rollback-blocked`, preserve evidence,
and stop mutation. Never use destructive recovery.

Append one decision event, regenerate views, verify them against the ledger, and
only then choose another hypothesis.

## Phase 7 — Stop, pause, or complete

On a user stop request:

1. append `stop_requested` immediately and set `STOP_REQUESTED`;
2. launch nothing new, including holdouts and follow-up validation;
3. finish or cancel only work allowed by the request;
4. validate existing artifacts without expanding evaluation scope;
5. reconcile candidate/incumbent and append `stopped`;
6. regenerate views and report final verified evidence.

On bounded completion, finish the current registered iteration/evidence policy,
then transition to `COMPLETE`. On infrastructure or recovery blockers, transition
to `PAUSED` with an exact next action. Resumption requires explicit authorization
and identity checks.

## Progress and final reporting

Report concise progress at useful boundaries, not after every command. Distinguish
verified incumbent from provisional candidate. Final output includes lifecycle,
budget, baseline, verified result/delta, constraints, canonical run IDs, promoted
identity, discarded/inconclusive counts, storage warning, and any unperformed
validation.
