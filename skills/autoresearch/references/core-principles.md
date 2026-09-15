# Core Autoresearch Principles

Read `shared-contract.md` first. These principles summarize the reasoning behind
the normative runtime, campaign, evidence, and execution contracts.

## 1. Constraints enable autonomy

Define modification scope, hard correctness/resource constraints, evidence cost,
and iteration/stop budget before experimentation. Constraints are promotion gates,
not prose reminders.

## 2. Strategy and tactics are separate

The user supplies the goal and authorization boundary. The controller selects
bounded tactical hypotheses. Helpers advise; they do not redefine the objective,
run canonical evidence, or promote candidates.

## 3. Mechanical metrics require typed validity

A metric is usable only when a command or structured verifier produces one finite
number under a known contract. The result also needs a typed outcome, fixed
denominator, suite/backend identity, and guards. Timeout, crash, parse failure,
missing output, duplicate metrics, NaN, and infinity are failures—not fallback
numbers. A domain-valid zero remains valid.

## 4. Use the cheapest adequate evidence

Qualify the harness on tiny fixtures, screen candidates cheaply, and reserve
independent/canonical evaluations for promising candidates. Fast evidence may be
provisional; speed does not grant promotion authority.

## 5. Iteration cost shapes search

Measure stage costs. Cheap reliable screens support exploration; expensive or
noisy evaluations require stronger hypotheses, paired controls, and practical
thresholds. Do not burn canonical or sealed evidence on unqualified candidates.

## 6. Immutable identity is memory

The append-only ledger, frozen source/build/harness manifests, and explicit run
IDs are the audit trail. Git can complement that trail in a safe experiment mode,
but commits are not mandatory and never justify destructive recovery.

## 7. Honest evidence beats optimistic labels

Report provisional, inconclusive, deferred, discarded, verified, and superseded
results precisely. State backend/resource limitations and adaptive-data caveats.
A unit improvement, process exit, or watcher summary is not a canonical gain.

## Meta-principle

Autonomy scales when authorization, scope, validity, comparison, promotion, and
recovery are explicit enough for the next action to be mechanically determined.
