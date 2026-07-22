---
name: oracle
description: "Oracle second-model review: bundle prompts/files, debug, refactor, design."
---

# Oracle (CLI) — best use

Oracle bundles a prompt and selected files into a one-shot request so another
model can answer with real repository context through the API or browser. A
prompt is required; attach files only when they add necessary context. Treat
responses as advisory and verify them against the codebase and tests.

## Main use case (browser, GPT-5.6)

Use browser mode with GPT-5.6 when the ChatGPT account exposes it. GPT-5.6 Sol
and GPT-5.6 Sol Pro are distinct targets: base Sol uses the Extra High effort
setting, while Pro is a separate picker target for difficult or long-running
work.

Recommended defaults:

- Engine: browser (`--engine browser`)
- Base Sol: `--model gpt-5.6-sol`
- Base Sol maximum reasoning: `--browser-thinking-time heavy` (Extra High)
- Pro: `--model gpt-5-pro`, without a thinking-time flag
- Fallback: explicitly use `--model gpt-5.5-pro` when GPT-5.6 is unavailable
- Attachments: directories/globs plus excludes; never attach secrets by default

### Local user override: preserve the current picker state

On this machine, when the user says the current model/thinking state works, do
not open or manipulate the model or effort picker. Pass
`--browser-model-strategy current`, omit `--browser-thinking-time`, and retain
the current state. This explicit preference overrides the generic Base Sol
`heavy` example above. Never silently switch to Pro or another effort after a
picker failure; either use the verified current state or ask the user.

GPT-5.6 availability is account-dependent. Confirm the base Sol picker and
retain model-selection evidence. A bare `Pro` picker label proves picker
selection but does not, by itself, prove the server-side Pro generation.

## GPT-5.6 model selection

This version supports the same aliases in browser and API mode:

- `gpt-5.6`: follow the GPT-5.6 family default
- `gpt-5.6-sol`: pin ChatGPT's `GPT-5.6 Sol` entry
- `gpt-5-pro`: select ChatGPT's `Pro` target

For base Sol on this machine, preserve the verified current picker state:

```bash
oracle --engine browser --model gpt-5.6-sol \
  --browser-model-strategy current \
  -p "<task>" --file "src/**"
```

Use `--browser-thinking-time heavy` only when the user explicitly asks Oracle
to change to Extra High for that run.

Do not use `--model "GPT-5.6 Sol Pro"`. Pro is intentionally handled as a
distinct picker target. Browser label validation rejects unknown future
variants such as `gpt-5.6-luna` instead of silently falling back to Sol; API
runs preserve such provider model IDs unchanged.

Browser mode maps these aliases to ChatGPT's Sol picker. API and multi-model
runs preserve the corresponding first-party OpenAI model IDs; provider-qualified
and unrelated custom IDs remain pass-through values.

The GPT-5.6 browser support depends on the unified Intelligence picker. It
recognizes the current English and Chinese effort labels, avoids matching
`高` inside `极高`, and re-queries the composer pill after React replaces it so
selection verification cannot rely on a detached stale node.

## Compatibility with npm 0.15.2

Do not pass `gpt-5.6` or `gpt-5.6-sol` to an unpatched npm 0.15.2 install. That
release can normalize those labels to `gpt-5.2`. Use the explicit fallback:

```bash
npx -y @steipete/oracle@0.15.2 --engine browser --model gpt-5.5-pro \
  -p "<task>" --file "src/**"
```

After upgrading to a release containing the GPT-5.6 model-selection and
unified-picker changes, verify all of the following before removing the
fallback guidance: `--help --verbose` exposes the new options, browser dry-run
resolves both aliases to GPT-5.6 Sol, API routing selects first-party OpenAI,
and a live browser run records strict GPT-5.6 selection evidence.

## Mandatory local browser policy (this installation)

For every ChatGPT browser run on this machine, unless the user explicitly asks
for API mode or a different remote browser, use the authenticated local launch
path below. This policy takes precedence over the generic remote-browser
examples later in this skill.

The user-level Oracle config at `~/.oracle/config.json` must retain these
settings (preserve unrelated keys and comments when repairing it):

```js
{
  engine: "browser",
  browser: {
    debugPort: 9222,
    chromeCookiePath: "/Users/abf/Library/Application Support/Google/Chrome/Default/Cookies",
    chatgptUrl: "https://chatgpt.com/g/g-p-6a259de390308191b9b01ed9d16db181-ogc2026/project",
    modelStrategy: "current",
  },
}
```

