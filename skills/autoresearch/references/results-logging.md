# Results Logging Protocol

Track every iteration in a structured log. Enables pattern recognition and prevents repeating failed experiments.

## Setup & Initialization

Autoresearch creates the log automatically at Phase 0 (baseline). The agent runs these commands during initialization:

```bash
# 1. Create log file with metric direction and header
echo "# metric_direction: higher_is_better" > autoresearch-results.tsv
echo -e "iteration\tcommit\tmetric\tdelta\tguard\tstatus\tdescription" >> autoresearch-results.tsv

# 2. Add to .gitignore (log is local, not committed)
echo "autoresearch-results.tsv" >> .gitignore
echo "autoresearch-state.md" >> .gitignore
echo "autoresearch-decisions.tsv" >> .gitignore
echo "autoresearch-ideas.md" >> .gitignore

echo -e "iter\thypothesis\tresult\tdecision\tnotes" > autoresearch-decisions.tsv
printf "# Ideas\n" > autoresearch-ideas.md

# 3. Run verify command to establish baseline metric
BASELINE=$(npx jest --coverage 2>&1 | grep 'All files' | awk '{print $4}')

# 4. Record baseline as iteration 0
COMMIT=$(git rev-parse --short HEAD)
echo -e "0\t${COMMIT}\t${BASELINE}\t0.0\tpass\tbaseline\tinitial state  coverage ${BASELINE}%" >> autoresearch-results.tsv
printf "# Autoresearch State\ngoal: <goal>\nmetric: <metric> (direction: higher)\nbaseline: %s\nbest_value: %s\nbest_iteration: 0\nbest_commit: %s\niteration: 0/<max-or-unbounded>\nactive_hypothesis: <none>\nlast_result: %s (0.0 from baseline)\n" \
  "$BASELINE" "$BASELINE" "$COMMIT" "$BASELINE" > autoresearch-state.md
```

## Durable State Files

Use three compact files to keep loop memory out of the conversation. They are local working files and should normally stay gitignored with `autoresearch-results.tsv`.

### `autoresearch-state.md`

Read this file at the start of every turn and update it after every keep/discard/crash decision.

```markdown
# Autoresearch State
goal: <one-line goal from config>
metric: <name> (direction: lower|higher)
baseline: <value>
best_value: <value>
best_iteration: <N>
best_commit: <hash>
iteration: <current>/<max-or-unbounded>
active_hypothesis: <one sentence>
last_result: <value> (<delta> from baseline)
```

Keep it short. It should contain only active facts needed for the next decision.

### `autoresearch-decisions.tsv`

Append one row per iteration immediately after the keep/discard/crash decision.

```tsv
iter	hypothesis	result	decision	notes
1	increase batch size	0.083	discard	OOM on worker
2	add caching layer	0.069	keep	-14% latency
```

This is the fastest scan of what was tried and why it stayed or was reverted.

### `autoresearch-ideas.md`

Maintain the hypothesis backlog and graveyard here instead of in conversation.

```markdown
# Ideas
- [untried] Tune parallelism in hot path
- [untried] Replace quadratic lookup with keyed index
- [tried-bad] Increase batch size (iter 1 — OOM)
- [tried-good] Add caching layer (iter 2 — -14% latency)
```

Before choosing a hypothesis, read this file. After deciding, move the attempted idea to `[tried-good]` or `[tried-bad]` and add any newly discovered ideas.

## Logging Function

Called at Phase 7 of every iteration after the keep/discard/crash decision:

```bash
# Function: log_iteration
log_iteration() {
  local iteration=$1 commit=$2 metric=$3 delta=$4 guard=$5 status=$6 description=$7
  echo -e "${iteration}\t${commit}\t${metric}\t${delta}\t${guard}\t${status}\t${description}" \
    >> autoresearch-results.tsv
}

# Usage examples:
log_iteration 1 "b2c3d4e" "87.1" "+1.9" "pass" "keep" "add tests for auth middleware"
log_iteration 2 "-" "86.5" "-0.6" "-" "discard" "refactor test helpers (broke 2 tests)"
log_iteration 3 "-" "0.0" "0.0" "-" "crash" "add integration tests (DB connection failed)"
log_iteration 4 "-" "-" "-" "-" "no-op" "attempted to modify read-only config"
log_iteration 5 "-" "-" "-" "-" "hook-blocked" "pre-commit lint rejected formatting"
```

## Reading & Using the Logs

