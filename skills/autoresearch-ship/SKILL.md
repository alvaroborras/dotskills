---
name: autoresearch-ship
description: Structured shipping workflow for code, releases, deployments, content, research candidates, and other deliverables. Use for ship, deploy, publish, launch, or release requests.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Take an authorized artifact from ready-ish to delivered through a mechanical checklist, safe preparation, dry-run, explicit external-action authorization, verification, and auditable logging.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/ship-workflow.md`. Shared repository safety, evidence, lifecycle, and
authorization rules override rollback or auto-approval examples.

## Workflow

1. Identify shipment type, target, mode, external side effects, and available tools.
2. Inventory current evidence and generate mechanically verifiable readiness gates.
3. Close preparation gaps through bounded safe changes and typed verification.
4. Dry-run whenever possible. A dry-run flag may automate readiness assessment but
   never authorizes push, deploy, publish, send, submit, charge, or remote deletion.
5. Obtain explicit user authorization for the concrete irreversible/external action
   unless that exact action was already explicitly requested.
6. Ship, verify the destination, and record immutable IDs and rollback limitations.
7. For verified research candidates, apply the dedicated research-candidate gate.

## Guardrails

- Never represent provisional or inconclusive research as promoted.
- Never perform remote deletion or destructive rollback without explicit request.
- Treat production, publication, billing, email, and submission as authorization
  boundaries rather than ordinary checklist steps.

</process>

<success_criteria>
- [ ] Shipment type, target, mode, and authorization are explicit.
- [ ] Mechanical readiness and dry-run gates pass.
- [ ] External actions match the user's authorization exactly.
- [ ] Post-ship verification and immutable identifiers are recorded.
- [ ] Research candidates satisfy provenance and promotion requirements.
</success_criteria>
