#!/usr/bin/env python3
"""Download top submissions from AtCoder contests."""

import argparse
import html
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def get_headers():
    """Return browser-like headers to avoid CloudFront blocks."""
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def fetch_submissions_list(session, contest, task=None, status="AC", user=None, page=1):
    """Fetch the submissions list page and extract submission IDs with scores."""
    params = {"f.Task": task or f"{contest}_a", "f.Language": "", "f.Status": status}
    if user:
        params["f.User"] = user
    if page > 1:
        params["page"] = page

    url = f"https://atcoder.jp/contests/{contest}/submissions?{urlencode(params)}"
    resp = session.get(url, headers=get_headers())
    resp.raise_for_status()

    # Extract submission IDs and scores
    # HTML structure per row:
    #   <td>time</td>
    #   <td>task</td>
    #   <td>user</td>
    #   <td>language</td>
    #   <td class="submission-score" data-id="ID">SCORE</td>
    #   ...
    submissions = []
    lines = resp.text.split("\n")

    # Find all submission rows by looking for <tr> blocks
    in_row = False
    row_lines = []

    for line in lines:
        if "<tr>" in line:
            in_row = True
            row_lines = []
        elif "</tr>" in line and in_row:
            in_row = False
            row_text = "\n".join(row_lines)
            # Extract ID and score from same line
            id_match = re.search(r'data-id="(\d+)"', row_text)
            score_match = re.search(r'submission-score[^>]*>(\d+)', row_text)
            # Extract user from /users/USERNAME pattern
            user_match = re.search(r'/users/([^"]+)"', row_text)

            if id_match:
                submissions.append({
                    "id": id_match.group(1),
                    "score": int(score_match.group(1)) if score_match else 0,
                    "user": user_match.group(1) if user_match else "unknown",
                })
        elif in_row:
            row_lines.append(line)

    # Check for next page
    has_next = "page=" in resp.text and f"page={page + 1}" in resp.text

    return submissions, has_next


def fetch_submission_source(session, contest, submission_id):
    """Fetch the source code for a specific submission."""
    url = f"https://atcoder.jp/contests/{contest}/submissions/{submission_id}"
    resp = session.get(url, headers=get_headers())
    resp.raise_for_status()

    # Extract source code from <pre id="submission-code">
    match = re.search(r'<pre id="submission-code"[^>]*>(.*?)</pre>', resp.text, re.DOTALL)
    if not match:
        return None, {}

    source = html.unescape(match.group(1))

    # Extract metadata - look for <th>Label</th><td>Value</td> pairs
    meta = {}
    meta_keys = ["Submission Time", "Language", "Score", "Code Size", "Exec Time", "Memory"]
    for label in meta_keys:
        # Handle both plain text and <time> tags in td
        pattern = rf'{label}\s*</th>\s*<td[^>]*>(?:<time[^>]*>)?([^<]+)'
        m = re.search(pattern, resp.text)
        if m:
            key = label.lower().replace(" ", "_")
            meta[key] = html.unescape(m.group(1)).strip()

    return source, meta


def detect_extension(language):
    """Map language string to file extension."""
    lang_lower = language.lower()
    if "python" in lang_lower:
        return ".py"
    elif "c++" in lang_lower or "cpp" in lang_lower:
        return ".cpp"
    elif "rust" in lang_lower:
        return ".rs"
    elif "java" in lang_lower:
        return ".java"
    elif "go" in lang_lower:
        return ".go"
    elif "javascript" in lang_lower or "node" in lang_lower:
        return ".js"
    elif "typescript" in lang_lower:
        return ".ts"
    elif "ruby" in lang_lower:
        return ".rb"
    elif "swift" in lang_lower:
        return ".swift"
    elif "kotlin" in lang_lower:
        return ".kt"
    elif "d " in lang_lower or "dlang" in lang_lower:
        return ".d"
    return ".txt"


def main():
    parser = argparse.ArgumentParser(description="Download top AtCoder submissions")
    parser.add_argument("contest", help="Contest ID (e.g., ahc066, abc300)")
    parser.add_argument("--cookie", "-c", required=True, help="Cookie string from browser")
    parser.add_argument("--task", "-t", help="Task ID (e.g., ahc066_a). Default: {contest}_a")
    parser.add_argument("--top", "-n", type=int, default=10, help="Number of top submissions to download (default: 10)")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--user", "-u", help="Filter by username")
    parser.add_argument("--min-score", type=int, default=0, help="Minimum score threshold")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")

    args = parser.parse_args()

    # Create session with cookies
    session = requests.Session()

    # Parse cookie string into dict
    for item in args.cookie.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            session.cookies.set(key.strip(), value.strip(), domain=".atcoder.jp")

    contest = args.contest
    output_dir = Path(args.output) / contest
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching submissions for contest: {contest}")

    # Fetch submissions
    all_submissions = []
    page = 1
    while len(all_submissions) < args.top * 2:  # Fetch extra in case of filtering
        subs, has_next = fetch_submissions_list(
            session, contest, task=args.task, user=args.user, page=page
        )
        all_submissions.extend(subs)
        if not has_next or len(all_submissions) >= args.top * 3:
            break
        page += 1
        time.sleep(args.delay)

    # Sort by score descending
    all_submissions.sort(key=lambda x: x["score"], reverse=True)

    # Filter by min score
    if args.min_score > 0:
        all_submissions = [s for s in all_submissions if s["score"] >= args.min_score]

    # Deduplicate by user (keep highest score per user)
    seen_users = set()
    unique_submissions = []
    for sub in all_submissions:
        if sub["user"] not in seen_users:
            seen_users.add(sub["user"])
            unique_submissions.append(sub)

    # Take top N
    top_submissions = unique_submissions[:args.top]

    print(f"Downloading top {len(top_submissions)} submissions...")

    # Download each submission
    downloaded = 0
    for i, sub in enumerate(top_submissions):
        sub_id = sub["id"]
        score = sub["score"]
        user = sub["user"]

        print(f"\n[{i+1}/{len(top_submissions)}] Submission {sub_id} by {user} (score: {score})")

        source, meta = fetch_submission_source(session, contest, sub_id)
        if not source:
            print(f"  ERROR: Could not extract source code")
            continue

        # Determine extension
        lang = meta.get("language", "")
        ext = detect_extension(lang)

        # Save source code
        filename = f"{user}_{sub_id}{ext}"
        filepath = output_dir / filename
        filepath.write_text(source, encoding="utf-8")
        print(f"  Saved: {filepath}")

        # Save metadata
        meta_filename = f"{user}_{sub_id}_meta.txt"
        meta_filepath = output_dir / meta_filename
        with open(meta_filepath, "w") as f:
            f.write(f"Submission ID: {sub_id}\n")
            f.write(f"User: {user}\n")
            f.write(f"Score: {score}\n")
            for k, v in meta.items():
                f.write(f"{k.replace('_', ' ').title()}: {v}\n")

        downloaded += 1
        time.sleep(args.delay)

    print(f"\nDone! Downloaded {downloaded} submissions to {output_dir}")


if __name__ == "__main__":
    main()
