# API reference

## `OptimizeAnythingConfig`

```python
OptimizeAnythingConfig(
    engine="gepa",
    name=None,
    max_evals=100,
    max_token_cost=None,
    max_concurrency=8,
    output_dir=None,
    run_dir=None,
    stop_at_score=None,
    engine_config={},
)
```

The pinned GEPA runtime has `sandbox=False` by default. This skill does not support enabling it;
preflight rejects a runtime whose default is different or a run that requests confinement.

Common fields:

| Field | Meaning |
|---|---|
| `engine` | `gepa`, `autoresearch`, `meta_harness`, `best_of_n`, or a custom engine instance |
| `max_evals` | Evaluation-call budget; set explicitly for useful search |
| `max_token_cost` | USD cap for the engine's proposer model |
| `max_concurrency` | Evaluation-server worker count |
| `run_dir` | Engine artifacts and work files |
| `output_dir` | Per-evaluation records, progress log, and summary |
| `stop_at_score` | Early stop threshold |
| `engine_config` | Typed engine-specific options |

## Engine options

### `gepa`

`engine_config` is passed to GEPA's typed configuration. Use `reflection`, `engine`, `tracking`,
`merge`, `refiner`, `callbacks`, and `stop_callbacks`. Common nested fields include:

The Codex runtime bridge injects these defaults when they are omitted:

```python
from gepa.strategies.proposal_sampling import PxNSampling
from gepa.strategies.proposal_selection import AllImprovements

engine_config={
    "engine": {
        "sampling_strategy": PxNSampling(p=2, n=2),
        "selection_strategy": AllImprovements(),
    },
}
```

Explicit strategy objects take precedence. `PxNSampling(p=2, n=2)` proposes four candidates per
step; `AllImprovements()` keeps every candidate that passes GEPA's acceptance criterion.

```python
engine_config={
    "reflection": {
        "reflection_lm": "openai/gpt-5.1",
        "reflection_minibatch_size": 5,
    },
    "engine": {
        "sampling_strategy": PxNSampling(p=2, n=2),
        "selection_strategy": AllImprovements(),
        "max_workers": 16,
        "seed": 0,
        "cache_evaluation": False,
        "raise_on_exception": True,
    },
}
```

### `autoresearch`

| Field | Meaning |
|---|---|
| `model` | Upstream field; Codex model is selected with `GEPA_CODEX_MODEL` |
| `ralph` | Forced off by this skill because sessions are not resumed |
| `max_no_eval_seconds` | Stop a proposer that makes no evaluation progress |
| `handoffs` | Artifacts from earlier sequential stages |
| `effort` | Codex reasoning effort, overridden by `GEPA_REASONING_EFFORT` |
| `max_thinking_tokens` | Optional fixed proposer-token budget |

### `meta_harness`

| Field | Meaning |
|---|---|
| `model` | Upstream field; Codex model is selected with `GEPA_CODEX_MODEL` |
| `max_iterations` | Maximum proposer sessions |
| `max_candidates_per_iter` | Candidate count per proposer session |
| `effort` | Codex reasoning effort, overridden by `GEPA_REASONING_EFFORT` |
| `max_thinking_tokens` | Optional fixed proposer-token budget |

### `best_of_n`

| Field | Meaning |
|---|---|
| `model` | LiteLLM model id; set it explicitly |
| `temperature` | Sampling temperature, default `1.0` |
| `max_n` | Optional sample count cap |
| `lm_kwargs` | Extra LM arguments |
| `effort` | Optional provider reasoning setting |

## Codex bridge

The agentic engines invoke `bin/gepa-agent` with a print-oriented JSON contract. The bridge:

1. consumes upstream-only flags;
2. sends the prompt through stdin to `codex exec --json`;
3. uses `GEPA_CODEX_MODEL` or `gpt-5.6-luna`;
4. forwards `GEPA_REASONING_EFFORT` or `high`;
5. emits one normalized result object for GEPA.

Set `CODEX_BIN` when the executable is not discoverable on `PATH`. The bridge never prints prompts,
credentials, or complete environment contents in diagnostics.

## Composition helpers

The public module also exposes `optimize_sequential`, `optimize_parallel`, `optimize_best_of`,
`optimize_vote`, and adaptive sequential helpers. Each stage receives the same evaluator contract;
agentic stages persist handoff artifacts under their configured run directory.
