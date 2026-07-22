---
name: atcoder-downloader
description: >
  Download top solutions and problem descriptions from AtCoder programming contests.
  Use when the user wants to study other participants' code, download submissions,
  fetch best solutions, or get problem statements from a contest. Supports both
  heuristic (AHC) and regular (ABC/ARC) contests. Requires browser cookies for authentication.
---

# AtCoder Downloader

## Quick Start

1. Get cookies from browser (see Cookie Setup below)
2. Run the download scripts:

```bash
# Download top submissions
python3 scripts/download_submissions.py <contest-id> --cookie "<cookie-string>" -n <top-count>

# Download problem descriptions
python3 scripts/download_descriptions.py <contest-id> --cookie "<cookie-string>"
```

## Cookie Setup

AtCoder requires authentication to view submissions. Get cookies from Chrome DevTools:

1. Sign in to https://atcoder.jp in Chrome
2. Open DevTools (F12 or Cmd+Opt+I) → **Network** tab
3. Navigate to any AtCoder page
4. Click any request → **Headers** → copy the `Cookie:` header value
5. Pass to script: `--cookie "paste-here"`

Key cookies needed: `REVEL_SESSION`, `_ga`, `_ga_RC512FD18N`

## Scripts

### download_submissions.py

Download source code from top-scoring submissions.

```bash
# Download top 10 from AHC066
python3 scripts/download_submissions.py ahc066 --cookie "..." -n 10

# Download top 5 from a specific task
python3 scripts/download_submissions.py ahc066 --cookie "..." -t ahc066_a -n 5

# Filter by user
python3 scripts/download_submissions.py ahc066 --cookie "..." --user kurakura

# Minimum score threshold
python3 scripts/download_submissions.py ahc066 --cookie "..." --min-score 10000000

# Custom output directory
python3 scripts/download_submissions.py ahc066 --cookie "..." -o ./solutions
```

### download_descriptions.py

Download problem statements as Markdown.

```bash
# Download all task descriptions (English preferred)
python3 scripts/download_descriptions.py ahc066 --cookie "..."

# Download specific task
python3 scripts/download_descriptions.py ahc066 --cookie "..." -t ahc066_a

# Force Japanese language
python3 scripts/download_descriptions.py ahc066 --cookie "..." --lang ja

# Custom output directory
python3 scripts/download_descriptions.py ahc066 --cookie "..." -o ./problems
```

## Scoring Notes

- **AHC (Heuristic) contests**: Higher score = better (maximize)
- **ABC/ARC contests**: Lower execution time/memory = better, but submissions sorted by AC status
- The script always sorts by score descending, which works correctly for both types

## Output Structure

### Submissions
```
<contest>/
├── username_12345678.cpp      # Source code
├── username_12345678_meta.txt # Metadata (score, language, etc.)
└── ...
```

### Descriptions
```
<contest>/
├── <task_id>.md               # Problem statement in Markdown
└── ...
```

## Troubleshooting

- **403 ERROR**: Cookies expired or invalid. Get fresh cookies from browser.
- **No submissions found**: Check contest ID and task ID are correct.
- **Rate limiting**: Increase delay with `--delay 1.0`
- **Empty task statement**: Some tasks (like system test tasks) don't have public problem statements
