---
name: oracle
description: "Use Oracle for second-model review, debugging, refactoring, or design with reliable ChatGPT browser authentication, verified file attachments, current-model preservation, and session monitoring."
---

# Oracle (CLI) — best use

Oracle bundles a prompt and selected files into a one-shot request so another
model can answer with real repository context through the API or browser. A
prompt is required; attach files only when they add necessary context. Treat
responses as advisory and verify them against the codebase and tests.

## Quick start

Install globally: `npm install -g @steipete/oracle`
Homebrew: `brew install steipete/tap/oracle`
Requires Node 24+. Or use `npx -y @steipete/oracle …` (or `pnpx`).

```bash
# Copy the bundle and paste into ChatGPT
npx -y @steipete/oracle --render --copy -p "Review the TS data layer for schema drift" --file "src/**/*.ts,**/*.test.ts"

# Minimal API run (expects OPENAI_API_KEY in your env)
npx -y @steipete/oracle -p "Write a concise architecture note for the storage adapters" --file src/storage/README.md

# Multi-model API run
npx -y @steipete/oracle -p "Cross-check the data layer assumptions" --models gpt-5.1-pro,gemini-3-pro --file "src/**/*.ts"

# Preview without spending tokens
npx -y @steipete/oracle --dry-run summary -p "Check release notes" --file docs/release-notes.md

# Check provider routing/readiness before an API panel
npx -y @steipete/oracle doctor --providers --models gpt-5.5-pro,gemini-3-pro,claude-4.6-sonnet

# Browser run (no API key, will open ChatGPT)
npx -y @steipete/oracle --engine browser -p "Walk through the UI smoke test" --file "src/**/*.ts"
```

## Main use case (browser, preserve current ChatGPT state)

Use browser mode when an authenticated ChatGPT session is available. Browser
mode automates Chrome directly.

Recommended defaults:

- Engine: browser (`--engine browser`)
- Use `--browser-model-strategy current` to keep the active ChatGPT model
- Authentication: a dedicated persistent Chrome profile exposed through local
  DevTools (`--remote-chrome`); log in once, then let Chrome reuse its own
  cookies
- Attachments: directories/globs plus excludes; never attach secrets by default

### Recommended local setup

Do not make Oracle decrypt the regular Chrome `Cookies` SQLite database on this
machine. That path has repeatedly produced `No ChatGPT cookies were applied`,
and a cookie row count is not proof that the browser can use the session. Use a
separate profile that Chrome owns and decrypts itself:

```bash
"$HOME/.agents/skills/oracle/scripts/chrome-session.sh" start \
  "https://chatgpt.com/"
```

Sign in to ChatGPT in the opened window once. The profile is retained at
`~/.oracle/chrome-profile`, and the local CDP endpoint is `127.0.0.1:9222`.
Check it without exposing cookies:

```bash
"$HOME/.agents/skills/oracle/scripts/chrome-session.sh" status
```

Use the same profile for every Oracle request. Do not pass
`--browser-cookie-path`, `ORACLE_BROWSER_COOKIES_FILE`, `--copy-profile`, or
`--browser-attach-running` in this path. `--remote-chrome` reuses the already
authenticated Chrome session and avoids cookie extraction entirely. The helper
refuses to use port `9222` when it cannot prove that the process owns the
dedicated profile.

The profile is intentionally separate from normal browsing. Remote debugging
gives any local process control over that profile, so keep the endpoint bound to
`127.0.0.1` and stop it when finished:

```bash
"$HOME/.agents/skills/oracle/scripts/chrome-session.sh" stop
```

### Local user override: preserve the current picker state

On this machine, when the user says the current model/thinking state works, do
not open or manipulate the model or effort picker. Pass
`--browser-model-strategy current`, omit `--model` and
`--browser-thinking-time`, and retain the current state. This explicit preference
overrides every generic example below. Never silently switch model or effort
after a picker failure; either use the verified current state or ask the user.

With `--browser-model-strategy current`, do not pass a thinking-time flag unless
the user explicitly asks to change it.

## Mandatory browser preflight and single-path policy

Browser submission must be deterministic. Do not burn retries discovering
whether a cookie database works, whether the project is correct, or whether a
file was attached. A database containing ChatGPT cookie rows is not proof that
Oracle can decrypt or apply those cookies.

Before each new browser request:

1. Run `$HOME/.agents/skills/oracle/scripts/oracle.sh status --hours 24`. Recover any relevant nonterminal session;
   never create a second request while submission is ambiguous.
2. Build the exact prompt and exactly one curated context file. Run
   `--dry-run summary --files-report` and record its character/token count.
3. Determine the delivery contract before launch: when any file is supplied,
   default to a real attachment (`--browser-attachments always`). Inline text is
   allowed only when the user explicitly asks for it. A request mentioning
   "attach", "attachment", "file", "project source", or "upload" requires a
   visible attachment chip; `auto` is forbidden.
