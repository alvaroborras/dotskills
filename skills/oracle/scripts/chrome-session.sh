#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '%s\n' \
    'Usage: chrome-session.sh {start|status|stop} [chatgpt-url]' \
    '' \
    'Environment:' \
    '  ORACLE_CHROME_PROFILE_DIR  Persistent profile (default: ~/.oracle/chrome-profile)' \
    '  ORACLE_CHROME_DEBUG_PORT   Local CDP port (default: 9222)' \
    '  ORACLE_CHROME_BINARY       Chrome binary override'
}

action="${1:-status}"
url="${2:-${ORACLE_CHATGPT_URL:-https://chatgpt.com/}}"
profile="${ORACLE_CHROME_PROFILE_DIR:-${HOME}/.oracle/chrome-profile}"
port="${ORACLE_CHROME_DEBUG_PORT:-9222}"
pid_file="${profile}/oracle-chrome.pid"
log_file="${profile}/oracle-chrome.log"

case "$action" in
  start|status|stop) ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 64 ;;
esac

chrome_binary="${ORACLE_CHROME_BINARY:-}"
if [[ -z "$chrome_binary" ]]; then
  for candidate in /opt/google/chrome/chrome google-chrome google-chrome-stable chromium chromium-browser; do
    if [[ "$candidate" == /* && -x "$candidate" ]] || command -v "$candidate" >/dev/null 2>&1; then
      chrome_binary="$candidate"
      break
    fi
  done
fi

if [[ "$action" == start && -z "$chrome_binary" ]]; then
  printf 'No Chrome binary found. Set ORACLE_CHROME_BINARY.\n' >&2
  exit 127
fi

python3 - "$action" "$profile" "$port" "$pid_file" "$log_file" "$url" "$chrome_binary" <<'PY'
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

action, profile, port_text, pid_file, log_file, url, chrome = sys.argv[1:]
port = int(port_text)


def process_rows():
    rows = []
    port_arg = f"--remote-debugging-port={port}"
    profile_arg = f"--user-data-dir={os.path.realpath(profile)}"
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as handle:
                raw = handle.read()
        except (FileNotFoundError, PermissionError, OSError):
            continue
        args = [part.decode(errors="replace") for part in raw.split(b"\0") if part]
        if port_arg in args and profile_arg in args:
            rows.append((int(entry), args))
    return rows


def browser_process_rows():
    return [(pid, args) for pid, args in process_rows() if not any(arg.startswith("--type=") for arg in args)]


def request(path):
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}{path}", timeout=2
        ) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def endpoint_state():
    version = request("/json/version")
    tabs = request("/json/list")
    if not version or not isinstance(tabs, list):
        return None
    return version, tabs


def print_state(state):
    rows = browser_process_rows()
    if not state:
        print(json.dumps({"running": False, "port": port, "profile": profile}))
        return
    version, tabs = state
    safe_tabs = [
        {
            "title": str(tab.get("title", ""))[:120],
            "url": str(tab.get("url", ""))[:240],
            "type": tab.get("type"),
        }
        for tab in tabs
        if tab.get("type") == "page"
    ]
    print(
        json.dumps(
            {
                "running": True,
                "ownedProcessIds": [pid for pid, _ in rows],
                "port": port,
                "profile": profile,
                "browser": version.get("Browser"),
                "tabs": safe_tabs,
            },
            indent=2,
        )
    )


state = endpoint_state()
owned = browser_process_rows()

if action == "status":
    if state and not owned:
        print(
            f"CDP port {port} is occupied by a process that does not own profile "
            f"{profile}; refusing to use it.",
            file=sys.stderr,
        )
        sys.exit(2)
    print_state(state)
    sys.exit(0)

if action == "stop":
    if not owned:
        print_state(state)
        sys.exit(0)
    for pid, _ in owned:
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and browser_process_rows():
        time.sleep(0.25)
    if browser_process_rows():
        print("Owned Chrome did not exit after SIGTERM; refusing SIGKILL.", file=sys.stderr)
        sys.exit(1)
    try:
        os.unlink(pid_file)
    except FileNotFoundError:
        pass
    print(json.dumps({"running": False, "stopped": True, "port": port}))
    sys.exit(0)

if state:
    if not owned:
        print(
            f"CDP port {port} is occupied by a process that does not own profile "
            f"{profile}; refusing to attach.",
            file=sys.stderr,
        )
        sys.exit(2)
    print_state(state)
    print("Existing owned Chrome is ready; sign in once if ChatGPT is not authenticated.")
    sys.exit(0)

if owned:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = endpoint_state()
        if state:
            print_state(state)
            sys.exit(0)
        time.sleep(0.25)
    print("Owned Chrome exists but did not expose CDP within 10 seconds.", file=sys.stderr)
    sys.exit(1)

os.makedirs(profile, mode=0o700, exist_ok=True)
with open(log_file, "ab") as log:
    process = subprocess.Popen(
        [
            chrome,
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--profile-directory=Default",
            "--no-first-run",
            "--no-default-browser-check",
            url,
        ],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )

with open(pid_file, "w", encoding="ascii") as handle:
    handle.write(f"{process.pid}\n")
os.chmod(pid_file, 0o600)

deadline = time.monotonic() + 15
while time.monotonic() < deadline:
    state = endpoint_state()
    if state:
        if not browser_process_rows():
            print("Chrome exposed CDP but ownership could not be verified.", file=sys.stderr)
            sys.exit(2)
        print_state(state)
        print(
            "A dedicated persistent profile is active. Log in to ChatGPT in this window "
            "once; future Oracle runs reuse this browser without cookie extraction."
        )
        sys.exit(0)
    if process.poll() is not None:
        print(f"Chrome exited with status {process.returncode}; see {log_file}.", file=sys.stderr)
        sys.exit(1)
    time.sleep(0.25)

print(f"Chrome did not expose CDP within 15 seconds; see {log_file}.", file=sys.stderr)
sys.exit(1)
PY
