# Campaign State, Lifecycle, and Retention

The machine-readable campaign and event formats are defined by
`../schemas/campaign.schema.json` and `../schemas/event.schema.json`. The reference
helper is `../scripts/campaign_state.py`; use its `init`, `register-run`, `append`,
`render`, `authorize`, `migrate-legacy`, `gc`, and explicit `gc-recover` commands
rather than hand-editing state.

## Namespaced layout

The default root is `.autoresearch/campaigns/<campaign-id>/`:

```text
campaign.json              immutable identity and metric contract ID
events.jsonl               authoritative append-only event ledger
runs/<run-id>/manifest.json
runs/<run-id>/status.json
views/state.md             generated compact handoff
views/results.tsv          generated evaluation view
views/decisions.tsv        generated decision view
views/ideas.md             generated backlog/graveyard view
artifacts/                 content-addressed or manifest-addressed payloads
locks/                     campaign and canonical-run leases
```

Use lowercase letters, digits, dots, underscores, and hyphens in campaign IDs.
Do not store canonical views at project root by default.

## Campaign and metric identity

`campaign.json` records at least:

- `schema_version`, `campaign_id`, `created_at`, `authorization_epoch`;
- goal, allowed scope, Git mode, iteration policy, and artifact policy;
- `metric_contract_id` and the complete metric contract;
- current lifecycle and stop reason;
- baseline/comparator identities and canonical stage;
- host/tool capability summary.

Derive `metric_contract_id` from the normalized metric definition, direction,
aggregation, denominator, suite/input identity, verifier/harness identity,
backend, environment requirements, and hard constraints. If any component changes,
close or pause the old campaign, create a new campaign ID and baseline, and never
compute cross-contract deltas.

## Append-only events

Append one structured event per state transition. Each event has `event_id`, UTC
timestamp, campaign ID, authorization epoch, event type, actor, and payload.
Useful event types include `campaign_created`, `authorized`, `hypothesis_added`,
`candidate_snapshotted`, `evaluation_queued`, `evaluation_started`,
`evaluation_finished`, `decision_recorded`, `promotion_started`,
`promotion_verified`, `stop_requested`, `stopped`, `paused`, and `completed`.

Append under a campaign lock and flush before launching subsequent work. Maintain
an atomic ledger-head receipt (event count, last event ID, and ledger hash) so
accidental truncation or tampering fails closed. Existing events are never rewritten. Generate all Markdown/TSV views from the ledger;
never hand-edit generated views as state. Any standalone logs named by a
specialized workflow are generated campaign views or report artifacts, never
competing sources of truth.

## Lifecycle and authorization

Valid lifecycle values are `RUNNING`, `PAUSED`, `STOP_REQUESTED`, `STOPPED`, and
`COMPLETE`.

Before any mutation, launch, holdout, or follow-up validation, read lifecycle and
authorization epoch from the ledger:

- `RUNNING`: authorized work may continue within budget.
- `PAUSED`: do not launch work until explicitly resumed.
- `STOP_REQUESTED`: launch nothing new; finish or cancel only work authorized by
  the stop instruction, reconcile artifacts, then write `STOPPED`.
- `STOPPED` or `COMPLETE`: no experiment, benchmark, holdout, or follow-up
  validation is authorized.

Only a new explicit user request may increment `authorization_epoch` and move a
stopped campaign to `RUNNING`, or create a new campaign. Record a durable
`authorization_ref` pointing to that request; a helper invocation without this
evidence must fail. Backlog entries are
historical memory, not authorization.

## Budgets and iteration accounting

Pre-register whether the budget counts hypotheses, candidate snapshots,
evaluations, or decisions. Default: one iteration is consumed when an in-scope
candidate is snapshotted for evaluation; syntax fixes before snapshot do not
consume another iteration, while a materially different candidate does. Log
crashes and infrastructure failures without silently replacing them with extra
unbounded attempts. Record separate `iteration_id`, `experiment_id`, and
`evaluation_id`.

## Legacy compatibility

If root-level `autoresearch-results.tsv`, `autoresearch-state.md`,
`autoresearch-decisions.tsv`, or `autoresearch-ideas.md` exist:

1. discover and report them without editing;
2. do not compare their values until a metric contract can be reconstructed;
3. migrate only on explicit request;
4. copy originals into `<campaign>/legacy/` with hashes and append a migration
   event; never delete or rewrite originals automatically.

## Retention policy

Default policy:

- retain ledgers, manifests, decisions, promoted candidates, canonical baselines,
  named comparators, and final audits indefinitely;
- mark unreferenced raw screen artifacts eligible after 14 days;
- mark failed or incomplete unreferenced artifacts eligible after 7 days;
- emit a storage warning at 10 GiB per project;
- deduplicate payloads by content hash when practical;
- garbage collection is dry-run-only by default and lists path, size, age, hash,
  reason, and references;
- delete eligible artifacts only after an explicit `gc --apply` action;
- before deletion, record intent, atomically quarantine each candidate, verify its
  recorded content hash again, and append a durable delete-commit event; then delete
  and append finalization. Interrupted pre-delete work stays quarantined and requires
  explicit `gc-recover --mode restore`; after a durable delete commit, partial
  deletion is reconciled with `gc-recover --mode finalize`, and remains auditable.

Never garbage-collect an artifact referenced by a retained manifest, ledger event,
promotion audit, sealed evaluation, or active run.
