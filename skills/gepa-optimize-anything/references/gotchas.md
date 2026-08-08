# Gotchas and pitfalls

## Reward hacking

Every engine maximizes exactly the score you compute. Gate correctness before rewarding speed,
style, or cost, and inspect winning candidates against the real objective.

## Selection bias

The selected validation score is the maximum over many candidates. Use a representative validation
set and report an untouched `test_set` score separately.

## Stochastic evaluators

One sample per evaluation can make scores noisy. Average multiple samples inside the evaluator when
the task model is stochastic.

## Budget sizing

`max_evals` counts evaluation calls, not proposals. Start around 15–20 times the selection-set size,
or 15–20 for a single-task run. Add `max_token_cost` for proposer spend and `stop_at_score` when
the metric has a ceiling.

## Strict engine configuration

Each engine validates its own `engine_config`. A key valid for `gepa` may be invalid for
`autoresearch`, `meta_harness`, or `best_of_n`; change the whole nested block when changing engines.

## Agentic prerequisites

AutoResearch and MetaHarness require the bundled entrypoint, an authenticated Codex executable, and
`jq` for AutoResearch's generated evaluation script. Run `scripts/preflight.py` before long jobs.
The runtime must use the pinned GEPA revision with a false default sandbox flag.

## Seed saturation

GEPA reflects on failures. If the seed is already near-perfect on the reflection minibatch, proposals
may all be rejected and the seed may be returned unchanged. Include examples that expose real gaps.

## Evaluator exceptions

Catch expected failures and return a low score with diagnostic feedback so the proposer can learn from
them. Use `raise_on_exception=False` only when converting exceptions to score zero is intentional.

## Parallel proposals

The skill defaults to `PxNSampling(p=2, n=2)` plus `AllImprovements()`: four proposals per step,
plus validation fan-out. Match both `max_concurrency` and GEPA worker counts to actual provider and
evaluator capacity; reduce either strategy dimension explicitly when capacity is tight.

## Quick checklist

- [ ] Correct data mode: single-task, multi-task, or generalization.
- [ ] Score is gated against the real objective.
- [ ] Feedback contains errors, diffs, and partial-credit details.
- [ ] Budget is sized for many proposals.
- [ ] `stop_at_score` and `max_token_cost` are set when appropriate.
- [ ] `run_dir` and `output_dir` are configured for persistent artifacts.
- [ ] Test-set reporting is enabled when an unbiased number matters.
- [ ] Codex preflight passes in the same Python environment as the run.
