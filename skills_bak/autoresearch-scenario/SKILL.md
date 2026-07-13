---
name: autoresearch-scenario
description: Scenario-driven exploration of use cases, edge cases, failures, and threat paths. Use this whenever the user wants to explore scenarios, generate test cases, map user journeys, or ask what could go wrong.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Start from a seed scenario, decompose it into exploration dimensions, generate one concrete situation at a time, classify and expand it, and keep iterating for breadth and depth.
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
1. Read `references/scenario-workflow.md` before execution and follow its adaptive setup and loop rules.
2. If the seed scenario is missing or too vague, ask the batched scenario setup with the current clarification tool. Ignore upstream tool notes that do not match the current environment.
3. Use the domain-specific dimension priorities from the reference when the domain is clear or provided.
4. Generate one concrete situation per iteration, classify it before keeping it, and expand high-value cases into edge cases or failure modes.
5. If the scenario results need empirical follow-up, hand off to sibling skills like `autoresearch-debug` or `autoresearch-security` with the generated situations in context.

## Guardrails
- Avoid vague scenarios. Every kept situation should have an actor, trigger, flow, and expected outcome.
- Rotate dimensions instead of overproducing happy paths.
- Keep deduplication strict so the score reflects real coverage.

</process>

<success_criteria>
- [ ] The seed scenario and domain are clear.
- [ ] Relevant dimensions are identified and explored.
- [ ] Generated situations are concrete and classified.
- [ ] High-value expansions produce edge cases or threat paths.
- [ ] Scenario outputs and logs are written to the structured output folder.
</success_criteria>
