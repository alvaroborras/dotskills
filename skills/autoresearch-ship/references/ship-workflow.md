# Ship Workflow  /autoresearch:ship

Read `../../autoresearch/references/shared-contract.md` first. Its authorization,
repository-safety, campaign, evidence, and lifecycle rules override conflicting
examples below.

For campaign runs, `events.jsonl` is authoritative. Named TSV/Markdown logs below
are rendered views or report artifacts under the campaign directory; do not append
them as independent state.

Universal shipping workflow that applies autoresearch loop principles to the last mile  taking anything from "done" to "deployed/published/delivered." Works for code, content, marketing, sales, research, design, or any artifact that needs to reach its audience.

**Core idea:** Shipping has a universal pattern regardless of domain. Identify  Checklist  Prepare  Dry-run  Ship  Verify  Log.

## Trigger

- User invokes `/autoresearch:ship`
- User says "ship it", "deploy this", "publish this", "launch this", "release this"
- User says "get this out the door", "push to prod", "send this out", "go live"

## Loop Support

Works with bounded mode for iterative pre-ship preparation:

```
# Ship with automatic preparation loop
/autoresearch:ship

# Bounded preparation  iterate N times before shipping
/autoresearch:ship
Iterations: 10

# Ship specific artifact
/autoresearch:ship
Target: src/features/auth/**
Destination: production
```

## PREREQUISITE: Interactive Setup (when invoked without flags)

**Blocking prerequisite:** If shipment type or target remains unresolved after inspection, use the current environment's available clarification mechanism before preparation.

**Single batched call  all 3 questions at once:**

When clarification is required, batch these three questions in one interaction when supported:

| # | Header | Question | Options (from context scan) |
|---|--------|----------|----------------------------|
| 1 | `What` | "What are you shipping?" | "Code PR", "Release / version tag", "Deployment to production", "Blog post / documentation" |
| 2 | `Mode` | "How should I ship it?" | "Full workflow (checklist, dry-run, authorization gate, ship, verify)", "Dry-run only (validate without shipping)", "Checklist only (just check readiness)", "Automate readiness checks (external action still requires authorization)" |
| 3 | `Monitor` | "Post-ship monitoring?" | "No monitoring", "5 minutes", "10 minutes", "30 minutes" |

**IMPORTANT:** Always ask all questions in a single call  never one at a time.

Flags may resolve preparation details but never imply an external target or authorize
delivery. Skip clarification only when shipment type, exact target, action, and desired
stopping point are all unambiguous; otherwise block at the authorization gate.

## Architecture

```
/autoresearch:ship
   Phase 1: Identify (what are we shipping?)
   Phase 2: Inventory (what's the current state?)
   Phase 3: Checklist (domain-specific pre-ship gates)
   Phase 4: Prepare (autoresearch loop until checklist passes)
   Phase 5: Dry-run (simulate the ship action)
   Phase 6: Ship (execute the actual delivery)
   Phase 7: Verify (post-ship health check)
   Phase 8: Log (record the shipment)
```

## Phase 1: Identify  What Are We Shipping?

Auto-detect the shipment type from context, or ask the user.

**Detection algorithm:**
```
FUNCTION detectShipmentType(context):
  # Check explicit user input first
  IF user specifies type  USE IT

  # Auto-detect from context
  IF git diff has staged changes OR user mentions "deploy/release/merge":
    IF has Dockerfile/k8s/deploy configs  "deployment"
    IF has open PR or branch changes  "code-pr"
    ELSE  "code-release"

  IF context mentions "blog/article/post" OR target files are *.md in content/:
     "content"

  IF context mentions "email/campaign/newsletter":
     "marketing-email"

  IF context mentions "landing page/ad/social":
     "marketing-campaign"

  IF context mentions "deck/proposal/pitch/quote":
     "sales"

  IF context mentions "paper/report/analysis/findings":
     "research"

  IF context mentions "assets/mockup/design/figma":
     "design"

  # Default: ask user
   ASK "What are you shipping? (code/content/marketing/sales/research/design/other)"
```

**Output:** ` Phase 1: Identified shipment  [type]: [brief description]`

## Phase 2: Inventory  Current State Assessment

Scan the artifact and its environment to understand readiness.

**For each shipment type, gather:**