4. Determine the authentication path *before* sending the real prompt: prefer
   the dedicated persistent profile and verify its owned CDP endpoint with
   `$HOME/.agents/skills/oracle/scripts/chrome-session.sh status`. Do not probe cookie
   databases speculatively. Cookie import is a last-resort diagnostic path, not
   the normal workflow.
5. Always pass the exact ChatGPT project URL named by the user or repository.
   Never use a configured fallback project for a different task.
6. When preserving current model/thinking state, pass only
   `--browser-model-strategy current`; omit `--model` and every effort flag.

The only allowed pre-submission recovery is one correction based on a concrete
failure: `attachment processing failed` -> rebuild the same one-file payload.
If the dedicated profile is not authenticated, stop and ask for a one-time
interactive login in that profile. Do not cascade through cookie databases,
profiles, ports, or attach modes. A request is never retried after a user turn
might exist.

### Approved remote-profile launch

Use the helper above when possible. The equivalent manual launch is shown only
for debugging. Use it only with explicit authorization for the profile. Do not
print cookie values or copy them into files. Chrome can decrypt its own profile
while Oracle's raw cookie importer may not.

```bash
 /opt/google/chrome/chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --user-data-dir="<approved-profile-dir>" \
  --profile-directory=Default \
  --no-first-run --no-default-browser-check about:blank

curl --silent --show-error --max-time 3 http://127.0.0.1:9222/json/version
curl --silent --show-error --max-time 3 http://127.0.0.1:9222/json/list
```

Then use one remote Oracle invocation. Do not combine `--remote-chrome` with
`--browser-attach-running` or `--browser-port`:

```bash
"$HOME/.agents/skills/oracle/scripts/oracle.sh" --verbose --engine browser \
  --browser-model-strategy current \
  --chatgpt-url "<intended-project-url>" \
  --remote-chrome 127.0.0.1:9222 \
  --browser-attachments always \
  --browser-input-timeout 2m \
  --timeout 2h \
  --browser-archive never \
  --slug "<readable-3-5-words>" \
  --write-output "artifacts/oracle/<run>.raw.md" \
  -p "$(<artifacts/oracle/<run>.prompt.md)" \
  --file "artifacts/oracle/<run>.context.md"
```

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

Use the bundled watcher instead of repeatedly issuing long sleeps. It is
read-only: it opens the Oracle-owned CDP target, checks the exact prompt prefix,
the expected attachment filename and processing state, and records only state
transitions:

```bash
python3 "$HOME/.agents/skills/oracle/scripts/watch-browser.py" \
  --session "<slug>" \
  --prompt "artifacts/oracle/<run>.prompt.md" \
  --context "artifacts/oracle/<run>.context.md" \
  --output "artifacts/oracle/<run>.watch.jsonl"
```

Use `--once` for a single diagnostic snapshot. The watcher never clicks Send,
Answer now, Stop answering, Continue, or Regenerate. Its `takeover-ready`
state means the exact payload is visible and Send is enabled; only then may a
human-approved Chrome DevTools input takeover click Send once after first
interrupting Oracle. A missing or processing attachment is not a valid send.

If launch/authentication fails before submission, use only the one concrete
recovery already authorized by the preflight policy. If submission occurred,
never duplicate the request; recover the same session. Apply the submission
watchdog below instead of waiting silently for `promptSubmitted` to change.
After a foreground run, confirm the Oracle-owned browser closed and port `9222`
is no longer listening. For a background run, retain its PID/session manifest
and leave its owned browser running until harvest and graceful cleanup.

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
- Upload exactly one plain-text/Markdown context file with
  `--browser-attachments always`. Use the installed CLI's
  `--browser-attachment-timeout` equivalent only if `oracle --help --verbose`
  exposes it; Oracle 0.16.1 relies on its built-in attachment wait.
  Do not let `auto` silently replace an expected attachment with an inline
  paste, even for a small context.
- Use `--browser-attachments never` only when the user explicitly requests an
  inline prompt and no attachment chip is required.
- Avoid ZIP attachments for text context. Use ZIP only for genuinely binary or
  path-structured evidence that cannot be summarized safely.
- Never fall back to a huge inline paste. If context approaches 100k tokens,
  curate it again.

Always preview the exact payload:

```bash
"$HOME/.agents/skills/oracle/scripts/oracle.sh" --dry-run summary --files-report \
  -p "$(<artifacts/oracle/<run>.prompt.md)" \
  --file artifacts/oracle/<run>.context.md
```

### 2. Launch visibly and verbosely

Use `--verbose` so attachment and composer progress is observable. Preserve the
current picker state unless the user explicitly requests a change:

```bash
unset ORACLE_BROWSER_COOKIES_FILE
"$HOME/.agents/skills/oracle/scripts/oracle.sh" --verbose --engine browser \
  --browser-model-strategy current \
  --chatgpt-url "<intended project URL>" \
  --browser-attachments always \
  --browser-input-timeout 2m \
  --timeout 2h \
  --slug "<run>" \
  --write-output artifacts/oracle/<run>.raw.md \
  -p "$(<artifacts/oracle/<run>.prompt.md)" \
  --file artifacts/oracle/<run>.context.md
```

