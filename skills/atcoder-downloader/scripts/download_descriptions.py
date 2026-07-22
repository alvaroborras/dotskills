#!/usr/bin/env python3
"""Download contest problem descriptions from AtCoder as Markdown."""

import argparse
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def fetch_tasks_list(session, contest):
    """Fetch the list of tasks for a contest."""
    url = f"https://atcoder.jp/contests/{contest}/tasks"
    resp = session.get(url, headers=get_headers())
    resp.raise_for_status()

    # Extract task IDs from the table
    # Pattern: /contests/{contest}/tasks/{task_id}
    tasks = []
    pattern = rf'/contests/{re.escape(contest)}/tasks/([^"?]+)'
    for match in re.finditer(pattern, resp.text):
        task_id = match.group(1)
        if task_id not in tasks:
            tasks.append(task_id)

    return tasks


def html_to_markdown(html_content):
    """Convert HTML problem statement to Markdown."""
    text = html_content

    # Remove script and style tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)

    # Convert headers
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', text, flags=re.DOTALL)

    # Convert code blocks
    text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', text, flags=re.DOTALL)

    # Convert inline code
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

    # Convert var tags (math)
    text = re.sub(r'<var>(.*?)</var>', r'$\1$', text)

    # Convert bold and italic
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Convert links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Convert lists
    text = re.sub(r'<ul[^>]*>', '', text)
    text = re.sub(r'</ul>', '', text)
    text = re.sub(r'<ol[^>]*>', '', text)
    text = re.sub(r'</ol>', '', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)

    # Convert paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)

    # Convert line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Convert horizontal rules
    text = re.sub(r'<hr\s*/?>', '\n---\n', text)

    # Convert div/section spans
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)
    text = re.sub(r'<section[^>]*>', '', text)
    text = re.sub(r'</section>', '', text)
    text = re.sub(r'<span[^>]*>', '', text)
    text = re.sub(r'</span>', '', text)

    # Convert images
    text = re.sub(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',  r'![\2](\1)', text)
    text = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>',  r'![](\1)', text)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    import html
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def fetch_task_statement(session, contest, task_id, lang="en"):
    """Fetch the problem statement for a task."""
    url = f"https://atcoder.jp/contests/{contest}/tasks/{task_id}?lang={lang}"
    resp = session.get(url, headers=get_headers())
    resp.raise_for_status()

    # Extract the task statement div content
    match = re.search(r'<div id="task-statement">(.*)', resp.text, re.DOTALL)
    if not match:
        return None

    full_content = match.group(1)

    # Check if task-statement is empty (some tasks like system test tasks don't have statements)
    if '<span class="lang-ja">' not in full_content and '<span class="lang-en">' not in full_content:
        # Check if there's any actual content (not just closing tags)
        # Look for section or h3 tags which indicate real content
        if not re.search(r'<section|<h[1-6]', full_content):
            return None

    # Extract language-specific section
    if lang == "en":
        # Find the lang-en span
        en_match = re.search(r'<span class="lang-en">(.*?)</span>\s*(?:</span>|$)', full_content, re.DOTALL)
        if en_match:
            statement_html = en_match.group(1)
        else:
            # No English version available, fall back to Japanese
            print(f"  Note: English version not available, using Japanese")
            ja_match = re.search(r'<span class="lang-ja">(.*?)</span>\s*(?:<span class="lang-en">|$)', full_content, re.DOTALL)
            if ja_match:
                statement_html = ja_match.group(1)
            else:
                return None
    else:
        # For Japanese, extract the lang-ja section
        ja_match = re.search(r'<span class="lang-ja">(.*?)</span>\s*(?:<span class="lang-en">|$)', full_content, re.DOTALL)
        if ja_match:
            statement_html = ja_match.group(1)
        else:
            statement_html = full_content

    return html_to_markdown(statement_html)


def main():
    parser = argparse.ArgumentParser(description="Download AtCoder problem descriptions as Markdown")
    parser.add_argument("contest", help="Contest ID (e.g., ahc066, abc300)")
    parser.add_argument("--cookie", "-c", required=True, help="Cookie string from browser")
    parser.add_argument("--task", "-t", help="Specific task ID (e.g., ahc066_a). Default: all tasks")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--lang", "-l", default="en", choices=["en", "ja"], help="Language (default: en)")

    args = parser.parse_args()

    # Create session with cookies
    session = requests.Session()
    for item in args.cookie.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            session.cookies.set(key.strip(), value.strip(), domain=".atcoder.jp")

    contest = args.contest
    output_dir = Path(args.output) / contest
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get task list
    if args.task:
        tasks = [args.task]
    else:
        print(f"Fetching task list for {contest}...")
        tasks = fetch_tasks_list(session, contest)
        print(f"Found {len(tasks)} tasks: {', '.join(tasks)}")

    # Download each task
    for task_id in tasks:
        print(f"\nDownloading {task_id}...")
        markdown = fetch_task_statement(session, contest, task_id, lang=args.lang)

        if markdown:
            filename = f"{task_id}.md"
            filepath = output_dir / filename
            filepath.write_text(markdown, encoding="utf-8")
            print(f"  Saved: {filepath}")
        else:
            print(f"  ERROR: Could not extract problem statement")

    print(f"\nDone! Downloaded {len(tasks)} problem descriptions to {output_dir}")


if __name__ == "__main__":
    main()
