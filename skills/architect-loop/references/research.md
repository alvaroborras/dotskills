# Slice-Level Research Fan-Out

Use this only when a slice depends on unfamiliar external APIs, libraries,
versions, operational constraints, or a user explicitly asks for research.

## Fan Out

Create 3-5 narrow, non-overlapping questions. Cover different angles such as
official docs, changelog/breaking changes, failure reports, alternatives,
security, or operational constraints.

Dispatch one read-only researcher per question:

```bash
mkdir -p .architect/research
codex exec -C <repo-root> --sandbox read-only -c web_search="live" \
  -m gpt-5.5 -c model_reasoning_effort="medium" \
  -o .architect/research/<NN>-<topic>.md \
  - < .architect/research/<NN>-<topic>.prompt.md
```

Research uses medium effort — read-only gathering benefits less from deep
reasoning than from breadth. Reserve high for schema-critical or
security-sensitive research.

## Research Block Template

```text
You are a web research agent. Answer ONE question. Do not write code, do not
make recommendations; judgment belongs to the architect reading your output.

QUESTION: <one narrow question>

OUTPUT FORMAT:
- Markdown findings.
- Every finding has source URL, source date if shown, exact figure or short
  quote, and confidence tag: high = primary source, med = reputable secondary,
  low = single blog/forum.
- Prefer primary sources: official docs, changelogs, release notes, source
  code, papers.
- Record exact version numbers and dates.
- When sources disagree, report the disagreement; do not resolve it.
- If you cannot find evidence, write NOT FOUND. Do not infer from memory.
- End with the 2-3 findings most likely to change implementation.
```

## Gather And Verify

Read all findings. Extract load-bearing claims: facts the spec depends on, such
as API shape, limits, version constraints, deprecations, or security behavior.
Verify each against a second independent source or the live dependency itself.
Discard low-confidence single-source claims or mark them as open questions.

Write `docs/prd/<slice>.md` with:

- Problem and decision.
- Requirements and non-goals.
- Verified facts with citations.
- Open questions for the human or builder PHASE 0.

Commit the PRD. Keep raw research under `.architect/research/` and add
`.architect/` to `.gitignore` if needed.
