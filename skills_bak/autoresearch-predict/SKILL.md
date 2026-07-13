---
name: autoresearch-predict
description: Multi-persona swarm analysis before you act. Use this whenever the user wants multiple expert perspectives, pre-debug prediction, pre-ship review, adversarial debate, or asks what several specialists would notice.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Analyze a scoped codebase through multiple expert personas, capture independent findings, run structured debate, synthesize consensus, preserve minority views, and optionally hand off ranked hypotheses to downstream skills.
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
1. Read `references/predict-workflow.md` before execution and use it as the canonical swarm workflow.
2. If scope, goal, or depth is missing, ask the batched predict setup with the current clarification tool. Ignore upstream tool notes that do not match the current environment.
3. Use `task` with `explore` or `quick_task` when the workflow calls for helper analysis passes. Keep the knowledge-file pattern from the reference.
4. Preserve Devil's Advocate behavior and anti-herd checks. Minority findings stay visible even when consensus is strong.
5. If the user requested chaining, load the matching sibling skill (`autoresearch-debug`, `autoresearch-security`, `autoresearch-fix`, `autoresearch-ship`, or `autoresearch-scenario`) and pass the hypothesis queue in context.

## Guardrails
- Predictions are priors, not conclusions. Empirical downstream loops always overrule swarm consensus.
- Keep evidence grounded in real file:line references.
- Honor token and scope limits; narrow scope when the swarm would otherwise become too diffuse.

</process>

<success_criteria>
- [ ] Scope, goal, and depth are resolved.
- [ ] Knowledge files are built or refreshed.
- [ ] Multiple personas analyze independently and debate openly.
- [ ] Consensus, minority findings, and anti-herd checks are recorded.
- [ ] Reports and optional handoff artifacts are written to the predict output folder.
</success_criteria>
