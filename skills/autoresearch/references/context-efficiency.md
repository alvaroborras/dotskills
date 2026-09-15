# Context Efficiency and Artifact Hygiene

## Working set

Keep only the active hypothesis, current verified incumbent, current run identity,
immediate blocker, and next action in conversation. Store authoritative history in
the event ledger and immutable artifacts. Generated `views/state.md` is the compact
handoff, not an additional source of truth.

## Initial read budget

Start with:

1. the shared contract and active skill workflow;
2. project instructions and campaign `campaign.json`;
3. `views/state.md`, latest relevant decisions, and active run manifest;
4. only the source and tests needed for the current hypothesis.

Do not begin by loading every historical log or reference. Hash or note unchanged
references and do not reread them without a reason.

## Checkpoint after every decision

After keep, discard, crash, cancellation, or inconclusive evidence:

1. append the decision event;
2. regenerate compact views;
3. record the newly verified fact and next action;
4. release completed run output from conversation;
5. retain only artifact paths and failure signatures needed later.

## Rebase thresholds

Create a fresh compact handoff when any of these occurs:

- the active context has accumulated several full logs or large source dumps;
- multiple completed phases are still being carried conversationally;
- the same unchanged file is about to be reread to recover a settled fact;
- a context compaction/restart is imminent;
- five iterations or a project-configured threshold have completed.

The handoff states campaign/lifecycle/epoch, metric contract ID, incumbent and
baseline run IDs, iteration budget, active hypothesis/run, next action, top
rejected directions, dirty-path protection, and artifact references. On restart,
read that handoff and manifests rather than reconstructing history from chat.

## Subagents and output

Use bounded subagents only when they reduce uncertainty. Require concise actionable
findings and verify their claims. Do not paste child logs into conversation. Child
output is not durable campaign state until the parent records a verified event.

## Artifact hygiene

Write raw output directly to run artifacts; do not route large transcripts through
conversation. Prefer bounded summaries and content hashes. Track project storage
size, deduplicate immutable payloads, and apply the retention policy in
`campaign-state.md`. Garbage collection remains dry-run until explicitly applied.

## Consistency audit

Before a progress or final report, read generated state and verify that lifecycle,
authorization epoch, incumbent, metric contract, run IDs, and claims agree with the
ledger and canonical reporter. Resolve divergence at the ledger/view generator,
not by patching prose copies.