Before each new browser session:

1. Run `oracle status --hours 24` and follow the single-session discipline.
2. Verify the cookie database exists and is readable. Never print, copy into
   logs, or attach cookie values. It is acceptable to query only a count of
   ChatGPT/OpenAI rows when diagnosing authentication.
3. Verify the config still names port `9222` and the cookie database above.
   Treat the configured OGC2026 URL only as a fallback. If the active
   repository's `AGENTS.md` or the user names another ChatGPT Project, pass that
   URL explicitly with `--chatgpt-url`; never send one project's context to the
   fallback project and never rewrite a project-specific instruction to OGC.
4. Probe `http://127.0.0.1:9222/json/version`. If the port is closed, let Oracle
   launch its temporary cookie-synced Chrome. If it is open, determine whether
   it belongs to the relevant Oracle session. Recover that session when
   relevant. For an unrelated/shared Chrome, stop or ask the user; never kill
   it and never allow Oracle to silently fall back to another port.

Use an ordinary browser invocation so Oracle creates a temporary automation
profile, imports the authenticated cookies, launches Chrome on `9222`, and
cleans it up afterward:

```bash
oracle --engine browser --model gpt-5.6-sol \
  --browser-model-strategy current \
  --chatgpt-url "<project URL from AGENTS.md or user>" \
  --slug "<readable-3-5-words>" \
  -p "<task>" --file "src/**"
```

Do **not** add `--browser-attach-running`, `--remote-chrome`, `--copy-profile`,
or an alternate `--browser-port` by default. Attach/remote modes reuse an
already-running browser and bypass Oracle's local cookie-sync/launch path;
copy-profile is less reliable on encrypted Chrome cookies. Use one of those
modes only when the user explicitly requests it or recovery of an existing
submitted session requires it.

Immediately after launch, inspect `~/.oracle/sessions/<slug>/meta.json`. During
the bounded pre-submission phase, require the correct port, authenticated
project URL, and controller ownership. `promptSubmitted` may remain false while
Oracle is composing or processing files; it is not by itself proof of failure.
The run becomes submitted when the port/project/auth checks hold and either
Oracle records the send or the exact server-side user turn is verified:

- `browser.runtime.chromePort == 9222`
- `browser.runtime.promptSubmitted == true` **or** the exact user turn exists
- `browser.runtime.tabUrl` is inside the intended ChatGPT project
- the session is authenticated (a ChatGPT project conversation loaded rather
  than a login page)

If launch/authentication fails before submission, correct the configuration or
cookie source and relaunch once. If submission occurred, never duplicate the
request; recover the same session. Apply the submission watchdog below instead
of waiting silently for `promptSubmitted` to change. After a foreground run, confirm the
Oracle-owned browser closed and port `9222` is no longer listening. For a
background run, retain its PID/session manifest and leave its owned browser
running until harvest and graceful cleanup.

## Efficient browser fast path

The default objective is: one compact payload, one browser session, submitted
within 90 seconds, followed by passive completion monitoring.

### 1. Collapse context before launch

Do not upload a pile of small Markdown/JSON files. Multiple attachment chips
are slow and the ChatGPT DOM can report them as unready after the UI already
looks usable. Build one deterministic `<run>.context.md` containing only the
necessary excerpts, with a `## FILE: path` header before each source.

- Prefer 1 prompt plus 1 context file.
- Target 10k–50k characters of context; remove generated tables, repeated
  instructions, and stale artifacts.
- With a context under roughly 55k characters, use
  `--browser-attachments auto` so Oracle can inline it and avoid attachment
  readiness entirely.
- If the compact context must exceed the inline threshold, upload exactly one
  plain-text/Markdown context file with `--browser-attachments always` and
  `--browser-attachment-timeout 5m`.
- Avoid ZIP attachments for text context. Use ZIP only for genuinely binary or
  path-structured evidence that cannot be summarized safely.
- Never fall back to a huge inline paste. If context approaches 100k tokens,
  curate it again.

Always preview the exact payload:

```bash
oracle --dry-run summary --files-report \
  -p "$(cat artifacts/oracle/<run>.prompt.md)" \
  --file artifacts/oracle/<run>.context.md
```

### 2. Launch visibly and verbosely