```bash
# Phase 1 (Review): Read recent entries for pattern recognition
tail -20 autoresearch-results.tsv
tail -20 autoresearch-decisions.tsv

# Count outcomes for progress tracking
KEEPS=$(grep -c 'keep' autoresearch-results.tsv || echo 0)
DISCARDS=$(grep -c 'discard' autoresearch-results.tsv || echo 0)
CRASHES=$(grep -c 'crash' autoresearch-results.tsv || echo 0)

# Detect stuck state: >5 consecutive discards triggers recovery
LAST_5=$(tail -5 autoresearch-results.tsv | awk -F'\t' '{print $6}')
# If all 5 are "discard"  trigger "When Stuck" protocol (re-read all files, try radical change)

# Pattern recognition: which file changes succeed?
# Cross-reference "keep" rows with git log to find winning patterns
grep 'keep' autoresearch-results.tsv | awk -F'\t' '{print $7}'
# Shows descriptions of all successful changes
```

Also read `autoresearch-state.md` and `autoresearch-ideas.md` before selecting the next hypothesis. Do not paste the whole logs into conversation; summarize the active fact and keep the rest in files.

## Integration with the Autoresearch Loop

Where logging fits in the loop lifecycle:

```
Phase 0 (Setup):     CREATE logs/state files, record baseline (iteration 0)
Phase 1 (Review):    READ state, ideas, and last 10-20 log entries
Phase 3-6 (Loop):    Modify, Commit, Verify, Decide
Phase 7 (Log):       APPEND result row, APPEND decision row, UPDATE state and ideas
Phase 8 (Repeat):    Back to Phase 1 (reads updated files)
```

Complete end-to-end example:

```
/autoresearch
Goal: Increase test coverage from 72% to 90%
Scope: src/**/*.ts
Verify: npx jest --coverage 2>&1 | grep 'All files' | awk '{print $4}'
Guard: npm run typecheck

# Internal lifecycle:
# 1. Agent creates autoresearch-results.tsv with baseline 72.0
# 2. Agent reads log (empty except baseline)  decides first experiment
# 3. Agent modifies code, commits, runs verify  gets 74.5
# 4. Agent appends: "1  b2c3d4e  74.5  +2.5  pass  keep  add auth middleware tests"
# 5. Next iteration: agent reads log, sees auth tests worked  tries similar pattern
# 6. Continues until coverage reaches 90% or iterations exhausted
```

## Log Format (TSV)

Create `autoresearch-results.tsv` in the working directory (gitignored):

```tsv
iteration	commit	metric	delta	guard	status	description
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| iteration | int | Sequential counter starting at 0 (baseline) |
| commit | string | Short git hash (7 chars), "-" if reverted |
| metric | float | Measured value from verification |
| delta | float | Change from previous best (negative = improved for "lower is better") |
| guard | enum | `pass`, `fail`, or `-` (no guard configured) |
| status | enum | `baseline`, `keep`, `keep (reworked)`, `discard`, `crash`, `no-op`, `hook-blocked` |
| description | string | One-sentence description of what was tried |

### Example

```tsv
iteration	commit	metric	delta	guard	status	description
0	a1b2c3d	85.2	0.0	pass	baseline	initial state  test coverage 85.2%
1	b2c3d4e	87.1	+1.9	pass	keep	add tests for auth middleware edge cases
2	-	86.5	-0.6	-	discard	refactor test helpers (broke 2 tests)
3	-	0.0	0.0	-	crash	add integration tests (DB connection failed)
4	-	88.9	+1.8	fail	discard	inline hot-path functions (guard: 3 tests broke)
5	c3d4e5f	88.3	+1.2	pass	keep	add tests for error handling in API routes
6	d4e5f6g	89.0	+0.7	pass	keep	add boundary value tests for validators
```

**Note:** When guard fails, the metric may have improved but the change is still discarded. The guard column makes this visible in the log so the agent can learn which optimization approaches tend to cause regressions.

## Log Management

- Create at setup (iteration 0 = baseline)
- Append after EVERY iteration (including crashes)
- Do NOT commit local state/log files unless the project explicitly asks for tracked experiment records
- Read `autoresearch-state.md`, `autoresearch-ideas.md`, and last 10-20 log rows at the start of each iteration
- Use logs to detect patterns: what kind of changes tend to succeed?

## Summary Reporting

Every 10 iterations (or at loop completion in bounded mode), print a brief summary:

```
=== Autoresearch Progress (iteration 20) ===
Baseline: 85.2%  Current best: 92.1% (+6.9%)
Keeps: 8 | Discards: 10 | Crashes: 2
Last 5: keep, discard, discard, keep, keep
```

## Metric Direction

Clarify at setup whether lower or higher is better:
- **Lower is better:** val_bpb, response time (ms), bundle size (KB), error count
- **Higher is better:** test coverage (%), lighthouse score, throughput (req/s)

Record direction in first line of results log as a comment:
```
# metric_direction: higher_is_better
```