Run it in a controllable foreground exec session. Do not hide a pre-submission
stall inside `nohup`.

### 3. Enforce a 90-second submission watchdog

Run the bundled read-only watcher for at most 90 seconds and report only state
changes. At the same time, it inspects the browser read-only for:

- exact intended project/conversation URL;
- authenticated state;
- prompt prefix present in the composer or first user turn;
- the single attachment chip, its expected filename, and ready state;
- whether Send is visible and enabled;
- whether a user turn or assistant generation already exists.

Then follow this state machine:

```text
promptSubmitted=true or user turn exists
  -> submitted; never click Send or relaunch

promptSubmitted=false, Send enabled, exact payload verified, no user turn
  -> Oracle submit automation is lagging

promptSubmitted=false, attachment is still processing at 90s
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

After submission, keep the same bounded watcher polling the exact conversation
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
4. Use browser mode with the verified current ChatGPT picker state; use API only
   when explicitly intended.
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

- Browser run with a real attachment:
  - `"$HOME/.agents/skills/oracle/scripts/oracle.sh" --verbose --engine browser --browser-model-strategy current --browser-attachments always -p "<task>" --file "artifacts/oracle/<run>.context.md"`

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

Follow the preflight policy above. The remote-browser path is only for an
explicitly authorized profile or recovery of an already-submitted session. If
such a persistent remote Chrome endpoint is required, verify it first:

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
timeout 2h "$HOME/.agents/skills/oracle/scripts/oracle.sh" \
  --engine browser \
  --browser-model-strategy current \
  --timeout 2h \
  --slug "<readable-3-5-words>" \
  --remote-chrome 127.0.0.1:PORT \
  --browser-attachments always \
  --max-file-size-bytes 10000000 \
  --write-output artifacts/oracle/<run>.raw.md \
  -p "$(<artifacts/oracle/<prompt>.md)" \
  --file artifacts/oracle/<context>.md \
  > artifacts/oracle/<run>.log 2>&1
```

Use `--chatgpt-url <url>` when the task belongs in a specific ChatGPT project or
workspace. Use `--browser-model-strategy current` when the desired picker state
has already been verified. Omit `--model` so the CLI cannot express an
unintended target model; retain only non-mutating current-state evidence in the
log.

Avoid copied browser profiles as the default recovery mechanism. They can fail
because copied login tokens may not decrypt or because the browser closes before
Oracle finishes. For an approved profile, prefer an owned remote Chrome process
and `--remote-chrome`; do not trial `--browser-tab` or
`--browser-attach-running` after that path is selected.

For background runs, always write a PID, log, and output path:

```bash
nohup bash -lc 'timeout 2h "$HOME/.agents/skills/oracle/scripts/oracle.sh" ...' \
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

Before launch, run a dry-run/files report and inspect `$HOME/.agents/skills/oracle/scripts/oracle.sh status --hours
24`. Record whether the context must appear as an attachment. After launch,
wait briefly and verify the session metadata, not just the wrapper PID:

```bash
jq '{status,browser:.browser.runtime,lifecycle}' \
  "$HOME/.oracle/sessions/<slug>/meta.json"
```

The decisive positive submission check is
`browser.runtime.promptSubmitted: true` or a verified server-side user turn.
When the delivery contract requires an attachment, verify the single expected
filename and ready attachment chip before treating any send as valid.
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
                          \-> errored (one concrete preflight-approved recovery
                              only if no user turn exists)
```

When the session is completed, retrieve the answer from the same session:

```bash
"$HOME/.agents/skills/oracle/scripts/oracle.sh" session <slug> --render \
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
"$HOME/.agents/skills/oracle/scripts/oracle.sh" status <slug> --hide-prompt
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
"$HOME/.agents/skills/oracle/scripts/oracle.sh" doctor --providers --models gpt-5.4,claude-4.6-sonnet,gemini-3-pro
"$HOME/.agents/skills/oracle/scripts/oracle.sh" --preflight --models gpt-5.4,gemini-3-pro
"$HOME/.agents/skills/oracle/scripts/oracle.sh" --route --model gpt-5.4
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
- List recent sessions with `$HOME/.agents/skills/oracle/scripts/oracle.sh status --hours 72`.
- Attach with `$HOME/.agents/skills/oracle/scripts/oracle.sh session <id> --render`.
- Use `--slug "<3-5 words>"` for readable session IDs.
- If a run times out, reattach; do not re-run it. Use `--force` only when a
  genuinely new identical run is intended.
- Successful non-project browser one-shots are archived automatically by
  default; override with `--browser-archive never|always`.

Recovery procedure:

1. Check `$HOME/.agents/skills/oracle/scripts/oracle.sh status --hours 24` and identify the relevant session id.
2. If the wrapper exited or Chrome disconnected, run:

   ```bash
   "$HOME/.agents/skills/oracle/scripts/oracle.sh" session <session-id> --live
   ```

3. If `--live` disconnects, stalls, or the answer might already be visible, run:

   ```bash
   "$HOME/.agents/skills/oracle/scripts/oracle.sh" session <session-id> --harvest \
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
