---
name: oracle
description: "Oracle second-model review via GPT-5.5 Pro: bundle prompts and files, ChatGPT Project context, debug, refactor, design-check, research. Use when stuck on a bug, need architectural review, cross-checking assumptions, or want a second opinion on complex code."
---

# Oracle — Second-Model Review

Oracle bundles your prompt + selected files into one request so another model can answer with real repo context. Supports API and browser automation modes. Browser mode can also target a ChatGPT Project so multiple Oracle sessions share persistent project instructions and sources. Treat outputs as advisory; verify against the codebase and tests.

## Installation Status

Oracle is installed globally (`oracle` CLI, v0.13.0). Requires Node 24+ (default via nvm).

## Browser Mode Setup

Browser mode authenticates via your existing Chrome login session. The primary
method reads Chrome's cookie database directly — no separate login needed, as
long as you've signed into ChatGPT in Chrome at least once.

**Primary: Chrome cookie database** (recommended — most reliable)

```bash
# Close Chrome first — the cookie DB is locked while Chrome is running.
# Then clear any stale cookie-file env var and run:
unset ORACLE_BROWSER_COOKIES_FILE
oracle --engine browser \
  --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-cookie-wait 10s \
  -p "Quick auth test. Reply with OK."
```

Only proceed with a large Oracle run after the quick auth test returns `OK`.

**Alternative: attach to running Chrome** (when Chrome is already open & logged in)

Start Chrome with remote debugging enabled:

```bash
# Quit Chrome, then relaunch:
open -a "Google Chrome" --args --remote-debugging-port=9222
```

Then use `--browser-attach-running` to reuse that session:

```bash
oracle --engine browser --browser-attach-running \
  -p "Quick auth test. Reply with OK."
```

**Fallback: manual-login profile** (when cookie DB and attach both fail)

Creates a separate Chrome profile for oracle. Run this ONCE to set up:

```bash
oracle --engine browser --browser-manual-login --browser-keep-browser \
  --browser-input-timeout 120000 -p "HI"
```

After setup, all subsequent `--browser-manual-login` runs reuse that profile.
If the profile goes stale (logged out), re-run the setup command above.

## Quick Commands

```bash
# Show help (run once per session)
oracle --help

# Preview bundle without spending tokens
oracle --dry-run summary -p "<task>" --file "src/**" --file "!**/*.test.*"

# Token/cost sanity check
oracle --dry-run summary --files-report -p "<task>" --file "src/**"

# Browser run — cookie DB (primary; close Chrome first)
unset ORACLE_BROWSER_COOKIES_FILE
oracle --engine browser \
  --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-cookie-wait 10s \
  --browser-auto-reattach-delay 30s --browser-auto-reattach-interval 2m \
  --browser-auto-reattach-timeout 2m --browser-timeout 20m \
  --model gpt-5.5-pro -p "<task>" --file "src/**"

# Browser run — attach to running Chrome (when already open with --remote-debugging-port=9222)
oracle --engine browser --browser-attach-running \
  --browser-auto-reattach-delay 30s --browser-auto-reattach-interval 2m \
  --browser-auto-reattach-timeout 2m --browser-timeout 20m \
  --model gpt-5.5-pro -p "<task>" --file "src/**"

# Browser run — manual-login fallback (when cookie DB and attach both fail)
oracle --engine browser --browser-manual-login \
  --browser-auto-reattach-delay 30s --browser-auto-reattach-interval 2m \
  --browser-auto-reattach-timeout 2m --browser-timeout 20m \
  --model gpt-5.5-pro -p "<task>" --file "src/**"

# Browser run with output file (cookie DB variant)
unset ORACLE_BROWSER_COOKIES_FILE
oracle --engine browser \
  --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-cookie-wait 10s \
  --browser-auto-reattach-delay 30s --browser-auto-reattach-interval 2m \
  --browser-auto-reattach-timeout 2m --browser-timeout 20m \
  --model gpt-5.5-pro -p "<task>" --file "src/**" \
  --write-output /tmp/oracle_output.md --slug "descriptive-slug"

# Manual paste fallback (assemble bundle, copy to clipboard)
oracle --render --copy -p "<task>" --file "src/**"

# ChatGPT Project Sources (persistent shared context)
oracle project-sources list \
  --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-cookie-wait 10s \
  --chatgpt-url "https://chatgpt.com/g/g-p-.../project"
oracle project-sources add --dry-run \
  --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
  --browser-cookie-wait 10s \
  --chatgpt-url "https://chatgpt.com/g/g-p-.../project" \
  --file AGENTS.md --file README.md --file docs/architecture.md

# API provider readiness check
oracle doctor --providers --models gpt-5.4,claude-4.6-sonnet,gemini-3-pro

# Sessions (list and reattach)
oracle status --hours 72
oracle session <id> --render
oracle restart <id>
```

### Important Browser Run Notes

