---
name: popcorn-cli
description: |
  Work with the Popcorn CLI to submit custom CUDA/HIP GPU kernels to GPU Mode leaderboards.
  Use when: setting up popcorn projects, registering for leaderboards, submitting kernels,
  fetching leaderboard task descriptions from gpumode.com API, managing submissions,
  debugging test/benchmark failures, or any popcorn CLI workflow. Triggers on keywords
  like popcorn, popcorn-cli, gpumode, leaderboard submission, GPU Mode, kernel bot.
---

# Popcorn CLI

## Quick Start

```bash
popcorn setup          # one-time: bootstrap project with skills + template
popcorn register discord  # one-time: authenticate (or github)
```

## Core Workflow

### 1. Understand the Task

Fetch the leaderboard description via the API:

```
GET https://www.gpumode.com/api/leaderboard/<ID>
```

The response includes:
- `data.description` — task contract (input/output, correctness gates, tolerance)
- `data.benchmarks` — benchmark cases with `batch`, `n`, `cond`, `seed`
- `data.reference` — reference implementation (`generate_input`, `check_implementation`, `ref_kernel`)
- `data.rankings` — current leaderboard rankings and scores

### 2. Write the Kernel

Use `torch.utils.cpp_extension.load_inline()` to embed CUDA/HIP kernels in `submission.py`.
For detailed templates and patterns, read the `load-inline-native-code` skill bundled with `popcorn setup`.

**Key rule**: the module-level `load_inline()` call must live **outside** `custom_kernel()`,
so compilation happens once at import time.

### 3. Submission Modes

Submit in this order when iterating:

| Mode | Command | Purpose |
|------|---------|---------|
| **test** | `popcorn submit --mode test submission.py` | Correctness gate first |
| **benchmark** | `popcorn submit --mode benchmark submission.py` | Check speed relative to reference |
| **leaderboard** | `popcorn submit --mode leaderboard submission.py` | Ranked submission |

Use `--no-tui` for scripted/CI runs. Use `--gpu B200` and `--leaderboard qr` to override POPCORN directives.

### 4. Manage Submissions

```bash
popcorn submissions list              # recent submissions
popcorn submissions show <ID>         # full details including logs
popcorn submissions delete <ID>       # remove unwanted submissions
```

## POPCORN Directives

Embed in `submission.py` to set defaults:

```python
#!POPCORN leaderboard qr
#!POPCORN gpu B200
```

## Reference

For full command reference and submission format details, see [references/commands.md](references/commands.md).