| Type | Inventory Checks |
|------|-----------------|
| code-pr | Changed files, test status, lint status, PR description, review status |
| code-release | Version tag, changelog, migration status, dependency audit |
| deployment | Build status, env vars, infra health, rollback plan |
| content | Word count, links checked, images present, metadata/frontmatter |
| marketing-email | Subject line, preview text, links, unsubscribe, CAN-SPAM compliance |
| marketing-campaign | Assets ready, tracking pixels, UTM params, A/B variants |
| sales | Pricing current, branding consistent, contact info, CTA clear |
| research | Citations complete, methodology documented, data sources linked |
| design | Formats exported, responsive variants, accessibility checked |

**Output:** ` Phase 2: Inventory complete  [N] items assessed, [M] gaps found`

## Phase 3: Checklist  Domain-Specific Pre-Ship Gates

Generate a mechanical checklist based on shipment type. Every item must be verifiable (pass/fail).

### Code Checklists

**code-pr:**
- [ ] All tests pass (`npm test` / `pytest` / language-specific)
- [ ] Lint clean (no errors, warnings acceptable)
- [ ] Type check passes (if applicable)
- [ ] PR description explains the "why"
- [ ] No secrets in diff (`git diff --cached | grep -i "password\|secret\|api_key"`)
- [ ] No TODO/FIXME in new code (or documented as intentional)
- [ ] Breaking changes documented (if any)
- [ ] Reviewer assigned or review complete

**code-release:**
- [ ] All code-pr checks pass
- [ ] Version bumped in package.json/pyproject.toml/Cargo.toml
- [ ] CHANGELOG updated with release notes
- [ ] Migration scripts tested (if DB changes)
- [ ] Dependency audit clean (`npm audit` / `pip audit`)
- [ ] Proposed tag name matches the version (creation occurs only in Phase 6)

**deployment:**
- [ ] All code-release checks pass
- [ ] Build succeeds in CI
- [ ] Environment variables set for target env
- [ ] Health check endpoint responds
- [ ] Rollback plan documented
- [ ] Monitoring/alerting configured
- [ ] Feature flags set correctly

### Content Checklists

**content (blog/docs):**
- [ ] Title present and descriptive
- [ ] No broken links (internal or external)
- [ ] Images have alt text
- [ ] Meta description present (160 chars)
- [ ] No placeholder text ("Lorem ipsum", "TODO", "TBD")
- [ ] Grammar/spell check passes
- [ ] Publish date set
- [ ] Author attribution present

### Marketing Checklists

**marketing-email:**
- [ ] Subject line present (60 chars recommended)
- [ ] Preview text set
- [ ] All links working and tracked (UTM parameters)
- [ ] Unsubscribe link present and functional
- [ ] Physical address included (CAN-SPAM)
- [ ] Responsive on mobile (test render)
- [ ] Plain text fallback exists
- [ ] Sender name and reply-to configured

**marketing-campaign:**
- [ ] All creative assets finalized
- [ ] Tracking pixels/UTM parameters configured
- [ ] Target audience defined and segmented
- [ ] Budget allocated and approved
- [ ] Landing page live and tested
- [ ] A/B test variants set (if applicable)
- [ ] Schedule confirmed

### Sales Checklists

**sales (deck/proposal):**
- [ ] Company/prospect name correct throughout
- [ ] Pricing is current and approved
- [ ] Contact information accurate
- [ ] Branding consistent (logos, colors, fonts)
- [ ] No competitor names misspelled
- [ ] CTA is clear and actionable
- [ ] Attached case studies/testimonials current
- [ ] File format appropriate (PDF for external, editable for internal)

### Research Checklists

**research (paper/report):**
- [ ] Abstract/executive summary present
- [ ] All citations properly formatted
- [ ] Data sources linked and accessible
- [ ] Methodology section complete
- [ ] Figures/charts labeled and referenced
- [ ] Conclusion addresses stated hypothesis
- [ ] Acknowledgments included
- [ ] No placeholder references ("[citation needed]")

### Verified Research Candidate Checklist

Use shipment type `research-candidate` when promoting or submitting an artifact
produced by an autoresearch campaign:

- [ ] Campaign ledger is reconciled, has no active runs, and identifies the epoch
      that produced the candidate; shipment authorization is checked separately.