- **Primary auth: Chrome cookie DB.** Close Chrome before running — the cookie
  database is locked while Chrome is open. Oracle will fail to read cookies if
  Chrome is running. Always clear `ORACLE_BROWSER_COOKIES_FILE` (unset it)
  before using `--browser-cookie-path`; the env var can conflict with explicit
  cookie flags and cause misleading failures.
- **Alternative: attach to running Chrome.** Start Chrome with
  `--remote-debugging-port=9222`, then use `--browser-attach-running`. This
  reuses your live, logged-in session. No cookie DB reads needed.
- **Fallback: manual-login profile.** Use `--browser-manual-login` when both
  cookie DB and attach-running fail. This uses a separate Chrome profile that
  requires a one-time manual ChatGPT login. If the profile goes stale, re-run
  the setup: `oracle --engine browser --browser-manual-login --browser-keep-browser
  --browser-input-timeout 120000 -p "HI"`.
- Treat `--browser-cookie-path`, `--browser-chrome-profile`, and
  `--browser-manual-login` as separate auth paths. One can be logged in while
  another fails. Never mix them in a single command.
- **Always auth-probe first.** Before any substantial browser-mode run, execute
  a tiny auth test: `-p "Quick auth test. Reply with OK."`. Only proceed with
  the full prompt after it returns `OK`. This saves you from waiting 10-20
  minutes only to discover a login failure.
- Before a substantial browser-mode consult, try to identify a ChatGPT Project
  for the current directory and use it as shared context. Check, in order:
  the user prompt, directory-local docs/config (`AGENTS.md`, `README*`, `docs/**`,
  `.oracle*`) for `https://chatgpt.com/g/.../project`, `~/.oracle/config.json`
  (`browser.chatgptUrl` or `browser.url`), and recent Oracle/browser URL
  history. A valid Project URL ends in `/project`, e.g.
  `https://chatgpt.com/g/g-p-.../project`.
- If no Project exists for the directory, create or obtain one before repeated
  Oracle work. Current Oracle CLI support can list/add Project Sources but does
  not expose a `create project` command. If a browser/UI automation tool that can
  create ChatGPT Projects is available, create a Project named after the
  directory/repo; otherwise ask the user to create it in ChatGPT and provide the
  `/project` URL. Save the URL in `~/.oracle/config.json` as
  `browser.chatgptUrl` or pass it with `--chatgpt-url`.
- Seed a new Project with durable context that will help all future sessions:
  root instructions (`AGENTS.md`, `CLAUDE.md`), `README*`, architecture/design
  docs, package/build/test config, benchmark specs, API schemas, and stable
  domain notes. Do not upload secrets, generated artifacts, large vendored
  trees, logs, datasets, caches, or temporary files.
- Run `oracle project-sources add ... --dry-run` first. Only run without
  `--dry-run` after reviewing the planned uploads; Project Sources are
  persistent and Oracle v1 is append-only (no delete/replace/sync command).
- Always add auto-reattach flags for GPT-5.5 Pro runs (>60K tokens) — they
  can take 10-20 minutes and the CLI may lose the tab connection.
- If a run times out, do NOT re-run; reattach with `oracle session <id> --render`.
- Use `--force` if Oracle warns about a duplicate prompt (different context is fine).
- API mode is NOT used in this repo (user preference).

### Browser Auth Troubleshooting

**Cookie DB failures (most common)**

- **Chrome is running → cookie DB locked.**
  Symptom: oracle hangs or fails with an empty/inaccessible cookie DB.
  Fix: quit Chrome completely (`Cmd+Q`), then re-run. The cookie DB is
  exclusively locked while Chrome is open.
- **`ORACLE_BROWSER_COOKIES_FILE` env var set → conflicts with explicit flags.**
  Symptom: `--browser-cookie-path` appears ignored; oracle launches a fresh
  unauthenticated Chrome.
  Fix: `unset ORACLE_BROWSER_COOKIES_FILE` before the command. This env var
  shadows explicit `--browser-cookie-path` and can cause confusing failures.
- **Wrong cookie DB path.**
  Symptom: oracle reports no cookies found, or launches unauthenticated.
  Fix: verify the path — on macOS it's
  `"$HOME/Library/Application Support/Google/Chrome/Default/Cookies"`. For
  non-Default profiles, replace `Default` with the profile directory name
  (e.g. `Profile 1`). Use `--browser-cookie-wait 10s` to handle transient
  locks from background Chrome processes.
- **Cookies expired or signed out.**
  Symptom: auth probe returns a login wall instead of `OK`.
  Fix: open Chrome normally, sign into ChatGPT, close Chrome, then retry
  with cookie DB. If the session was expired, a fresh login is needed.

**Attach-running failures**

- **Chrome not started with remote debugging.**
  Symptom: `--browser-attach-running` can't connect.
  Fix: quit Chrome, relaunch with `open -a "Google Chrome" --args
  --remote-debugging-port=9222`, verify with `curl http://127.0.0.1:9222/json`.
- **Wrong port.**
  Symptom: connection refused on 9222.
  Fix: check the port Chrome is using. Oracle defaults to 9222; override with
  `--remote-chrome 127.0.0.1:<port>`.

**Manual-login failures**

