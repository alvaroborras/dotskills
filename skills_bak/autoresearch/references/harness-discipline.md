# Harness Discipline for Autoresearch Loops

Rules for building and operating iterative benchmarks that waste minimal iterations.

---

## 1. Harness Must Be Git-Tracked

`autoresearch.sh` (or equivalent) **MUST** be committed to git before the loop starts.

Without git tracking, `log_experiment discard` cannot reset the harness to baseline state. Every revert requires a manual rewrite — wasting iterations on configuration drift rather than code experiments.

```bash
git add autoresearch.sh
git commit -m "autoresearch: add harness"
```

Only the harness configuration file needs tracking. Output directories, cache files, and the results log stay gitignored.

---

## 2. Fast-Test Mode

The harness **MUST** support a fast diagnostic mode to validate hypotheses before the full run.

```bash
# Full run (all configured targets, used for kept iterations only)
RUN_SCOPE="${RUN_SCOPE:-all}"

# Fast mode (small representative slice or reduced per-target budget)
FAST_MODE="${FAST_MODE:-0}"  # env var or --fast flag

# Pick the hardest or most representative target for fast mode when possible
FAST_TARGET="${FAST_TARGET:-representative}"
```

**Rule**: Never run the full harness to validate an unproven hypothesis. Fast-test first. Only run the full harness after the fast-test shows improvement. If the metric requires all targets, keep all targets but reduce per-target budgets in fast mode.

This avoids wasting full benchmark runs on changes that a diagnostic pass would reject.

---

## 3. Pre-Iteration Gate

Every iteration **MUST** follow this sequence. Skipping steps 2-4 wastes full runs on changes that a diagnostic pass would reject:

```
1. State hypothesis (one sentence: what changes and why)
2. Edit code
3. Syntax check (language-appropriate parser/compiler)
4. Fast-test on diagnostic target or reduced budget
5. If improved: run full harness → log as keep
6. If not: discard change, log finding, next hypothesis
```

**Never change both harness configuration and implementation code in the same iteration** — you can't attribute the result.

---

## 4. Edit Discipline on Large Files

Files over 1000 lines require extra care. Repeated overlapping edits cascade:

| Rule | Rationale |
|------|-----------|
| Re-read file before every edit | Stale hashes poison subsequent edits |
| Verify syntax after every single edit | `ast.parse()` takes 0.1s; cascaded errors take minutes to debug |
| Prefer `ast_grep`/`ast_edit` for structural changes | AST-aware, doesn't drift with line numbers |
| New logic goes in new modules | One-line call-site change instead of editing a large file in-place repeatedly |

---

## 5. Composition: Test Merge Before Scaling

When combining independently generated partial solutions or optimization passes, test the composition on the smallest representative target before scaling to the full harness.

**Pattern**: Run each component on a diagnostic target. Validate the merged output. If the combined result degrades quality on the diagnostic target, stop and redesign before spending a full run.

Repeatedly scaling unvalidated compositions wastes iterations and hides which component caused the regression.

---

## 6. Iteration Budget Management

Track the ratio of meaningful to stability iterations:

| Condition | Action |
|-----------|--------|
| 5 consecutive iterations show no metric movement despite code changes | Switch to stability-only mode (no code changes, confirm determinism) |
| 3 consecutive iterations degrade the metric | Stop and re-plan. The approach is wrong. |
| Remaining iteration budget is low | Only exploit known-success patterns; no exploration |

Don't spend the remaining budget on random walks when recent evidence says the search is stuck.

---

## 7. Structured Decision Log

Maintain a compact decision log separate from the results TSV. One line per iteration:

```
iter | hypothesis                    | fast_test | result  | decision
12   | increase cache size           | better    | 0.083   | keep
13   | switch queue discipline       | worse     | 0.091   | discard
```

This prevents re-trying the same approach under a slightly different name. Git commits serve as the primary memory, but the decision log provides a quick scan of what was attempted.

---

## 8. Async Harness Pattern

Long harness runs should not pin the conversation in a polling loop.

**Preferred: pi-tasks (`@tintinweb/pi-tasks`)**

Use pi-tasks when installed because it provides structured experiment tasks, file-backed project persistence, dependency metadata, and a single blocking output retrieval call:

```text
TaskCreate(subject="Run full benchmark", description="bash autoresearch.sh", activeForm="Running benchmark…")
TaskExecute(task_ids=["#1"], agentType="Explore")
# Do independent work while the harness runs.
TaskOutput(task_id="#1", block=true, timeout=600000)
TaskUpdate(task_id="#1", metadata={hypothesis: "<hypothesis>", result: "<metric>", decision: "<decision>"})
```

**Fallback: native async bash**

```text
bash(async: true, timeout: <seconds>, command: "bash autoresearch.sh")
# Do independent work while the harness runs.
job(poll: ["<job-id>"])  # final blocking wait only
```

Never poll repeatedly just to watch logs. Capture the artifact reference, extract the metric once, and write the decision to the state files.

---

## 9. Time Budget Awareness


Know the actual time cost of each stage:

| Stage | Typical time | Dominated by |
|-------|--------------|--------------|
| Data loading / setup | project-specific | Input size and initialization |
| Fast diagnostic run | project-specific | Representative target and reduced budget |
| Full harness run | project-specific | Number of targets and solver/test workload |
| Validation / guard | project-specific | Invariant checks and integration coverage |
| Scoring / metric extraction | project-specific | Parser and reporting overhead |

Set iteration caps based on measured per-iteration cost, not aspiration. If the harness is expensive, use fast diagnostics and async execution aggressively.
