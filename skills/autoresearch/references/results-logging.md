# Campaign Ledger and Generated Views

Read `campaign-state.md` and `metric-evidence.md` first.

## One source of truth

Store each campaign under `.autoresearch/campaigns/<campaign-id>/`. The
append-only `events.jsonl` ledger is authoritative. `views/state.md`,
`views/results.tsv`, `views/decisions.tsv`, and `views/ideas.md` are regenerated
projections and must not be independently edited.

Use a project-native ledger instead when it provides equivalent identity,
lifecycle, immutability, and reporting guarantees.

## Event schema

Every event includes:

- `schema_version`, unique `event_id`, UTC `timestamp`;
- `campaign_id`, `authorization_epoch`, `event_type`, and `actor`;
- a structured `payload` appropriate to the event.

Evaluation payloads identify `iteration_id`, `experiment_id`, `evaluation_id`,
`stage`, `suite`, `backend`, `candidate_run_id`, `comparator_run_id`, candidate
and comparator metrics, typed outcome, delta, guard/constraint status, and
artifact references. Delta is candidate minus the explicitly named comparator;
metric direction determines whether it improved.

Decision payloads use `provisional`, `verified-keep`, `discard`, `inconclusive`,
`deferred`, `superseded`, or `stopped`, plus one-sentence rationale and evidence
run IDs.

## Generated state view

`views/state.md` contains only the active handoff:

- campaign ID, metric contract ID, lifecycle, authorization epoch;
- goal, scope, Git mode, and budget;
- baseline and verified incumbent run IDs/metrics;
- active hypothesis and run;
- latest typed result and decision;
- next authorized action;
- protected dirty paths and key artifact references.

On restart, read this view and validate it against the final ledger event and run
manifests. Regenerate it if inconsistent.

## Results view

Recommended columns:

```text
iteration_id experiment_id evaluation_id stage suite backend candidate_run_id comparator_run_id metric comparator_metric delta outcome guards constraints decision artifact_ref
```

Do not force evaluation variants such as holdouts and full confirmations into one
integer iteration. Preserve exact comparator identity and backend in every row.

## Ideas view

Ideas are `untried`, `active`, `tried-good`, `tried-bad`, or `historical`. Before
retrying a failed family, record what is materially different. Ideas never imply
authorization, especially after a stop.

## Write order

For each iteration:

1. append hypothesis/candidate events;
2. create immutable run manifest and append queued/started transitions;
3. append typed completion or failure;
4. append the parent-owned decision;
5. regenerate all views atomically;
6. verify view lifecycle/incumbent/run IDs against the ledger.

Flush the decision before launching another candidate.

## Compatibility

Legacy root-level state is read-only until explicitly migrated under the rules in
`campaign-state.md`. Never overwrite an existing campaign or compare values whose
metric contract identity is unknown.

## Reporting

At configured intervals, report baseline, verified incumbent, provisional active
candidate, typed outcome counts, keeps/discards/inconclusive results, budget, and
lifecycle. Reference artifacts rather than pasting logs. Final reports distinguish
verified evidence from diagnostics and list unperformed validation.