- **Profile logged out / stale.**
  Symptom: Chrome opens but ChatGPT shows a login screen.
  Fix: re-run the one-time setup:
  `oracle --engine browser --browser-manual-login --browser-keep-browser --browser-input-timeout 120000 -p "HI"`.
  Log in manually in the opened window, then let the command complete.
- **`setTypeOfService EINVAL`.**
  Symptom: macOS Keychain permission prompt blocked.
  Fix: switch to cookie DB auth (close Chrome, unset
  `ORACLE_BROWSER_COOKIES_FILE`, use `--browser-cookie-path`). This error
  is specific to Keychain-based cookie access and does not occur with
  explicit cookie DB paths.

**General**

- **Mixing auth flags.** Don't combine `--browser-manual-login` with
  `--browser-cookie-path` or `--browser-attach-running`. Pick one auth
  path per command. Conflicting flags produce unpredictable results.
- **Project sources auth mismatch.** Project sources commands (list/add)
  use the same auth flags as runs. If `project-sources list` works but a
  full run fails, the auth flags likely differ between the two commands —
  copy the exact flags that worked.

## Attaching Files (`--file`)

- Include: `--file "src/**"`, `--file src/index.ts`, `--file docs --file README.md`
- Exclude: `--file "src/**" --file "!src/**/*.test.ts" --file "!**/*.snap"`
- Default-ignored: `node_modules`, `dist`, `coverage`, `.git`, `.turbo`, `.next`, `build`, `tmp`
- Honors `.gitignore`; dotfiles filtered by default; files > 1 MB rejected
- Target: keep total input under ~196k tokens

## Prompt Template

For one-shot runs, Oracle starts with **zero** project knowledge. If browser
mode is pointed at a ChatGPT Project, still include the task-specific context;
the Project is shared background, not a replacement for a precise prompt.
Include:

1. **Project briefing**: stack, build/test commands, platform constraints
2. **File map**: key directories, entrypoints, config files, dependency boundaries
3. **Exact question**: what you tried, error text (verbatim), constraints
4. **Desired output**: "return patch plan + tests", "list risky assumptions", "give 3 options with tradeoffs"

## Engines

- **Browser** (default when no `OPENAI_API_KEY`): automates ChatGPT in Chrome. Supports GPT and Gemini. Stable on macOS.
- **API**: requires `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY` in env. Supports all models including Claude, Grok, Codex.
- API runs require explicit user consent before starting (they cost money).

## ChatGPT Project Workflow

Use a ChatGPT Project for any repo or directory that will need repeated Oracle
sessions. The goal is to avoid re-uploading stable context and to keep related
Oracle chats grouped.

1. Identify the target directory/repo name and search for an existing Project
   URL in directory-local context first:
   ```bash
   rg -n "https://chatgpt\\.com/g/[^[:space:]\")]+/project" \
     AGENTS.md README* docs .oracle* 2>/dev/null
   ```
   Then check the global Oracle config:
   ```bash
   jq -r '.browser.chatgptUrl // .browser.url // empty' ~/.oracle/config.json
   ```
2. If a Project URL exists, verify it:
   ```bash
   oracle project-sources list \
     --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
     --browser-cookie-wait 10s \
     --chatgpt-url "<project-url>"
   ```
3. If no Project URL exists, create a ChatGPT Project for that directory in the
   ChatGPT UI, copy the URL ending in `/project`, and either add it to
   `~/.oracle/config.json`:
   ```json
   {
     "engine": "browser",
     "browser": {
       "chatgptUrl": "https://chatgpt.com/g/g-p-.../project",
       "cookiePath": "/Users/abf/Library/Application Support/Google/Chrome/Default/Cookies"
     }
   }
   ```
   or pass it per run with `--chatgpt-url`.
4. Choose Project Sources conservatively. Prefer durable, high-signal files:
   repo instructions, README, architecture docs, dependency manifests, test
   commands, API/schema docs, benchmark/evaluation specs, and core domain notes.
5. Preview uploads:
   ```bash
   oracle project-sources add --dry-run \
     --browser-cookie-path "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" \
     --browser-cookie-wait 10s \
     --chatgpt-url "<project-url>" \
     --file AGENTS.md --file README.md --file docs/architecture.md
   ```
6. If the dry run is correct and the user has approved the persistent mutation,
   repeat without `--dry-run`.
7. For future browser consults, include `--chatgpt-url "<project-url>"` unless
   it is configured globally. Continue attaching task-specific files with
   `--file`; Project Sources are shared background context, not a substitute for
   the exact code under review.

## Sessions

- Stored under `~/.oracle/sessions`
- If CLI times out: **do not re-run** — reattach with `oracle session <id> --render`
- Use `--slug "<3-5 words>"` for readable session IDs
- Duplicate prompt guard: use `--force` to override

## Safety

- Don't attach secrets (`.env`, key files, auth tokens)
- Prefer "just enough context": fewer files + better prompt beats whole-repo dumps
- Verify outputs against the codebase and tests — oracle is advisory, not authoritative