Use `--verbose` so attachment and composer progress is observable. Preserve the
current picker state unless the user explicitly requests a change:

```bash
unset ORACLE_BROWSER_COOKIES_FILE
oracle --verbose --engine browser --model gpt-5.6-sol \
  --browser-model-strategy current \
  --chatgpt-url "<intended project URL>" \
  --browser-cookie-path \
    "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-attachments auto \
  --browser-input-timeout 2m \
  --browser-attachment-timeout 5m \
  --timeout 2h \
  --slug "<run>" \
  --write-output artifacts/oracle/<run>.raw.md \
  -p "$(cat artifacts/oracle/<run>.prompt.md)" \
  --file artifacts/oracle/<run>.context.md
```

Run it in a controllable foreground exec session. Do not hide a pre-submission
stall inside `nohup`.

### 3. Enforce a 90-second submission watchdog

Poll the session metadata every 5 seconds for at most 90 seconds and report
only state changes. At the same time, inspect the browser read-only for:

- exact intended project/conversation URL;
- authenticated state;
- prompt prefix present in the composer or first user turn;
- expected inline context marker or the single attachment chip;
- whether Send is visible and enabled;
- whether a user turn or assistant generation already exists.

Then follow this state machine:

```text
promptSubmitted=true or user turn exists
  -> submitted; never click Send or relaunch

promptSubmitted=false, Send enabled, exact payload verified, no user turn
  -> Oracle submit automation is lagging

promptSubmitted=false, context still processing at 90s
  -> pre-submission packaging failure; stop and compact/rebuild once

login/wrong project/picker error
  -> stop before submission and correct that specific cause once
```

Do not make the user click Send. If the exact payload is verified and Send is
enabled but Oracle has not submitted by 90 seconds, use the controlled
pre-submission takeover:

1. Interrupt the Oracle controller first so it cannot race and submit twice.
2. Verify the Oracle-owned Chrome/CDP endpoint remains open.
3. Re-check the project URL, exact prompt prefix, context marker/chip, absence
   of an existing user turn, and the enabled Send button.
4. Click **Send exactly once** using the browser-control/Chrome DevTools trusted
   input path.
5. Verify that the prompt moved into a user turn and an assistant turn or
   generation state appeared; record the conversation URL.
6. Treat local `promptSubmitted=false` as stale metadata and monitor that
   server-side conversation. Never restart the original request.

This takeover applies only to the pre-submission Send button. The
generation-control non-intervention policy below remains absolute.

If the user submits manually before takeover, interrupt the controller
immediately, verify the created user turn, and continue passive monitoring; do
not scold, duplicate, or try to repair the stale local session.

### 4. Monitor completion with one watcher

After submission, use one bounded watcher that polls the exact conversation
every 30 seconds and records only transitions (`submitted`, `thinking`,
`completed`, `errored`). Do not spend a sequence of agent turns issuing long
sleep commands. The watcher must be read-only: never click `Answer now`,
`Stop answering`, `Continue`, `Regenerate`, or similar controls.

Completion requires all of the following:

- no `Stop answering` or `Answer now` control;
- a nontrivial final assistant turn;
- normal post-completion controls such as `Copy response` may be present.

Harvest via `oracle session ... --render/--harvest` when session metadata is
accurate. If a controlled or user manual send made metadata stale, extract only
the last completed assistant turn from the exact conversation DOM and save it
to `artifacts/oracle/<run>.rendered.md` with the conversation URL and retrieval
timestamp. Then close only the Oracle-owned browser and verify its port closed.

## Golden path

1. Apply the mandatory local browser policy above.
2. Pick the smallest file set that still contains the truth and collapse it to
   one compact context Markdown file.
3. Preview the exact one-payload bundle with `--dry-run summary` and
   `--files-report`.
4. Use browser mode for GPT-5.6; use API only when explicitly intended.
5. If a run detaches or times out, reattach to the stored session instead of
   starting a duplicate.
6. Apply the 90-second submission watchdog; do not wait silently on attachment
   processing.
7. Start at most one Oracle session for a given request. If the state is
   uncertain, recover or monitor the existing session before considering a new
   run.

## Single-session discipline

Before launching a new run, inspect recent sessions:

```bash
oracle status --hours 24
```

If a relevant session is listed as `running`, `stalled`, detached, or otherwise
ambiguous, do **not** start another session with the same prompt. Use the stored
session id:

