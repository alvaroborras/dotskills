---
name: autoresearch-security
description: Autonomous security audit with STRIDE, OWASP, and adversarial analysis. Use this whenever the user wants a security sweep, threat model, vulnerability hunt, red-team style review, or autoresearch focused on risk.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Run a structured security audit: map assets and trust boundaries, build a threat model, test one attack vector per iteration, classify findings, and produce a report with code-backed evidence.
</objective>

<process>

## Harness translation
Adapted from Udit Goenka's MIT-licensed autoresearch project. Apply these translations everywhere:
1. When upstream docs say `AskUserQuestion`, use the current environment's clarification tool and batch setup questions exactly as requested.
2. When upstream docs say to switch to another `/autoresearch:...` command, load the sibling skill with the matching name through the current environment's skill-loading mechanism.
3. Ignore any upstream `ToolSearch` instructions or tool-availability notes that do not match the current environment.
4. Use `task` with the `explore` agent for bounded codebase scouting and `task` with `quick_task` for small independent checks. Every subagent assignment must include a line cap and ask for actionable deltas only.
5. Host repo safety rules win over the upstream docs: never revert unrelated user changes, never use destructive git commands unless explicitly requested, and stage only explicit files you changed.

## Source of truth
Read the bundled reference files for this skill before executing. They preserve the upstream autoresearch workflow details that do not fit comfortably in this summary.

## Workflow
1. Read `references/security-workflow.md` before execution and use it as the source of truth for the audit flow.
2. If scope or focus is missing, scan the codebase first and then ask the single batched security setup with the current clarification tool.
3. Keep the default mode read-only. If the user explicitly requests `--fix`, treat that as permission to hand findings into `autoresearch-fix` or remediate inline.
4. Every finding needs code evidence, a plausible attack scenario, severity, OWASP mapping, STRIDE mapping, and confidence.
5. If you reach CI/CD examples in the reference files, treat the old Claude-specific snippets as historical examples and adapt them to the current environment instead of copying them verbatim.

## Guardrails
- Do not report purely theoretical vulnerabilities without code evidence.
- Aim for coverage across OWASP and STRIDE, not just a long list of low-quality findings.
- Keep security reports in the structured `security/` output folder described by the reference.

</process>

<success_criteria>
- [ ] Assets, trust boundaries, and attack surfaces are mapped.
- [ ] The audit iterates through attack vectors methodically.
- [ ] Findings are severity-ranked and evidence-backed.
- [ ] Coverage progress is tracked across OWASP and STRIDE.
- [ ] A final security report and iteration log are produced.
</success_criteria>
