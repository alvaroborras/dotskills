---
name: autoresearch-learn
description: Autonomous codebase learning and documentation generation. Use this whenever the user wants docs from scratch, docs refreshed after changes, a documentation health check, or a quick project summary grounded in the code.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Understand a codebase, generate or update evidence-grounded documentation, validate it mechanically, and retain a concise auditable learning record.
</objective>

<process>

## Source of truth

Read `../autoresearch/references/shared-contract.md` relative to this skill, then
`references/learn-workflow.md`. Apply shared capability, delegation, state,
lifecycle, and context rules to every mode.

## Workflow

1. Discover available tools and classify init, update, check, or summarize mode.
2. Inspect project instructions, entry points, tests, configuration, and existing
   docs before asking only genuinely blocking questions.
3. Use bounded read-only scouts when helpful, verify their citations, and enforce
   pre/post workspace checks.
4. Generate project-specific documentation from real symbols and commands. Store
   iterative state under a namespaced campaign; export final docs where requested.
5. Validate references, links, commands, configuration keys, size limits, and
   source consistency mechanically. Record residual warnings honestly.

## Guardrails

- Do not generate generic boilerplate or claim unverified behavior.
- Do not let read-only helpers modify shared files.
- Do not overwrite user documentation outside authorized scope.
- Honor context checkpoints and durable stop state.

</process>

<success_criteria>
- [ ] Project structure and mode are correctly classified.
- [ ] Documentation is grounded in verified code evidence.
- [ ] Mechanical validation passes or remaining warnings are explicit.
- [ ] Campaign state and reports are namespaced and auditable.
</success_criteria>