- [ ] Decision is `verified-keep`, not provisional, deferred, or inconclusive.
- [ ] Canonical candidate and comparator run IDs are named and compatible.
- [ ] Evaluated-source hash equals the source being shipped.
- [ ] Frozen source, build, harness, suite, input, configuration, and toolchain
      identities are present.
- [ ] Rebuild under recorded flags succeeds and required binary/source identity
      checks pass.
- [ ] Correctness, source-size, CPU, wall-time, memory, security, and compatibility
      constraints pass.
- [ ] Exact case coverage, typed outcomes, and practical threshold pass the metric
      contract.
- [ ] Integrity-checked evidence bundle and known reproducibility limitations are
      recorded.
- [ ] Commit/tag or immutable destination identity is recorded.
- [ ] The user explicitly authorizes the concrete upload, submission, publication,
      push, or release action.

A completed campaign does not itself authorize external publication or submission.

### Design Checklists

**design (assets/mockups):**
- [ ] All requested formats exported (PNG, SVG, PDF)
- [ ] Responsive variants provided (mobile, tablet, desktop)
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] No placeholder images or text
- [ ] Source files organized and named
- [ ] Brand guidelines followed
- [ ] Handoff notes/specs documented

**Output:** ` Phase 3: Checklist generated  [N] items, [P] passing, [F] failing`

## Phase 4: Prepare  Iterative Improvement Loop

Apply the autoresearch loop to fix failing checklist items.

```
metric = count_passing_checklist_items / total_checklist_items * 100
direction = higher_is_better
target = 100 (all items pass)

LOOP (until all pass OR max iterations):
  1. Read checklist status
  2. Pick highest-priority failing item
  3. Fix it (one atomic change)
  4. Re-run checklist verification
  5. IF item now passes  keep, log "fixed: [item]"
  6. IF item still fails  preserve evidence, abandon isolated candidate, try again
  7. IF all items pass  EXIT LOOP with "ready to ship"
```

**Priority order for fixes:**
1. **Blockers**  security issues, broken builds, missing critical content
2. **Required**  tests, lint, links, compliance items
3. **Recommended**  descriptions, documentation, polish

Preparation mutations stay within explicitly authorized source scope and use the
shared isolated-candidate/verification contract. They never imply delivery.

**Preparation capabilities:**
- Run test suites and fix failures
- Fix lint errors automatically
- Add missing meta descriptions
- Generate changelog entries from git log
- Check and fix broken links
- Add alt text to images (describe or prompt user)
- Format citations
- Export missing design formats

**Items that require human input:**
- Pricing approval
- Legal review sign-off
- Brand approval
- Strategic decisions (A/B test variants)
- Flag these and ask the user; if an item is required, it remains a blocker.

**Output:** ` Phase 4: Preparation complete  [N/N] checklist items passing`

## Phase 5: Dry-Run  Simulate Before Shipping

Execute a simulation of the ship action without side effects.

| Type | Dry-Run Action |
|------|---------------|
| code-pr | Render the proposed title/body and preview the PR diff; do not create a PR |
| code-release | Validate the proposed tag name and preview the changelog; do not create a tag |
| deployment | Build locally or in an authorized sandbox; do not contact the target environment |
| content | Preview render and check links without publishing |
| marketing-email | Render a local/provider preview; do not send any email |
| marketing-campaign | Render local assets and proposed settings; do not create or activate a campaign |
| sales | Preview PDF render, check all pages |
| research | Export to final format, check pagination |
| design | Preview all exported formats, check dimensions |

**Dry-run gate:**
- Present dry-run results to the user.
- `--auto` may automate preparation/readiness checks only; it never authorizes an
  external or irreversible action.
- Proceed only when the current request explicitly authorizes the exact target and
  action; otherwise obtain confirmation at this boundary.
- `--dry-run` stops here and performs no ship action.

**Output:** ` Phase 5: Dry-run complete  [result summary]`

## Phase 6: Ship  Execute the Delivery

This is an external-action boundary. Immediately before acting, verify that the
current user request explicitly authorizes the exact action and destination, that
all required blockers passed, and that credentials/capabilities are available.
Record the authorization evidence. If any element is missing, stop after the
dry-run and ask; checklist success, `--auto`, prior campaign authorization, or a
previous shipment never counts as authorization.

