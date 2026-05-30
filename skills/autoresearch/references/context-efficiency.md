# Context Efficiency Playbook

Autoresearch loops can run for many iterations. Treat context as a scarce working set: keep only the current decision in conversation, and push durable history into files, git, task metadata, and artifacts.

## 1. Working Memory Model

Use three layers of memory:

| Layer | What belongs there | What does not belong there |
|---|---|---|
| Conversation | Current hypothesis, current metric, immediate blocker, next action | Raw logs, old failed ideas, full benchmark output |
| Durable files | Current state, decisions, idea backlog, compact conclusions | Command spam, duplicated artifacts |
| Artifacts / git | Full logs, diffs, committed experiment history | Long prose summaries copied back into chat |

Active facts are the only facts the next step needs: best value, current branch/commit, active hypothesis, latest metric, and the next command. Archived facts are everything already decided; store them outside the conversation.

## 2. Required State Files

Create or update these files in the project root unless the project has an explicit experiment directory:

- `autoresearch-state.md` — current active facts. Read at the start of every turn and after restarts.
- `autoresearch-decisions.tsv` — one compact row per iteration: hypothesis, result, decision, notes.
- `autoresearch-ideas.md` — hypothesis backlog and graveyard. Move tried ideas to `[tried-good]` or `[tried-bad]`.

After each keep/discard/crash decision:

1. Append the measured result to `autoresearch-results.tsv`.
2. Append the decision to `autoresearch-decisions.tsv`.
3. Update best/current fields in `autoresearch-state.md`.
4. Move the hypothesis in `autoresearch-ideas.md` from `[untried]` to `[tried-good]` or `[tried-bad]`.
5. Add any newly discovered ideas to `autoresearch-ideas.md`; do not narrate the whole backlog in chat.

## 3. Subagent Orchestration

Use subagents for bounded, independent work that reduces uncertainty while preserving the main agent's context.

Dispatch subagents for:

- Disjoint codebase scouting before selecting a hypothesis.
- Independent syntax checks or diff review after a change.
- Output analysis while a long harness run is in flight.
- Disjoint one-file edits when ownership is explicit and the main agent will integrate.

Do not dispatch subagents for:

- The canonical harness run.
- The keep/discard decision.
- Final reporting.
- Open-ended exploration without a line cap.

Every subagent assignment must include:

- Exact files or subsystem boundaries.
- The non-goal: do not run project-wide gates or formatters.
- A hard output cap, e.g. `return ≤15 lines`.
- `no logs, only actionable deltas`.

Template:

```text
task(agent="explore", tasks=[
  {
    id: "ScoutCore",
    description: "Scout core hot path",
    assignment: "Read src/core/algo.py only. Identify likely optimization targets. Return ≤15 lines, no logs, only actionable deltas. Do not edit files or run project-wide commands."
  },
  {
    id: "ScoutPipeline",
    description: "Scout pipeline hot path",
    assignment: "Read src/pipeline/stage2.py only. Identify likely optimization targets. Return ≤15 lines, no logs, only actionable deltas. Do not edit files or run project-wide commands."
  }
])
```

## 4. Async Harness Execution

Prefer structured async execution over blocking on a long command.

### Tier 1 — Preferred: `@tintinweb/pi-tasks`

Use pi-tasks when installed. It is preferred because it provides structured tasks with metadata, background execution, project-scoped file persistence, dependency relationships, and one-shot blocking output retrieval.

Pattern:

```text
TaskCreate(subject="Run full benchmark", description="<verify-or-harness-command>", activeForm="Running benchmark…")
TaskExecute(task_ids=["#1"], agentType="Explore")
# While it runs: inspect diffs, update ideas, or dispatch bounded output-analysis scouts.
TaskOutput(task_id="#1", block=true, timeout=<timeout-ms>)
TaskUpdate(task_id="#1", metadata={hypothesis: "<hypothesis>", result: "<metric>", decision: "<decision>"})
```

Use dependency management only when an experiment truly depends on another. Do not model dependencies just because tasks are sequential.

### Tier 2 — Fallback: native async bash

When pi-tasks is unavailable, use native async and wait once:

```text
bash(async: true, timeout: <seconds>, command: "<verify-or-harness-command>")
# While running: do independent analysis and update state files.
job(poll: ["<job-id>"])  # final blocking wait only
```

Never poll repeatedly to watch progress. Polling loops consume context without improving decisions. If a command emits large output, keep the `artifact://` reference and extract only the metric and failure signature.

## 5. Log Hygiene

- Paste metric lines, not full logs.
- Use `artifact://...` references for raw command output.
- Store repeated failure signatures in `autoresearch-decisions.tsv` or `autoresearch-ideas.md`.
- If a subagent returns too much text, summarize it into state files and avoid quoting it back.
- When a result is ambiguous, rerun or inspect the artifact; do not carry uncertainty forward as prose.

## 6. Graveyard Pattern

Failed approaches belong in `autoresearch-ideas.md`, not in conversation.

```markdown
# Ideas
- [untried] Replace repeated lookup with keyed index
- [tried-bad] Increase batch size (iter 4 — OOM)
- [tried-bad] Disable validation shortcut (iter 7 — guard failed)
- [tried-good] Cache parsed input metadata (iter 9 — -11% runtime)
```

Before selecting a hypothesis, scan the graveyard for similar failures. If the new idea is a variant of a failed approach, state what is materially different in `autoresearch-decisions.tsv`.

## 7. Handoff Compression

After several iterations with no metric movement, or before deliberately restarting with a fresh context, write a compact handoff such as `local://autoresearch_handoff.md` with:

```markdown
# Autoresearch Handoff
Goal: <goal>
Metric: <metric and direction>
Baseline: <value>
Best: <value> at iter <N>, commit <hash>
Current branch: <branch>
Last result: <value>, decision <keep|discard|crash>
Current hypothesis: <one sentence or none>
Do next: <one concrete next action>
Avoid: <top 3 tried-bad ideas with iteration numbers>
Artifacts: <links to latest relevant logs>
```

The handoff is a synopsis, not a transcript. Keep it short enough that a fresh agent can read it and immediately continue the loop.

## 8. Decision Ownership

The main agent owns integration and the keep/discard decision. A helper can say "metric line appears improved" or "diff is syntactically safe," but the main agent must compare metric direction, guard status, complexity cost, and project constraints before deciding.
