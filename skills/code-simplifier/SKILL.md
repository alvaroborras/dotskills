---
name: code-simplifier
description: Simplify recently modified code for clarity, consistency, and maintainability without changing behavior. Use after writing or editing code, or when asked to refactor or clean up code. Keep scope to touched files unless broader review is requested.
---

# Code Simplifier

Refine code so it is easier to read, reason about, and maintain while preserving exact functionality.

## Non-Negotiable Rules

1. Preserve behavior exactly. Do not change outputs, side effects, runtime contracts, or error semantics.
2. Preserve public interfaces unless the user explicitly requests breaking changes.
3. Keep scope to recently modified code by default.
4. Follow project standards in `AGENTS.md` and local repo instructions first, then existing conventions.
5. Respect higher-priority instructions from system, developer, and user messages.

## Project Standards

Apply the repo's language-specific conventions. When relevant:

- Prefer clarity over brevity.
- Use guard clauses to flatten deep nesting.
- Keep naming explicit and domain-meaningful.
- Avoid nested ternaries and dense one-liners.
- Extract repeated literals or logic only when it improves readability.
- Keep comments only when they explain intent, constraints, or surprising behavior.

## Simplification Priorities

Prioritize high-impact, low-risk improvements:

- Flatten deep nesting with early returns.
- Remove duplicate logic, dead branches, and redundant abstractions.
- Rename unclear identifiers to improve readability.
- Consolidate related logic while keeping concerns separated.
- Replace magic values with named constants when that improves comprehension.
- Tighten control flow so the happy path is easier to follow.

## Do Not

- Do not broaden scope to unrelated files for style-only churn.
- Do not introduce clever rewrites that reduce readability.
- Do not remove abstractions that genuinely improve organization.
- Do not add dependencies for cosmetic refactors.
- Do not change observable behavior in the name of cleanup.

## Scope Discovery

Use this order:

1. Files or regions explicitly requested by the user.
2. Files touched in the current session.
3. Current git diff, when available.

If no clear target exists, ask one focused clarifying question before broad changes.

## Refinement Workflow

1. Identify candidate sections in scope.
2. Define behavior boundaries: inputs, outputs, side effects, and error paths.
3. Apply the smallest set of edits with the largest readability gain.
4. Run a behavior-parity self-check:
   - Same outputs for the same inputs.
   - Same side effects and execution order.
   - Same async behavior and error propagation.
   - Same public types and interfaces.
5. Run existing tests, lint, and typecheck when available.
6. Report only meaningful simplifications and verification results.

Operate proactively: after code is written or modified, run this simplification pass on touched code unless instructed otherwise.
