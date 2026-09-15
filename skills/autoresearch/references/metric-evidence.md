# Metric and Evidence Contract

## Metric contract

Define before the first candidate:

- primary metric name, direction, unit, aggregation, and fixed denominator;
- exact verifier and parser behavior;
- suite/input manifest and workload families;
- backend and environment identity;
- candidate/comparator pairing policy;
- minimum practical absolute and relative improvement;
- noise, repetition, and uncertainty policy;
- mandatory guards and hard resource/size/correctness constraints;
- evidence stages and promotion gate;
- sealed or one-shot evaluation restrictions.

A single mechanical number is necessary but not sufficient. The contract explains
when that number is valid and comparable. Its machine-readable format is
`../schemas/metric-contract.schema.json`; its ID is the SHA-256 digest of normalized
complete contract JSON.

The machine-readable result format is
`../schemas/verification-result.schema.json`.

## Typed verification result

Every evaluation returns a structured result:

- `outcome`: `valid`, `build_error`, `crash`, `cpu_timeout`, `wall_timeout`,
  `parse_error`, `checker_rejection`, `infrastructure_error`, `cancelled`, or
  `stale`;
- `metric`: one finite number only when `outcome=valid`;
- guard and constraint results;
- run, candidate, suite, backend, harness, and artifact identities;
- coverage counts and diagnostic metrics.

Never substitute a number for a non-valid outcome. Missing output, duplicate
metric lines, NaN, infinity, parser ambiguity, timeout, and nonzero process exit
fail closed. A legitimate accepted zero is valid when the official semantics permit it.
Use structured parsing or shell pipelines with failure propagation; process exit
zero alone is not semantic success.

## Comparability

A delta names its comparator explicitly. Candidate and comparator must have the
same metric contract ID and compatible suite, cases, backend, harness, inputs,
constraints, environment, and concurrency policy. Prefer contemporaneous paired
runs on identical cases. If any required identity differs, label the result
`noncomparable`; do not compute or claim an attributable gain.

Use the contract's fixed denominator. Invalid cases remain represented according
to official semantics; never silently average successful cases only.

## Evidence ladder

Pre-register the cheapest valid ladder for the project:

1. `smoke`: build, parser/protocol, and basic guard checks;
2. `screen`: fast representative development evaluation;
3. `independent`: disjoint or contemporaneous paired confirmation;
4. `canonical`: full official-equivalent evaluation;
5. `promotion-audit`: identity, coverage, constraints, and reproducibility.

The reference implementation requires a valid sealed `promotion-audit` run in the
current authorization epoch, followed by a validated `promotion_verified` event
that binds that run, canonical candidate/comparator, source identity, coverage,
constraints, threshold, and parent-owned decision.

Passing one stage permits only provisional scheduling of the next stage; it is
not acceptance. A screen can only produce `provisional`. Independent disagreement
becomes `inconclusive` or `discard`. Only a valid canonical result plus a completed
promotion audit can produce `verified-keep`. Unit correctness does not substitute
for score evidence.

For expensive metrics, validate the parser and harness on a tiny fixture rather
than requiring the canonical command to finish quickly. Record measured stage
costs and use the least expensive stage capable of answering the current question.

## Noisy and adaptively reused data

For noisy metrics:

- pin controllable environment variables and concurrency;
- use paired case-level differences where feasible;
- report practical effect size and an appropriate uncertainty summary;
- investigate largest regressions and workload-family effects;
- require independent confirmation for small gains;
- label intervals on repeatedly reused development data as descriptive.

A positive point estimate below the practical threshold is not automatically a
keep. Score-neutral changes may be retained only under a pre-registered secondary
rule, such as materially simpler code or verified resource reduction, while
remaining honest about no primary-metric gain.

## Suite discipline

Keep screening/development, independent validation, transformed stress, and sealed
final suites distinct. Seed diversity is not workload diversity. Stress results
are diagnostics and are not mixed into the official objective with arbitrary
weights. A sealed or one-shot suite is reserved and consumed only according to
its recorded policy; results from it cannot be used for further tuning unless the
policy explicitly permits that.

## Constraints and diagnostics

Evaluate hard constraints before expensive scoring where possible and again during
promotion. Examples include source or bundle size, CPU, wall time, memory, protocol
validity, security gates, and compatibility. Record scopes accurately: combined
native CPU is not solver-only CPU, and wall timeout is not CPU timeout.

Diagnostic metrics explain the primary result but do not silently replace it.
Record acceptance, per-family metrics, largest regressions, resource maxima, and
domain-specific cost components when available.

## Promotion audit

Promotion requires machine-checkable evidence for:

- completed canonical run and exact expected case coverage with no duplicates;
- typed outcomes and all required guards/constraints;
- named comparator and valid delta under the metric contract;
- evaluated source hash equal to promoted source hash;
- frozen source, build, harness, suite, input, config, and toolchain identities;
- reproducible rebuild under recorded flags;
- resource and size limits;
- immutable run IDs and artifact references;
- parent-owned decision and commit/tag identity when applicable.

Record failed checklist items and why a candidate was not promoted.
