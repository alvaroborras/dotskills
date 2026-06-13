# Discovery-Scale Research Lanes

Use this for broad discovery, state-of-the-art surveys, or technology
selection. For narrow slice facts, use `research.md`.

## Orchestrator Rules

First write a research brief: question, decision it informs, constraints, and
what "answered" means. Design lanes for this topic; do not use all lanes by
default. Keep each lane to about five subjects and give it a search budget.

Every lane prompt starts with:

```text
You are a web research agent. Answer ONE assigned objective. Do not write code
or recommendations; judgment belongs to the orchestrator. Budget: <N> searches.
If two consecutive searches yield no new load-bearing facts, stop and return.
Every finding carries source URL, source date, exact figure or short quote, and
confidence: high primary source, med reputable secondary, low single blog/forum.
Prefer primary sources. Report disagreements. Write NOT FOUND when evidence is
missing. End with the 2-3 findings most likely to change a design decision.
```

## Lane Types

Scout: map terminology, load-bearing systems/papers/repos/vendors, recurring
experts, rich source classes, and natural fault lines. Use for brainstorm-scale
topics before final lane design.

Academic: find recent surveys, frontier papers, influential seeds, and code
availability. Prefer arXiv, Semantic Scholar, OpenReview, OpenAlex, and primary
paper pages. Score by relevance, recency, citation velocity, venue signal, and
code availability.

Popular repos: find adopted libraries with evidence beyond stars. Record
dependents, registry downloads, last release, issue health, and whether stars
are proportional to forks/issues/dependents.

Emerging repos: find recent work with sustained activity, maintainer response,
tests/releases, paper or reputable-org backing, and proportional growth. Flag
single-contributor or README-only hype.

Production patterns: inspect 2-3 production libraries adjacent to the design.
Read public API, one happy-path flow, tests around the feature, closed issues,
and merged PRs. Extract API ergonomics, error handling, extension points, and
testing patterns.

General web: official docs/changelogs, expert posts, postmortems, failure
reports, comparisons, pricing, limits, and operational constraints. Treat SEO
lists as pointers only.

Expert opinion: second wave after first results identify relevant people.
Report positions, dates, affiliation/conflict-of-interest, and disagreements.
Expert opinions do not count as factual verification.

## Synthesis

Verify load-bearing claims with at least two independent sources where
possible. Mark claims VERIFIED, UNVERIFIED, DISPUTED, or SUSPICIOUS. Actively
search for criticism or counterexamples for the most important claims.

Write `docs/research/<topic>.md` with answer first, brief, major findings,
decision implications, disputes, expert positions, open questions, and dated
citations. Commit the report. If it feeds a build slice, distill it into
`docs/prd/<slice>.md`.
