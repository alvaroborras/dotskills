---
name: autoresearch-debug
description: Autonomous bug hunting with the scientific method. Use this whenever the user wants root-cause analysis, broad bug hunting, hypothesis-driven debugging, or says debug/autoresearch the failures.
license: MIT
compatibility: agents, opencode, omp
---

<objective>
Investigate bugs iteratively: gather symptoms, map the error surface, form a falsifiable hypothesis, test it, classify what was learned, log it, and keep going until the user stops or the iteration budget is exhausted.
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
1. Read `references/debug-workflow.md` before execution and follow it closely.
2. If scope or symptom is missing, do the recommended pre-scan and ask the single batched debug setup with the current clarification tool.
3. Work one hypothesis at a time. Record what you tested, what evidence you found, and whether the hypothesis was confirmed, disproven, or inconclusive.
4. Use code evidence with file:line locations for every confirmed bug. Keep disproven hypotheses too; they are part of the investigation memory.
5. If the user asked to fix findings or the workflow says to chain into fixing, load `autoresearch-fix` with the discovered findings in context.

## Guardrails
- Do not jump to fixes before you understand the bug.
- Prefer reproducible experiments over guesswork.
- Keep each investigation iteration atomic so you know what changed your understanding.

</process>

<success_criteria>
- [ ] Symptoms or autonomous scan results are captured.
- [ ] The error surface is mapped before deep testing.
- [ ] Hypotheses are specific and testable.
- [ ] Confirmed findings include evidence, severity, and reproduction notes.
- [ ] Results are logged and ready for optional handoff to `autoresearch-fix`.
</success_criteria>
