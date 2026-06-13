---
name: kaggle-notebooks
description: >
  Browse and download Kaggle notebooks from the Code section of competitions.
  Fetches .ipynb files and converts them to clean Python scripts, optionally
  downloading outputs and execution logs. Use when the user wants to browse
  Kaggle kernels, download notebooks as .py files, fetch kernel output data,
  or retrieve execution logs. Triggers on phrases like "download Kaggle
  notebooks", "fetch kernel", "convert Kaggle notebook to Python", "get
  notebook logs", or "browse competition kernels".
---

# Kaggle Notebooks

Fetch Kaggle competition notebooks (kernels), convert to Python scripts,
and optionally download outputs and logs.

## Quick Start

```bash
# List top notebooks for a competition
uv run python scripts/fetch_notebooks.py neurogolf-2026 --list

# Download top 5 notebooks by votes as clean .py files
uv run python scripts/fetch_notebooks.py neurogolf-2026 --top 5

# Download a specific notebook
uv run python scripts/fetch_notebooks.py neurogolf-2026 \
    --kernel konbu17/neurogolf-2026-blended-401-v117

# Download with output data and logs
uv run python scripts/fetch_notebooks.py neurogolf-2026 \
    --kernel konbu17/neurogolf-2026-blended-401-v117 --output --logs

# Download top 3 and also pull their output files
uv run python scripts/fetch_notebooks.py neurogolf-2026 --top 3 --output

# Search for notebooks by keyword
uv run python scripts/fetch_notebooks.py neurogolf-2026 --search "fp16 blend"
```

Requires Kaggle API credentials at `~/.kaggle/kaggle.json` and the `kaggle` package.

## What You Get

```
notebooks/
├── README.md                              # Index with notebook table
├── owner_kernel-slug/                     # Per-notebook directory
│   ├── kernel-slug.py                     # Clean Python script
│   ├── kernel-slug.ipynb                  # Original notebook (reference)
│   ├── kernel-metadata.json               # Kaggle kernel metadata
│   ├── kernel-slug.log                    # Execution log (if --logs)
│   └── _output/                           # Downloaded output (if --output)
│       └── ...
└── ...
```

Each `.py` file is a clean script with:
- Docstring header with kernel metadata (author, URL, votes)
- Removed `get_ipython().system()` calls (replaced with `# pip install` comments)
- Removed `# In[ ]:` cell markers
- Markdown cells preserved as clean comment blocks
- Runnable via `python kernel-slug.py`

## Options

| Flag | Description |
|------|-------------|
| `<competition-slug>` | Competition to search (e.g. `neurogolf-2026`) |
| `--list` | List notebooks with metadata without downloading |
| `--top N` | Download top N notebooks sorted by votes |
| `--kernel <owner/slug>` | Download a specific notebook |
| `--search <term>` | Filter notebooks by search term |
| `--sort-by <field>` | Sort by: `votes`, `recent`, `hotness`, `views` (default: `votes`) |
| `--language <lang>` | Filter by language: `python`, `r`, `julia` (default: all) |
| `--output` | Also download kernel output files (placed in `_output/`) |
| `--logs` | Also download execution logs (saved as `.log` file) |
| `--output-dir <dir>` | Output directory (default: `notebooks/`) |
| `--no-clean` | Keep raw nbconvert output (cell markers, IPython magics) |
| `--max-pages N` | Maximum listing pages (default: 10, 20 per page) |

## Troubleshooting

- **`kaggle` not found**: Install with `uv pip install kaggle`
- **Authentication failed**: Ensure `~/.kaggle/kaggle.json` exists with `username` and `key`
- **Competition not found**: Verify the slug matches the URL path (e.g., `neurogolf-2026` not `NeuroGolf 2026`)
- **nbconvert not available**: Install with `uv pip install nbconvert nbformat`
- **Empty output**: The competition may have no public kernels, or access is restricted
