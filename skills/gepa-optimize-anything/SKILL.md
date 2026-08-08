---
name: gepa-optimize-anything
description: >-
  Optimize any scorable text artifact—prompts, code, configurations, schemas, agent instructions,
  or search solutions—with GEPA's evaluator-driven optimize_anything API. Use when Codex needs to
  design an evaluator, improve a candidate through execution feedback, compare optimization engines,
  or run AutoResearch and MetaHarness through Codex.
---

# optimize_anything

Use `optimize_anything` when a candidate can be represented as text and a program can score it.
The evaluator owns the truth: return a higher-is-better score and actionable feedback. The optimizer
does not inspect the evaluator's implementation.

## Engines

- `gepa` — reflective evolutionary search with Pareto-aware selection; the default and usually the
  best first choice when evaluator feedback is rich.
- `autoresearch` — one Codex subprocess repeatedly edits and evaluates a candidate in a work tree.
- `meta_harness` — Codex proposes several candidates from frontier/history state; the engine scores
  each candidate and records the result.
- `best_of_n` — independent samples retained as a comparison baseline.

All agentic engines use the bundled `bin/gepa-agent` bridge and Codex. Do not substitute another
agent CLI. Agent runs are intentionally unconfined because the candidate may need to compile, run,
benchmark, and edit files. Use this skill only in a trusted workspace.

## Install the pinned runtime

The upstream revision immediately before the default-confinement change is pinned so a fresh setup
does not silently acquire a different process policy:

```bash
cd /home/alvaro/.agents/skills/gepa-optimize-anything
python3 -m venv .venv
.venv/bin/pip install "gepa[full] @ git+https://github.com/gepa-ai/gepa.git@2059343dfcc622aab67943b4ce98184ae302661a"
python scripts/reapply_codex_runtime.py --apply
export PATH="/home/alvaro/.agents/skills/gepa-optimize-anything/bin:$PATH"
```

Set `OPENAI_API_KEY` for the in-process reflection engine. Authenticate Codex and optionally set:

```bash
export CODEX_BIN="$(command -v codex)"
export GEPA_CODEX_MODEL=gpt-5.6-luna
export GEPA_REASONING_EFFORT=high
```

Run `python scripts/preflight.py --engine autoresearch` before an agentic run. If the evaluator
must use another Python environment, call `scripts/bootstrap_host_runtime.py` before importing
`gepa.optimize_anything`.

## Candidate and evaluator contract

```python
from gepa.optimize_anything import OptimizeAnythingConfig, optimize_anything

def evaluate(candidate: str, example) -> tuple[float, dict]:
    output = run_system(candidate, example)
    score = grade(output, example)
    return score, {"output": output, "error": getattr(output, "error", None)}

result = optimize_anything(
    seed_candidate=SEED,
    evaluator=evaluate,
    dataset=trainset,
    valset=valset,
    test_set=testset,
    objective="Maximize task quality while preserving the required output format.",
    background="Constraints, domain rules, and evaluator details.",
    config=OptimizeAnythingConfig(
        engine="gepa",
        max_evals=300,
        stop_at_score=1.0,
        run_dir="runs/example",
        output_dir="outputs/example",
    ),
)
print(result.best_candidate, result.best_score)
```

The evaluator may accept `(candidate)` for a single task or `(candidate, example)` when datasets
are supplied. Return feedback that explains failures: compiler output, diffs, partial scores, logs,
and violated constraints are more useful than a bare number. Use `batch_evaluator` when scoring
several candidate/example pairs is cheaper as one provider batch.

## Choose the data mode

- No `dataset` and no `valset`: single-task optimization.
- `dataset` only: optimize across a shared training pool.
- `dataset` plus `valset`: optimize on training data and select on held-out validation data.
- `test_set`: reporting-only; it is scored after optimization and never enters the search.

Size `max_evals` for many proposals, not one. A practical starting point is 15–20 times the number
of examples in the selection set, or 15–20 for a single-task run. Add `stop_at_score` when the
metric has a known ceiling and `max_token_cost` for agentic engines.

## Parallel GEPA proposals

For GEPA 0.1.4+, this skill defaults every `OptimizeAnythingConfig(engine="gepa")` to
`PxNSampling(p=2, n=2)` plus `AllImprovements()`. That means four proposal tasks per step, with
every accepted improvement retained. The evaluator and model provider must support concurrent work:

```python
from gepa.strategies.proposal_sampling import PxNSampling
from gepa.strategies.proposal_selection import AllImprovements

config = OptimizeAnythingConfig(
    engine="gepa",
    max_concurrency=16,
    engine_config={
        "engine": {
            "sampling_strategy": PxNSampling(p=2, n=2),
            "selection_strategy": AllImprovements(),
            "max_workers": 16,
        }
    },
)
```

The defaults are injected by the Codex runtime bridge, so the `engine_config["engine"]` block may be
omitted. Supplying either strategy explicitly overrides only that strategy.

Keep both concurrency limits within evaluator, CPU/GPU, and provider capacity. Make the evaluator
retry-safe and independent of evaluation order.

## Agentic engines

Put the skill's `bin` directory first on `PATH`. AutoResearch creates `program.md`, candidate files,
and an `eval.sh` HTTP client. MetaHarness creates frontier/history state and expects each proposal
to write `pending_eval.json`. The test set remains sealed by the evaluation server.

Use `engine_config` fields documented in [references/api.md](references/api.md). The bridge consumes
the upstream print-oriented command contract and invokes `codex exec --json`; it ignores unsupported
session controls and uses a fresh Codex invocation per proposer call.

## Workflow

1. Choose the data mode and write a gated, non-gameable score.
2. Include concrete diagnostic feedback in the evaluator result.
3. Set an explicit evaluation budget, token cap, and score stop when applicable.
4. Run preflight and a one-call reflection-LM check for long jobs.
5. Inspect the first evaluation, then monitor accepted proposals and artifact directories.
6. Compare the final candidate with the seed on the held-out test set.

Read [references/gotchas.md](references/gotchas.md) for reward hacking, selection bias, budget sizing,
and agent failure modes. Read [references/writing_evaluators.md](references/writing_evaluators.md)
when designing a new evaluator. Use [references/tracking.md](references/tracking.md) for experiment
tracking configuration.
