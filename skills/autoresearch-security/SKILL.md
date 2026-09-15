---
name: autoresearch-security
description: Autonomous security audit with STRIDE, OWASP, and adversarial analysis. Use for threat modeling, vulnerability hunting, red-team review, or risk-focused autoresearch.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Map assets and trust boundaries, test one authorized attack hypothesis at a time, classify evidence-backed findings, and produce an auditable security report.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/security-workflow.md`. Shared authorization, runtime, repository,
campaign, and evidence rules override host-specific examples.

## Workflow

1. Resolve scope, authorization, environment boundaries, safe test limits, and
   reporting sensitivity. Default to read-only analysis.
2. Map assets, entry points, trust boundaries, attacker capabilities, OWASP and
   STRIDE coverage before adversarial testing.
3. Test one bounded vector per iteration without affecting real users, production,
   billing, or third-party systems unless explicitly authorized.
4. Require code evidence, reproducible scenario, impact, severity, mapping,
   confidence, and remediation for every finding.
5. Parent-verify delegated findings. If fixes are authorized, hand them to the fix
   workflow under a separate safe modification scope.

## Guardrails

- Do not report purely theoretical vulnerabilities as confirmed.
- Never broaden authorization from a backlog item or prior campaign.
- Keep sensitive artifacts namespaced with appropriate permissions and retention.
- Honor durable stop state before every active test.

</process>

<success_criteria>
- [ ] Assets, boundaries, authorization, and attack surface are explicit.
- [ ] Tests are bounded, typed, and reproducible.
- [ ] Findings are severity-ranked and evidence-backed.
- [ ] OWASP/STRIDE coverage and untested areas are reported honestly.
</success_criteria>
