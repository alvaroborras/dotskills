# Immutable Execution and Harness Contract

## Harness qualification

Before optimization, qualify the harness with the smallest practical fixtures:

- successful build and one valid evaluation;
- deterministic input generation or recorded randomness;
- exact metric parsing and duplicate/missing/non-finite rejection;
- legitimate accepted-zero behavior;
- malformed input/output, EOF, trailing output, and checker rejection;
- build failure, crash, nonzero exit, CPU timeout, wall timeout, and cancellation;
- child/process-group cleanup and parent-death behavior;
- concurrent-run isolation and canonical-run lease;
- official/accelerated backend parity fixtures when an accelerated backend exists;
- source, binary, harness, configuration, input, and toolchain hashing.

Do not optimize against an unqualified harness. Fixing harness behavior is a
separate campaign/setup change and invalidates affected baselines.

The machine-readable manifest format is
`../schemas/run-manifest.schema.json`.

## Immutable run manifest

Create `runs/<run-id>/manifest.json` before launch using exclusive creation. Seal
it read-only and record its hash; workers and monitors must never rewrite it.
`scripts/campaign_state.py register-run` provides the reference registration and
queue gate. It contains:

- campaign, authorization epoch, experiment, evaluation, candidate, and comparator
  IDs;
- stage, suite, exact cases/manifest hash, backend, worker count, and timeouts;
- metric contract and verifier/harness/config/input hashes;
- frozen source/build paths and hashes, compiler/runtime/toolchain identity;
- command, working directory, environment allowlist, expected outputs;
- lifecycle, process ownership, artifact paths, and resume/cancel policy.

Snapshot the complete driver and everything it reads before blocking. Never edit
a running driver's script or evaluate a mutable live source file. Do not select
artifacts by newest pathname.

## Run state machine

Use durable states: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCEL_REQUESTED`,
`CANCELLED`, and `STALE`. Record transitions atomically. `COMPLETED` means the
coordinator exited successfully and semantic validation found all expected typed
results and artifacts. Launcher exit, status-file presence, case acceptance, and
resource evidence are separate facts.

A missing final summary while a known process is alive means not yet complete.
A stale run requires ownership/process checks and explicit recovery; do not infer
failure from age alone.

## Async capability order

Choose execution from available capabilities:

1. a project-native durable runner satisfying this contract;
2. a structured task/job facility with stable IDs and blocking retrieval;
3. a single blocking command with a sufficient timeout;
4. a carefully managed background process only if it can persist identity,
   ownership, cancellation, and artifacts.

Do not assume any specific async argument, task extension, job API, or agent. Never
poll repeatedly merely to narrate progress. Waiting helpers and subagents are
advisory and may not reinterpret results.

## Canonical reporter

One deterministic reporter reads a specified run ID and emits:

- manifest and lifecycle identity;
- coordinator exit and semantic completion separately;
- typed outcome counts and fixed-denominator metric;
- candidate/comparator identities and compatibility;
- guards, constraints, resources, coverage, hashes, and artifacts.

Watchers call this reporter or report only process state. They never substitute a
metric from another run, infer missing queued artifacts are failures, or promote a
candidate. The parent verifies the report before logging a decision.

## Isolation and leases

Use a campaign lock for ledger writes and a canonical-run lease for resource-
sensitive evaluations. Do not run competing canonical benchmarks concurrently
unless the metric contract explicitly proves concurrency neutrality. Scratch
builds must not overwrite user binaries or shared tool outputs.

## Cancellation and resume

A cancellation request is durable before signalling processes. Stop new case
scheduling, terminate owned process groups/descendants safely, preserve completed
records, and verify cleanup. Resume reuses the exact frozen manifest and completed
case records; it does not rebuild from mutable sources. If identity validation
fails, create a new run rather than mixing evidence.

## Baseline invalidation

Re-establish the relevant baseline when metric, parser, harness, suite, backend,
inputs, toolchain, constraints, concurrency, timeout policy, or instrumentation
changes in a way that can affect results. Record parity-only harness changes as
such only after differential validation.