```bash
oracle session <session-id> --live
oracle session <session-id> --harvest
oracle session <session-id> --render
```

Prefer `--live` or `--harvest` while a browser conversation may still be active.
Use `--render` after completion, or when a non-live render is known not to
block. A browser wrapper process can exit while the ChatGPT/Gemini conversation
continues server-side; the wrapper PID alone is not proof that the model run is
finished or lost.

Only relaunch without explicit user approval when the failed run clearly ended
before prompt submission, for example login failure before the message was sent.
If the prompt may have reached the model, reattach/harvest/wait instead of
duplicating the request. Use `--force` only for an intentionally new identical
run.

## Browser UI non-intervention policy

Do **not** manually click ChatGPT/Gemini generation-control buttons during
Oracle recovery, including but not limited to `Answer now`, `Continue`,
`Resume`, `Stop generating`, `Regenerate`, `Try again`, or similar buttons.
These controls change the model-side generation state and are not part of the
safe Oracle recovery protocol.

If a browser page exposes an `Answer now` or continuation-style button after
prompt submission, treat the session as not ready or stalled. The only allowed
actions without explicit user approval are:

- wait and monitor the same session;
- run `oracle session <session-id> --live`;
- run `oracle session <session-id> --harvest`;
- run `oracle session <session-id> --render` after completion;
- inspect read-only metadata, logs, transcript artifacts, or DOM text for
  diagnosis.

If clicking a generation-control button appears necessary to obtain an answer,
stop and ask the user for explicit approval first. Document the exact button,
the observed session state, and why passive recovery is insufficient. Never
click it proactively.

## Commands

- Show help:
  - `npx -y @steipete/oracle --help --verbose`

- Preview without calling a model:
  - `npx -y @steipete/oracle --dry-run summary -p "<task>" --file "src/**" --file "!**/*.test.*"`
  - `npx -y @steipete/oracle --dry-run full -p "<task>" --file "src/**"`

- Inspect token usage:
  - `npx -y @steipete/oracle --dry-run summary --files-report -p "<task>" --file "src/**"`

- Browser run:
  - `oracle --verbose --engine browser --model gpt-5.6-sol --browser-model-strategy current -p "<task>" --file "artifacts/oracle/<run>.context.md"`

- Manual paste fallback:
  - `npx -y @steipete/oracle --render-markdown --copy-markdown -p "<task>" --file "src/**"`
  - `--render` is an alias for `--render-markdown`.

- Performance trace:
  - `npx -y @steipete/oracle --perf-trace --perf-trace-path /tmp/oracle-perf.json --dry-run summary -p "<task>" --file "src/**"`

## Attaching files

`--file` accepts files, directories, and globs. Pass it multiple times or use
comma-separated entries.

- Include: `--file "src/**"`, `--file src/index.ts`, `--file docs --file README.md`
- Exclude: prefix a pattern with `!`, for example `--file "!src/**/*.test.ts"`
- Default ignored directories: `node_modules`, `dist`, `coverage`, `.git`,
  `.turbo`, `.next`, `build`, and `tmp`
- Globs honor `.gitignore` and do not follow symlinks.
- Dotfiles require an explicit dot-segment in the pattern, such as
  `--file ".github/**"`.
- Files over 1 MB are rejected by default; configure
  `ORACLE_MAX_FILE_SIZE_BYTES` or `maxFileSizeBytes` when necessary.

Keep total input under roughly 196k tokens. Use `--files-report` or
`--dry-run json` to identify oversized inputs. Never attach `.env` files,
private keys, auth tokens, or other secrets unless they have been redacted and
are essential to the question.

## Engines and browser controls

- Auto-selection uses API when `OPENAI_API_KEY` is set and browser otherwise.
- Browser supports GPT models through ChatGPT and Gemini models through Gemini
  web. API-only models include `gpt-5.1-codex`.
- Current model families include GPT-5.5/5.4/5.2/5.1, Gemini 3.x, and Claude
  4.x; availability depends on engine and provider.
- API runs require explicit user consent because they may incur usage costs.
- Browser attachments use `--browser-attachments auto|never|always`.
- For many files, add `--browser-bundle-files --browser-bundle-format auto|zip`.
- Reuse an existing Chrome session with `--browser-tab <ref>`,
  `--browser-attach-running`, or `--remote-chrome <host:port>`.