The actual ship action is domain-specific:

| Type | Ship Action |
|------|------------|
| code-pr | `gh pr create` with full description, request reviewers |
| code-release | `git tag`, `git push --tags`, create GitHub release |
| deployment | `git push` to deploy branch, trigger CI/CD, or `kubectl apply` |
| content | Publish via CMS API, or commit to content branch |
| marketing-email | Send via ESP API (SendGrid, Mailchimp, etc.) |
| marketing-campaign | Activate campaign in ad platform |
| sales | Send email with attachment, or share link |
| research | Upload to repository, submit to journal/platform |
| design | Upload to asset library, share with stakeholders |

**Safety rails:**
- Confirm target (staging vs production, draft vs publish)
- Log the exact command/action taken
- Record timestamp
- Capture any response/confirmation IDs

**Output:** ` Phase 6: Shipped  [action taken] at [timestamp]`

## Phase 7: Verify  Post-Ship Health Check

Confirm the shipment actually landed and is healthy.

| Type | Verification |
|------|-------------|
| code-pr | PR created, CI running, link accessible |
| code-release | Tag visible, release page published, assets attached |
| deployment | Health endpoint returns 200, no error spike in logs |
| content | Page loads, links work, appears in sitemap |
| marketing-email | Delivery rate > 95%, no bounce spike |
| marketing-campaign | Ads serving, landing page loading, tracking firing |
| sales | Email delivered, link tracking active |
| research | Accessible via URL/DOI, properly indexed |
| design | Assets downloadable, correct dimensions |

**Post-ship monitoring (with `--monitor N` flag):**
```
FOR N minutes:
  Check health metrics every 60 seconds
  IF anomaly detected  ALERT user immediately
  Log metrics to ship-log
```

**Output:** ` Phase 7: Verified  [health status summary]`

## Phase 8: Log  Record the Shipment

Create a ship log entry for traceability.

**Log format (append a ledger event, then render `ship-log.tsv`):**
```tsv
timestamp	type	target	checklist_score	dry_run	shipped	verified	duration	notes
2026-03-16T14:30:00Z	code-pr	#42	18/18	pass	pass	pass	4m32s	auth feature PR
```

**Summary output:**
```
=== Ship Complete ===
Type: [shipment type]
Target: [where it went]
Checklist: [P/T] items passed
Duration: [total time]
Status: SHIPPED 
```

## Flags

| Flag | Purpose |
|------|---------|
| `--dry-run` | Run all phases except actual ship (stop at Phase 5) |
| `--auto` | Automate preparation checks only; never authorize external delivery |
| `--force` | Skip non-critical checklist items (still enforce blockers) |
| `--rollback` | Prepare a recovery plan; execute it only with separate authorization for its exact external actions |
| `--monitor N` | Post-ship monitoring for N minutes |
| `--type <type>` | Override auto-detection with explicit shipment type |
| `--checklist-only` | Only generate and evaluate checklist (stop at Phase 3) |

## Composite Metric

For bounded loop mode, the ship readiness metric:

```
ship_score = (checklist_passing / checklist_total) * 80
           + (dry_run_passed ? 15 : 0)
           + (no_blockers ? 5 : 0)
```

- **100** = fully ready to ship
- **80-99** = ready with minor items (can ship with `--force`)
- **<80** = not ready, continue preparing

## Recovery Protocol

`--rollback` or a failed post-ship check creates a proposed recovery plan; it does
not authorize execution. Closing a PR, changing a deployment, unpublishing,
pausing a campaign, sending a correction, requesting retraction, or changing an
asset library are new external actions and each requires separate explicit
authorization for the exact target. Preserve the shipped identity and verification
evidence before recovery. Non-reversible actions such as sent email are reported,
not presented as rollback-capable.

## Output Directory

Within an active campaign, create
`.autoresearch/campaigns/<campaign-id>/artifacts/ship/{YYMMDD}-{HHMM}-{ship-slug}/`
with:
- `checklist.md` — full checklist with pass/fail status;
- `ship-log.tsv` — generated iteration view (if preparation ran);
- `summary.md` — final ship report.

For a one-off non-campaign shipment, use a user-approved output path and do not
create a competing autoresearch state ledger.
