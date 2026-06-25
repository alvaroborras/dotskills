# Popcorn CLI Command Reference

## Authentication

```bash
popcorn register discord     # register via Discord
popcorn register github      # register via GitHub
popcorn reregister           # re-authenticate
```

## Project Setup

```bash
popcorn setup                # bootstrap project with agent skills + submission template
```

Creates: `.popcorn/`, `.codex/skills/`, `.claude/skills/`, `submission.py`, `AGENTS.md`

## Submission

```bash
popcorn submit <file>                          # interactive TUI submission
popcorn submit --no-tui <file>                 # non-interactive, prints results to stdout
popcorn submit --mode test <file>              # correctness-only check
popcorn submit --mode benchmark <file>         # performance benchmark against reference
popcorn submit --mode leaderboard <file>       # ranked leaderboard submission
popcorn submit --mode profile <file>           # profiling run
popcorn submit --gpu B200 <file>               # override GPU target
popcorn submit --leaderboard qr <file>         # override leaderboard
```

## Managing Submissions

```bash
popcorn submissions list                  # list recent submissions
popcorn submissions show <SUBMISSION_ID>  # full details + logs
popcorn submissions delete <SUBMISSION_ID>  # remove a submission
```

## Join Private Leaderboard

```bash
popcorn join <INVITE_CODE>                # join a closed leaderboard
```

## Admin (Requires POPCORN_ADMIN_TOKEN)

```bash
popcorn admin <command>
```

## Submission File Format

A single Python file with:

1. **POPCORN directives** (optional, first lines):
```python
#!POPCORN leaderboard <name>
#!POPCORN gpu <gpu_type>
```

2. **Required imports and signature**:
```python
import torch
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    ...
```

- `input_t` / `output_t` are defined by the leaderboard's reference implementation.
- The checker calls `custom_kernel()` and validates against the task's correctness gates.
- Inline CUDA/HIP kernels use `torch.utils.cpp_extension.load_inline()`.

## Leaderboard API

```
GET  https://www.gpumode.com/api/leaderboard/<ID>
```

Response fields:
- `data.name` — leaderboard name (e.g. "qr")
- `data.description` — task contract, input/output spec, correctness tolerances
- `data.benchmarks` — array of `{batch, n, cond, seed}` cases
- `data.reference` — Python source for `generate_input`, `check_implementation`, `ref_kernel`
- `data.rankings.<GPU>` — current leaderboard: `rank`, `score` (geometric mean runtime in seconds), `user_name`, `submission_id`
- `data.gpu_types` — allowed GPU targets
- `data.lang` — submission language ("Python")
- `data.deadline` — ISO 8601 deadline
- `data.time_left` — human-readable remaining time