- Use `--browser-model-strategy select|current|ignore` to control picker
  behavior.
- Use `--browser-follow-up "<prompt>"` for another turn in the same browser
  conversation, or `--followup <sessionId|responseId>` for a stored run.
- Use `--browser-research deep` only when Deep Research is explicitly wanted.

## Robust browser execution pattern

On this installation, use the mandatory cookie-synced port-`9222` launch policy
above by default. The remote-browser pattern in this section is only for an
explicit user request or recovery of an already-submitted session. If such a
persistent remote Chrome endpoint is required, verify it first:

```bash
python3 - <<'PY'
import json, urllib.request
data = json.load(urllib.request.urlopen("http://127.0.0.1:PORT/json/list", timeout=3))
print("tabs", len(data))
for tab in data[:8]:
    print("-", tab.get("title", "")[:80], tab.get("url", "")[:120])
PY
```

Then point Oracle at that endpoint:

```bash
timeout 2h oracle \
  --engine browser \
  --model gpt-5-pro \
  --browser-model-strategy current \
  --timeout 2h \
  --slug "<readable-3-5-words>" \
  --remote-chrome 127.0.0.1:PORT \
  --browser-attachments always \
  --max-file-size-bytes 10000000 \
  --write-output artifacts/oracle/<run>.raw.md \
  -p "$(sed -n '1,260p' artifacts/oracle/<prompt>.md)" \
  --file artifacts/oracle/<context>.zip \
  > artifacts/oracle/<run>.log 2>&1
```

Use `--chatgpt-url <url>` when the task belongs in a specific ChatGPT project or
workspace. Use `--browser-model-strategy current` when the desired picker state
has already been verified and picker automation is fragile; otherwise use the
default selection strategy and retain model-selection evidence in the log.

Avoid copied browser profiles as the default recovery mechanism. They can fail
because copied login tokens may not decrypt or because the browser closes before
Oracle finishes. Prefer `--remote-chrome`, `--browser-tab`, or
`--browser-attach-running` when a signed-in browser is already available.

For background runs, always write a PID, log, and output path:

```bash
nohup bash -lc 'timeout 2h oracle ...' \
  > artifacts/oracle/<run>.log 2>&1 &
echo $! > artifacts/oracle/<run>.pid
```

During long jobs, poll sparingly and avoid blocking sleeps longer than the host
workflow can tolerate. Report material state changes: prompt submitted, model
streaming, detached, stalled, completed, harvested, or errored.

## Resumable background-job protocol

When the user asks for a background Oracle run and later retrieval, treat the
run as a persistent subtask owned by the current conversation. The foreground
turn must leave behind enough state for a later turn to resume without
guessing. Use a unique slug and create a small run manifest beside the PID:

```text
artifacts/oracle/<run>.prompt.md
artifacts/oracle/<run>.context.md
artifacts/oracle/<run>.pid
artifacts/oracle/<run>.log
artifacts/oracle/<run>.raw.md
artifacts/oracle/<run>.state.json   # slug, wrapper PID, session ID, start time
```

Before launch, run a dry-run/files report and inspect `oracle status --hours
24`. After launch, wait briefly and verify the session metadata, not just the
wrapper PID:

```bash
jq '{status,browser:.browser.runtime,lifecycle}' \
  "$HOME/.oracle/sessions/<slug>/meta.json"
```

The decisive positive submission check is
`browser.runtime.promptSubmitted: true` or a verified server-side user turn.
`promptSubmitted: false` means only that Oracle has not recorded its own send;
it may still be composing, may have failed before submission, or may be stale
after a user/controlled manual send. Apply the 90-second watchdog and inspect
the read-only browser state before classifying it. A corrected relaunch is
allowed only after proving that no user turn exists and the model never
received the prompt. Picker errors are a common pre-submission failure. Do not
switch to Pro or change effort automatically; preserve a user-verified current
state or ask before changing it.

If `promptSubmitted` is true, never start a second run for the same request.
On subsequent turns, read the manifest and inspect the same session's
`meta.json` and log. Poll with one read-only watcher at 30–60 second intervals
and report only state transitions. Do not use repeated long foreground sleeps
that consume agent turns or prevent the conversation from receiving a user
message. The
expected state machine is:

```text
launched -> submitted -> streaming -> completed -> harvested -> cleaned
                         \-> detached/stalled -> reattach/live/harvest
                         \-> errored (only relaunch if promptSubmitted=false)
```

