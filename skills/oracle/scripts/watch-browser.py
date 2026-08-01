#!/usr/bin/env python3
"""Read-only Oracle browser/session watchdog.

This intentionally never clicks or mutates the browser. It combines Oracle's
session metadata with a small CDP Runtime.evaluate probe so attachment
readiness and server-side submission are checked against the actual tab.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import websocket
except ImportError as exc:  # pragma: no cover - depends on the host environment
    raise SystemExit(
        "watch-browser.py requires Python package websocket-client; "
        "install it with `python3 -m pip install --user websocket-client`."
    ) from exc


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def http_json(port: int, path: str) -> Any:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}{path}", timeout=3
        ) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def target_for(port: int, target_id: str | None, url_hint: str) -> dict[str, Any] | None:
    tabs = http_json(port, "/json/list")
    if not isinstance(tabs, list):
        return None
    pages = [tab for tab in tabs if tab.get("type") == "page"]
    if target_id:
        for tab in pages:
            if tab.get("id") == target_id:
                return tab
    for tab in pages:
        if url_hint in str(tab.get("url", "")):
            return tab
    return pages[0] if len(pages) == 1 else None


def evaluate(tab: dict[str, Any], port: int, expression: str) -> dict[str, Any] | None:
    endpoint = tab.get("webSocketDebuggerUrl")
    if not endpoint:
        return None
    try:
        socket = websocket.create_connection(
            endpoint,
            timeout=5,
            origin=f"http://127.0.0.1:{port}",
        )
        socket.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": True,
                    },
                }
            )
        )
        while True:
            message = json.loads(socket.recv())
            if message.get("id") == 1:
                socket.close()
                value = message.get("result", {}).get("result", {}).get("value")
                return value if isinstance(value, dict) else None
    except Exception:
        return None


DOM_PROBE = r"""
(async () => {
  const body = document.body?.innerText || '';
  const promptPrefix = PROMPT_PREFIX_SENTINEL;
  const buttons = [...document.querySelectorAll('button')].map((button) => ({
    text: (button.innerText || button.getAttribute('aria-label') || button.title || '').trim(),
    disabled: Boolean(button.disabled || button.getAttribute('aria-disabled') === 'true')
  }));
  const messages = [...document.querySelectorAll('[data-message-author-role]')].map((node) => ({
    role: node.getAttribute('data-message-author-role'),
    chars: (node.innerText || '').trim().length,
    hasPromptPrefix: (node.innerText || '').includes(promptPrefix)
  }));
  const labels = [...document.querySelectorAll('[aria-label], [title]')]
    .map((node) => (node.getAttribute('aria-label') || node.title || '').trim())
    .filter(Boolean);
  const send = buttons.find((button) => /^(send|send message)$/i.test(button.text));
  const processing = /uploading|processing|analyzing file|reading file|waiting for file/i.test(body);
  const loginUrl = /\/auth\/|login|sign[- ]?up/i.test(location.pathname);
  const composer = Boolean(document.querySelector('textarea, [contenteditable="true"]'));
  const userMessages = messages.filter((message) => message.role === 'user');
  const assistantMessages = messages.filter((message) => message.role === 'assistant');
  const composerText = [...document.querySelectorAll('textarea, [contenteditable="true"]')]
    .map((node) => (node.value || node.innerText || node.textContent || '').trim())
    .join('\n');
  let sessionUser = false;
  try {
    const response = await fetch('/api/auth/session', { credentials: 'include' });
    const session = await response.json();
    sessionUser = Boolean(session && session.user);
  } catch {}
  return {
    url: location.href,
    title: document.title,
    authenticated: !loginUrl && (sessionUser || composer || userMessages.length > 0 || assistantMessages.length > 0),
    composerPresent: composer,
    promptPrefixPresent: !promptPrefix || body.includes(promptPrefix) || composerText.includes(promptPrefix),
    promptSubmittedInDom: userMessages.some((message) => message.hasPromptPrefix),
    assistantChars: assistantMessages.reduce((sum, message) => sum + message.chars, 0),
    sendVisible: Boolean(send),
    sendEnabled: Boolean(send && !send.disabled),
    attachmentLabels: [...new Set(labels.filter((label) => /\.(md|txt|json|csv|zip|py|ts|tsx|js|jsx|pdf)$/i.test(label)))].slice(-8),
    visibleText: body.slice(-20000),
    attachmentProcessing: processing,
    stopControl: buttons.some((button) => /stop generating|stop answering/i.test(button.text)),
    continuationControl: buttons.some((button) => /answer now|continue|resume|regenerate|try again/i.test(button.text)),
    visibleError: /something went wrong|error generating|network error/i.test(body),
  };
})()
"""


def state_snapshot(
    meta_path: Path,
    port: int,
    expected_file: str | None,
    prompt_prefix: str | None,
    url_hint: str,
) -> dict[str, Any]:
    meta = read_json(meta_path) or {}
    runtime = meta.get("browser", {}).get("runtime", {})
    target = target_for(port, runtime.get("chromeTargetId"), url_hint)
    expression = DOM_PROBE.replace(
        "PROMPT_PREFIX_SENTINEL", json.dumps(prompt_prefix or "")
    )
    dom = evaluate(target, port, expression) if target else None
    prompt_seen = bool(runtime.get("promptSubmitted"))
    if dom:
        prompt_seen = prompt_seen or bool(dom.get("promptSubmittedInDom"))
        prompt_seen = prompt_seen or bool(dom.get("promptPrefixPresent")) and bool(
            dom.get("promptSubmittedInDom")
        )
    expected_name = Path(expected_file).name if expected_file else None
    labels = dom.get("attachmentLabels", []) if dom else []
    visible_text = str(dom.get("visibleText", "")) if dom else ""
    attachment_present = bool(
        expected_name
        and (any(expected_name in label for label in labels) or expected_name in visible_text)
    )
    attachment_ready = not expected_name or (
        attachment_present and not bool(dom and dom.get("attachmentProcessing"))
    )
    authenticated = bool(dom and dom.get("authenticated"))
    submitted = prompt_seen
    assistant_chars = int(dom.get("assistantChars", 0)) if dom else 0
    complete = submitted and assistant_chars >= 120 and not bool(
        dom and (dom.get("stopControl") or dom.get("continuationControl"))
    )
    if not dom:
        phase = "cdp-unavailable"
    elif not authenticated:
        phase = "authentication-required"
    elif dom.get("visibleError"):
        phase = "browser-error"
    elif complete:
        phase = "completed"
    elif submitted:
        phase = "submitted" if assistant_chars == 0 else "streaming"
    elif expected_name and not attachment_present:
        phase = "attachment-missing"
    elif not attachment_ready:
        phase = "attachment-processing"
    elif dom.get("sendEnabled") and (
        not prompt_prefix or bool(dom.get("promptPrefixPresent"))
    ) and (not expected_name or attachment_ready):
        phase = "takeover-ready"
    elif prompt_prefix and not dom.get("promptPrefixPresent"):
        phase = "prompt-mismatch"
    else:
        phase = "composing"
    return {
        "phase": phase,
        "oracleStatus": meta.get("status"),
        "targetUrl": (dom or {}).get("url") or runtime.get("tabUrl"),
        "authenticated": authenticated,
        "promptSubmitted": submitted,
        "promptPrefixPresent": bool(dom and dom.get("promptPrefixPresent")),
        "expectedAttachment": expected_name,
        "attachmentPresent": attachment_present,
        "attachmentReady": attachment_ready,
        "attachmentLabels": labels,
        "sendEnabled": bool(dom and dom.get("sendEnabled")),
        "assistantChars": assistant_chars,
        "stopControl": bool(dom and dom.get("stopControl")),
        "continuationControl": bool(dom and dom.get("continuationControl")),
        "visibleError": bool(dom and dom.get("visibleError")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="Oracle session slug or id")
    parser.add_argument("--meta", type=Path, help="Path to Oracle session meta.json")
    parser.add_argument("--port", type=int, default=int(os.environ.get("ORACLE_CHROME_DEBUG_PORT", "9222")))
    parser.add_argument("--context", type=Path, help="Expected uploaded context file")
    parser.add_argument("--prompt", type=Path, help="Prompt file, used only for local bookkeeping")
    parser.add_argument("--url-hint", default="chatgpt.com")
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--submission-deadline", type=float, default=90)
    parser.add_argument("--completion-timeout", type=float, default=7200)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--output", type=Path, help="Append transition JSON to this file")
    args = parser.parse_args()

    if not args.meta and not args.session:
        parser.error("one of --session or --meta is required")
    meta_path = args.meta or Path.home() / ".oracle" / "sessions" / args.session / "meta.json"
    prompt_prefix = None
    if args.prompt:
        try:
            prompt_prefix = next(
                (line.strip()[:80] for line in args.prompt.read_text(encoding="utf-8").splitlines() if line.strip()),
                None,
            )
        except OSError:
            pass

    started = time.monotonic()
    last_signature: tuple[Any, ...] | None = None
    while True:
        state = state_snapshot(
            meta_path,
            args.port,
            str(args.context) if args.context else None,
            prompt_prefix,
            args.url_hint,
        )
        signature = (
            state["phase"],
            state["oracleStatus"],
            state["attachmentPresent"],
            state["attachmentReady"],
            state["promptSubmitted"],
            state["assistantChars"] > 0,
            state["sendEnabled"],
        )
        if signature != last_signature:
            line = json.dumps({"timestamp": time.time(), **state}, sort_keys=True)
            print(line, flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            last_signature = signature

        elapsed = time.monotonic() - started
        if args.once:
            return 0
        if not state["promptSubmitted"] and elapsed >= args.submission_deadline:
            print(
                json.dumps(
                    {
                        "error": "submission deadline exceeded",
                        "action": "interrupt_oracle_and_rebuild_only_after_confirming_no_user_turn",
                    }
                ),
                file=sys.stderr,
            )
            return 2
        if state["promptSubmitted"] and state["phase"] == "completed":
            return 0
        if elapsed >= args.completion_timeout:
            print(json.dumps({"error": "completion timeout exceeded"}), file=sys.stderr)
            return 3
        time.sleep(max(args.interval, 0.5))


if __name__ == "__main__":
    raise SystemExit(main())
