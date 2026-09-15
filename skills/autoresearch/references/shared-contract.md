# Shared Autoresearch Contract

This is the normative contract for every `autoresearch-*` skill. Read it before a
skill-specific workflow. The sibling skills locate it at
`../autoresearch/references/shared-contract.md` relative to their own `SKILL.md`.

## Authority

This contract is normative. Vendored upstream files are explicitly
**NON-NORMATIVE**.

Apply instructions in this order:

1. host safety boundaries, available capabilities, and higher-priority instructions;
2. the user's current request and explicit authorization;
3. repository-local instructions;
4. this shared contract and the references it links;
5. the active skill's workflow;
6. vendored upstream material, which is provenance only.

Authorization never creates an unavailable capability or overrides a host safety
boundary. A lower layer cannot authorize destructive Git operations, an external
side effect, a new experiment after a stop, or use of a tool that is unavailable.
When a skill-specific workflow conflicts with this contract, this contract wins.

## Required references

Load only the references needed for the operation:

- [Runtime and repository safety](runtime-safety.md)
- [Campaign state, lifecycle, and retention](campaign-state.md)
- [Metric and evidence contract](metric-evidence.md)
- [Immutable execution and harness discipline](execution-contract.md)
- [Context efficiency](context-efficiency.md)

The core improvement loop also reads `autonomous-loop-protocol.md`. Planning
reads the sibling plan workflow. Shipping a verified research result reads the
`research-candidate` section of the ship workflow.

## Non-negotiable invariants

- Verification fails closed. Failure is never replaced by a numeric metric.
- A legitimate metric value of zero remains valid when the domain permits it.
- Only compatible candidate and comparator evaluations may produce a delta.
- A screen result is provisional; only the configured promotion gate can keep a
  candidate as verified.
- Campaign lifecycle and authorization are durable. `STOPPED` and `COMPLETE`
  prohibit new evaluations until an explicit user request creates a new epoch.
- Candidate work never justifies destructive recovery or loss of unrelated work.
- Canonical benchmark truth comes from validated artifacts, not a watcher,
  subagent summary, process exit alone, or the newest pathname.
- Child workers are read-only by default. The controller may delegate a bounded
  candidate mutation only inside an isolated workspace with explicit scope,
  ownership, and verification; children never decide canonical truth, promote,
  mutate controller-owned state, or perform external actions.
- The parent/controller owns experiment selection, comparison, promotion, and
  final reporting.
- One append-only event ledger is authoritative. Markdown and TSV files are
  generated views, not independent sources of truth.

## Default campaign location

Use `.autoresearch/campaigns/<campaign-id>/`. If a project already has a durable
research system that satisfies this contract, use it rather than creating a
parallel ledger. Legacy root-level `autoresearch-*.{md,tsv}` files are discovered
read-only and are migrated only by an explicit migration action.

## Completion language

Use these terms precisely:

- `provisional`: passed a noncanonical screen;
- `inconclusive`: evidence disagrees or is insufficient;
- `deferred`: valid candidate intentionally not promoted;
- `verified-keep`: all configured promotion gates passed;
- `discard`: valid evidence rejects the candidate;
- `superseded`: previously verified candidate replaced by a later one;
- `stopped`: no further work is authorized in the current epoch.

Never describe a provisional or inconclusive result as retained, final, or an
improvement to the canonical metric.
