---
name: kaggle-discussions
description: Scrape Kaggle competition discussion forums. Fetch all Q&A threads with author attribution and save as organized Markdown files. Use when the user wants to archive, browse, or analyze Kaggle competition discussion threads, or says "fetch the Kaggle discussions", "scrape the forum", "download discussion threads", or similar.
---

# Kaggle Discussions

Fetch all discussion threads for a Kaggle competition and save them as Markdown files.

## Quick Start

```bash
uv run python scripts/fetch_discussions.py <competition-slug>
```

The script writes to `discussions/` by default. Use `--output-dir` to redirect.

Requires Kaggle API credentials at `~/.kaggle/kaggle.json` and the `kaggle` + `kagglesdk` packages.

## What You Get

```
discussions/
├── README.md              # Index with topic list table
├── Title_One_12345.md     # Per-thread Q&A
├── Title_Two_12346.md
└── ...
```

Each thread file has:
- Thread metadata (URL, author, date, votes)
- Full message tree with nested replies preserved
- Author attribution via content heuristics (Kaggle's API hides author names for invitation-only competitions)

## Author Attribution

Kaggle's API does not return `authorName` for invitation-only competitions. The script infers authors via:

1. **@mentions** in follow-up messages (e.g., reply addresses "@username", so that user is likely the topic starter)
2. **Official phrase detection** — organizer posts are detected by signature phrases and tone
3. **Signature blocks** — explicit team signatures in message content

Authors that can't be resolved show as "Unknown".

## Troubleshooting

- **`kaggle` / `kagglesdk` not found**: Install with `uv pip install kaggle`
- **Authentication failed**: Ensure `~/.kaggle/kaggle.json` exists with `username` and `key`
- **Competition not found**: Verify the slug matches the URL path (e.g., `titanic` not `Titanic`)
- **Empty output**: The competition may have no discussion threads, or the competition is private and requires separate access
