# Autoresearch Campaign Planning

Read `../../autoresearch/references/shared-contract.md` first.

## 1. Inspect before asking

Identify project instructions, repository state, existing research runners,
modifiable paths, tests, benchmarks, official evaluators, hard constraints, and
likely expensive stages. Discover available tools rather than assuming an API.
Ask a compact clarification batch only for decisions that cannot be inferred
responsibly.

## 2. Goal and scope

Record a one-sentence goal and resolve allowed globs to real paths. Separate:

- candidate modification scope;
- harness/setup scope;
- generated artifact scope;
- protected user-owned paths.

Warn when scope exceeds what can be understood or safely isolated. Do not include
tests in candidate scope merely to make guards easier to pass.

## 3. Campaign identity and Git mode

Choose a unique, stable campaign ID and default location
`.autoresearch/campaigns/<campaign-id>/`, with `events.jsonl` as the authoritative
ledger and Markdown/TSV only as generated views. Select `experiment-worktree`,
`experiment-branch`, or `ledger-only` according to repository capabilities and
policy. Record pre-existing dirty paths. If legacy root-level state exists,
discover it read-only and offer explicit migration rather than overwriting it.

## 4. Primary metric contract

Define:

| Field | Requirement |
|---|---|
| name/unit/direction | One primary mechanical objective |
| aggregation | Exact formula, including rounding |
| denominator | Fixed expected population and invalid-case treatment |
| verifier/parser | Structured command and exact finite-number cardinality |
| suite/input identity | Manifest, workload families, hashes, overlap policy |
| backend/environment | Official/diagnostic role, workers, limits, pinned factors |
| comparator | Named baseline/control and paired-run policy |
| threshold | Minimum practical absolute and relative gain |
| noise policy | Repetitions, paired statistics, uncertainty summary |
| constraints | Correctness, size, CPU, wall, memory, security, compatibility |
| sealed policy | Reservation, one-shot rules, and tuning prohibition |

A command that emits a number is insufficient if failures can emit the same shape,
if successful cases are silently excluded, or if backend identity is absent.

## 5. Typed verifier qualification

The verifier must distinguish `valid`, build error, crash, CPU timeout, wall
timeout, parse error, checker rejection, infrastructure error, cancellation, and
stale state. `metric` exists only for a valid finite result. Legitimate zero is
allowed when defined by the domain.

Dry-run the cheapest representative fixture and test at least:

- one valid nonzero result;
- accepted zero when applicable;
- command failure;
- missing and duplicate metric output;
- NaN/infinity rejection;
- timeout classification;
- guard failure.

Use failure-propagating pipelines or structured parsing. Do not substitute a
numeric sentinel for failure.

## 6. Evidence ladder

Register commands, suites, expected cost, and gates for:

1. smoke/build/protocol checks;
2. representative screen;
3. disjoint or paired independent confirmation;
4. canonical official-equivalent verification;
5. promotion audit.

For expensive canonical evaluation, qualify its parser and manifest using a tiny
fixture rather than requiring the full run during planning. A screen cannot create
a verified keep.

## 7. Harness and baseline policy

List identities that invalidate the baseline: metric/parser, harness, suite,
backend, input, toolchain, timeout, concurrency, instrumentation, or constraints.
Require immutable run manifests and a canonical reporter. If an accelerated
backend exists, define parity fixtures and label it diagnostic until proven
compatible for the claimed comparison.

## 8. Budget, lifecycle, and retention

Specify:

- bounded/unbounded mode and exactly what consumes an iteration;
- retry limits for infrastructure failures;
- lifecycle start state and stop-current-work policy;
- authorization epoch behavior on resume;
- checkpoint/context-rebase interval;
- default retention from `campaign-state.md`, including the 10 GiB warning and
  explicit-only `gc --apply` deletion.

## 9. Final contract

Present a compact ready-to-run block containing:

- Campaign ID, Goal, Scope, Git Mode;
- Metric, Direction, Aggregation, Denominator;
- Verify/Parser, Guard, Constraints;
- Suites, Backends, Comparator, Threshold, Noise Policy;
- Evidence Stages and Promotion Gate;
- Iteration Budget/Unit, Lifecycle, Stop Policy;
- State Directory, Sealed Policy, Retention;
- qualification results and baseline if valid.

If the user requested planning only, do not launch. If they explicitly requested
the loop as well, hand this contract to `autoresearch` without asking redundant
questions.

## Failure handling

Do not launch when scope is empty, the baseline is invalid, metric cardinality is
ambiguous, required constraints cannot be checked, campaign identity collides, or
a stopped campaign lacks new authorization. Explain the exact failed contract
field and the smallest safe correction.