When the session is completed, retrieve the answer from the same session:

```bash
oracle session <slug> --render \
  > artifacts/oracle/<run>.rendered.md \
  2> artifacts/oracle/<run>.render.log
```

Preserve the rendered answer and the browser transcript. Then create a concise
curated research/result note in the repository, clearly separating Oracle
advice from locally verified facts and measured results. Do not claim the
research task is complete merely because the wrapper exited; completion must
be confirmed by Oracle session state or a valid harvested response.

## Graceful cleanup

After retrieval, end only the background processes owned by this run. Read the
recorded wrapper PID and check its command line before sending `SIGTERM`; wait
up to 10 seconds, then use `SIGKILL` only for a still-running owned wrapper.
If a controller PID is recorded, apply the same ownership check. Do not kill a
shared Chrome process or browser profile merely because Oracle used it. A
completed Oracle session normally needs no controller termination, but stale
wrapper processes must still be checked. Finally verify:

```bash
pgrep -af 'timeout .*oracle|oracle --engine' || true
oracle status <slug> --hide-prompt
```

The final user update should include the session status, result paths, whether
the answer was harvested or rendered, and explicit confirmation that owned
background jobs were cleaned up. If the user sends a new message while the
run is active, treat it as a possible resume request: inspect the existing
manifest/session first and continue the same run unless the user explicitly
asks for a new one.

## API preflight

Before an API run, check provider readiness without printing secrets:

```bash
oracle doctor --providers --models gpt-5.4,claude-4.6-sonnet,gemini-3-pro
oracle --preflight --models gpt-5.4,gemini-3-pro
oracle --route --model gpt-5.4
```

Use `--provider openai` or `--no-azure` when first-party OpenAI routing is
required. For multi-model panels where partial success is useful, use
`--allow-partial --write-output <path>` so successful outputs and the manifest
can be recovered.

Set an explicit deadline for automation, for example `--timeout 10m`; Oracle
derives the HTTP timeout unless `--http-timeout` is supplied.

## Sessions and recovery

- Sessions are stored under `~/.oracle/sessions`; override with
  `ORACLE_HOME_DIR`.
- Browser artifacts include `transcript.md` and, when available, research
  reports and generated images.
- List recent sessions with `oracle status --hours 72`.
- Attach with `oracle session <id> --render`.
- Use `--slug "<3-5 words>"` for readable session IDs.
- If a run times out, reattach; do not re-run it. Use `--force` only when a
  genuinely new identical run is intended.
- Successful non-project browser one-shots are archived automatically by
  default; override with `--browser-archive never|always`.

Recovery procedure:

1. Check `oracle status --hours 24` and identify the relevant session id.
2. If the wrapper exited or Chrome disconnected, run:

   ```bash
   oracle session <session-id> --live
   ```

3. If `--live` disconnects, stalls, or the answer might already be visible, run:

   ```bash
   oracle session <session-id> --harvest \
     > artifacts/oracle/<session-id>.harvest.latest.md \
     2> artifacts/oracle/<session-id>.harvest.latest.log
   ```

4. If harvest returns only a short planning preamble and the session is still
   running or stalled, treat the answer as not ready. Wait and harvest the same
   session again later.
5. When a complete answer is harvested, preserve the raw harvest and extract a
   clean assistant answer to a separate file before writing any curated summary.
6. If the browser shows `Answer now`, `Continue`, `Resume`, `Regenerate`,
   `Try again`, or any similar generation-control button, do not click it.
   Continue passive recovery or ask the user for explicit approval.
7. Do not launch a smaller fallback or duplicate prompt unless the user
   explicitly approves it or the original run definitely failed before prompt
   submission.

## Prompt template

Oracle starts with zero project knowledge. Include:

- Project briefing: stack, services, build/test commands, and platform constraints
- Where things live: entrypoints, configs, key modules, and dependency boundaries
- Exact question, prior attempts, and verbatim error text
- Constraints such as API compatibility, performance budgets, and files not to change
- Desired output such as a patch plan, tests, risk list, or tradeoff comparison

For a long investigation, make the prompt restorable: put a 6–30 sentence
briefing at the top, concrete reproduction and errors in the middle, and attach
all context files required by a fresh model at the bottom. Oracle runs are
one-shot; the model does not remember prior runs.
