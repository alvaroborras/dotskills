# Autoresearch skill family

The nine `autoresearch-*` skills share the normative contract in
`references/shared-contract.md`. Sibling skills locate it through
`../autoresearch/references/shared-contract.md` relative to their own `SKILL.md`.
Install the family together; a sibling must fail clearly rather than silently use
stale inline behavior when the core contract is missing.

JSON Schemas for campaigns, events, metric contracts, immutable run manifests, and
typed verification results live under `schemas/`.

Campaign state defaults to `.autoresearch/campaigns/<campaign-id>/`. Use
`scripts/campaign_state.py` to initialize namespaced state, seal and register run
manifests, append lifecycle/results/decisions, regenerate views, copy legacy state
explicitly, and plan/apply artifact garbage collection. Run-producing events require
the originating `--event-epoch`; `register-run` is the only queue path. The helper
does not execute benchmarks or mutate Git.

Validate the installed family with:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

Vendored `references/upstream-*.md` files are historical attribution only and are
excluded from normative safety scans. A timestamped pre-refactor backup should be
stored outside the skill discovery tree so it cannot create duplicate skills.
