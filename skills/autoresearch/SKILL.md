---
name: autoresearch
description: Autonomous goal-directed iteration for measurable improvements. Use this whenever the user wants an autoresearch loop, repeated modify -> verify -> keep/discard cycles, bounded or unbounded experiments, or says to work autonomously toward a numeric metric.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Run an autonomous improvement campaign against a mechanical metric: establish a compatible baseline, test one focused candidate at a time, promote only with sufficient evidence, preserve immutable provenance, and continue until the authorized stop condition.
</objective>

<process>

## Source of truth

Before execution read:

1. `references/shared-contract.md` and the shared references it requires;
2. `references/autonomous-loop-protocol.md`;
3. `references/results-logging.md` and `references/harness-discipline.md`.

`references/upstream-skill.md` and `references/upstream-command.md` are retained
for attribution and historical context only. They are non-normative and must not
override the shared contract.

## Workflow

1. Route planning, debugging, fixing, security, shipping, scenario exploration,
   prediction, or documentation requests to the matching sibling skill.
2. Discover available tools and project-native research infrastructure. Do not
   assume agent names, async APIs, or clarification tools.
3. Resolve Goal, Scope, Metric, Direction, Verify, constraints, evidence stages,
   and iteration/stop policy. If material fields are missing, inspect for safe
   defaults and ask only blocking questions in a compact batch.
4. Select a safe Git mode and protect pre-existing work. Reuse a project-native
   durable runner when it satisfies the shared contract.
5. Create or resume `.autoresearch/campaigns/<campaign-id>/`; read lifecycle and
   authorization before any mutation or evaluation.
6. Establish a typed, compatible baseline and follow the loop: review -> state
   hypothesis -> isolate candidate -> smoke -> evaluate -> compare -> decide ->
   append event -> regenerate views -> repeat.
7. Use the configured evidence ladder. A screen result is provisional; only a
   completed promotion audit creates `verified-keep`.
8. In bounded mode stop at the registered budget. In unbounded mode continue
   without asking whether to proceed, but honor user interruption immediately
   through the durable stop protocol.

## Execution discipline

- The parent/controller owns canonical harness execution, comparison, promotion,
  and final reporting.
- Long runs use the safest available durable mechanism and immutable run manifest.
  Do not poll repeatedly and do not use subagents as benchmark watchers.
- Verification fails closed and returns typed outcomes. Never turn a crash,
  timeout, or parse error into a numeric metric.
- Compile and evaluate frozen candidate snapshots, not mutable live source paths.
- Keep conversational output compact; durable facts belong in the campaign
  ledger, generated views, and run artifacts.

## Guardrails

- Never stage or mutate unrelated user work.
- Never use destructive Git recovery or bypass repository hooks automatically.
- Never compare incompatible contract IDs, suites, backends, or harnesses.
- Never launch work from a `STOPPED` or `COMPLETE` campaign without a new explicit
  authorization epoch.

</process>

<success_criteria>
- [ ] Campaign and metric contracts are complete and namespaced.
- [ ] Baseline and every evaluation have typed outcomes and immutable identities.
- [ ] Each candidate is atomic, isolated, mechanically checked, and logged once.
- [ ] Promotion follows the registered evidence ladder and constraints.
- [ ] Views are generated from one append-only ledger.
- [ ] Stop/resume authorization, repository safety, and retention policy are honored.
</success_criteria>
