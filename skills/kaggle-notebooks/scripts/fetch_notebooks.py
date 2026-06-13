#!/usr/bin/env python3
"""Fetch Kaggle competition notebooks and convert to clean Python scripts.

Usage:
    uv run python fetch_notebooks.py <competition-slug> [options]

Examples:
    uv run python fetch_notebooks.py neurogolf-2026 --list
    uv run python fetch_notebooks.py neurogolf-2026 --top 5
    uv run python fetch_notebooks.py neurogolf-2026 --kernel owner/slug --output --logs
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


# ── Helpers ──────────────────────────────────────────────────────────

def sanitize_dirname(name: str, max_len: int = 64) -> str:
    """Convert a kernel ref or title to a safe directory name."""
    safe = name.replace("/", "_").replace("\\", "_")
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in safe)
    safe = "_".join(safe.split())[:max_len]
    return safe or "notebook"


def strip_ipython_magic(code: str) -> str:
    """Remove get_ipython().system() and get_ipython().run_line_magic() calls."""
    def _replace_shell(m):
        cmd = m.group(1).strip().strip("'").strip('"')
        if cmd.startswith("pip install"):
            return f"# {cmd}"
        return f"# !{cmd}"
    code = re.sub(
        r"get_ipython\(\)\.(?:system|run_line_magic)\s*\(\s*['\"](?:system\s+)?([^'\"]*?)['\"]\s*\)",
        _replace_shell,
        code,
    )
    code = re.sub(r"get_ipython\(\)\.run_line_magic\([^)]+\)", "", code)
    return code


def clean_notebook_py(raw_py: str, metadata: dict) -> str:
    """Convert nbconvert output to a clean runnable script."""
    lines = raw_py.splitlines()

    # Build header docstring
    title = metadata.get("title", "Kaggle Notebook")
    author = metadata.get("author", "Unknown")
    votes = metadata.get("total_votes", "?")
    ref = metadata.get("ref", "")
    url = f"https://www.kaggle.com/code/{ref}" if ref else ""

    header: list[str] = ['"""', f"{title}"]
    if author:
        header.append("")
        header.append(f"Author: {author}")
        header.append(f"Votes: {votes}")
    if url:
        header.append(f"Source: {url}")
    header.append(f"Converted: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    header.append('"""')
    header.append("")

    # Remove nbconvert boilerplate and cell markers
    body: list[str] = []
    for line in lines:
        stripped = line.rstrip()

        # Strip nbconvert coding header
        if stripped in ("#!/usr/bin/env python", "# coding: utf-8"):
            continue

        # Strip cell markers: # In[ ], # In[42], # In[42]:
        if re.match(r"^#\s*In\s*\[\s*\d*\s*\]\s*:?\s*$", stripped):
            # Add blank line between cells for readability
            if body and body[-1] != "":
                body.append("")
            continue

        body.append(line)

    # Join, then clean IPython magics
    result = strip_ipython_magic("\n".join(body))

    # Clean up: collapse 3+ blank lines to 2
    result = re.sub(r"\n{3,}", "\n\n", result)

    # Strip leading blank lines before adding header
    result = result.lstrip("\n")

    return "\n".join(header) + result + "\n"


# ── CLI ──────────────────────────────────────────────────────────────

SORT_OPTIONS = {
    "votes": "voteCount",
    "recent": "dateRun",
    "hotness": "hotness",
    "views": "viewCount",
}


def list_notebooks(api: KaggleApi, args: argparse.Namespace):
    """List notebooks with metadata table."""
    sort_by = SORT_OPTIONS.get(args.sort_by, "voteCount")
    search = args.search or None
    language = args.language or None

    all_kernels: list = []
    page = 1
    while page <= args.max_pages:
        kernels = api.kernels_list(
            competition=args.competition,
            page=page,
            page_size=20,
            sort_by=sort_by,
            language=language,
            search=search,
        )
        if not kernels:
            break
        all_kernels.extend(kernels)
        if len(kernels) < 20:
            break
        page += 1

    print(f"Competition: {args.competition}")
    print(f"Total notebooks found: {len(all_kernels)}")
    print()
    print(f"{'#':>3}  {'Votes':>5}  {'Title':<60}  {'Author':<25}  {'Ref'}")
    print(f"{'='*3}  {'='*5}  {'='*60}  {'='*25}  {'='*40}")

    for i, k in enumerate(all_kernels, 1):
        title = (k.title or "Untitled")[:58]
        author = (k.author or "Unknown")[:23]
        votes = k.total_votes or 0
        ref = k.ref or ""
        print(f"{i:3d}  {votes:5d}  {title:<60}  {author:<25}  {ref}")

    return all_kernels


def fetch_notebook(
    api: KaggleApi,
    kernel_ref: str,
    output_dir: Path,
    *,
    pull_output: bool = False,
    pull_logs: bool = False,
    clean: bool = True,
) -> dict | None:
    """Download a single notebook, convert to .py, optionally pull output/logs."""
    dirname = sanitize_dirname(kernel_ref)
    nb_dir = output_dir / dirname
    nb_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Pulling {kernel_ref} ...")

    # Pull the kernel files
    try:
        api.kernels_pull(kernel_ref, path=str(nb_dir), metadata=True, quiet=False)
    except Exception as e:
        print(f"    ERROR pulling kernel: {e}")
        return None

    # Find the .ipynb file
    ipynb_path = None
    metadata_path = None
    for f in nb_dir.iterdir():
        if f.suffix == ".ipynb":
            ipynb_path = f
        elif f.name == "kernel-metadata.json":
            metadata_path = f

    if not ipynb_path:
        print(f"    WARNING: No .ipynb found in {nb_dir}")
        return None

    # Read metadata from kernel-metadata.json
    metadata: dict = {}
    if metadata_path:
        try:
            metadata = json.loads(metadata_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Enrich metadata from kernel listing (exact ref match)
    try:
        kernels = api.kernels_list(search=kernel_ref, page_size=10)
        if kernels:
            exact = next((k for k in kernels if k.ref == kernel_ref), None)
            if not exact:
                exact = kernels[0]
            metadata.setdefault("title", exact.title)
            metadata.setdefault("author", exact.author)
            metadata.setdefault("total_votes", exact.total_votes)
            metadata.setdefault("ref", exact.ref)
            metadata.setdefault("last_run_time", str(exact.last_run_time) if exact.last_run_time else "")
    except Exception:
        pass

    # Convert to .py
    py_path = nb_dir / f"{ipynb_path.stem}.py"
    try:
        result = subprocess.run(
            ["jupyter", "nbconvert", "--to", "script", str(ipynb_path), "--stdout"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        raw_py = result.stdout
        if result.returncode != 0 or not raw_py.strip():
            print("    WARNING: nbconvert failed, using raw JSON extraction")
            # Fallback: extract code cells from ipynb JSON
            nb = json.loads(ipynb_path.read_text())
            code_lines: list[str] = []
            for cell in nb.get("cells", []):
                if cell.get("cell_type") == "code":
                    source = cell.get("source", [])
                    if isinstance(source, list):
                        code_lines.extend(source)
                    else:
                        code_lines.append(str(source))
                    code_lines.append("\n")
            raw_py = "".join(code_lines)

        if clean and raw_py.strip():
            final_py = clean_notebook_py(raw_py, metadata)
        else:
            final_py = raw_py

        py_path.write_text(final_py)
        print(f"    -> {py_path.name} ({len(final_py.splitlines())} lines)")
    except Exception as e:
        print(f"    ERROR during conversion: {e}")
        return None

    # Pull output
    if pull_output:
        output_subdir = nb_dir / "_output"
        output_subdir.mkdir(exist_ok=True)
        try:
            files, log = api.kernels_output(kernel_ref, path=str(output_subdir), quiet=True)
            count = len(files) if files else 0
            print(f"    Output: {count} file(s) downloaded -> _output/")
        except Exception as e:
            print(f"    ERROR pulling output: {e}")

    # Pull logs
    if pull_logs:
        try:
            log_content = api.kernels_logs(kernel_ref)
            log_path = nb_dir / f"{ipynb_path.stem}.log"
            log_path.write_text(log_content)
            print(f"    Logs: {len(log_content.splitlines())} lines -> {log_path.name}")
        except Exception as e:
            print(f"    ERROR pulling logs: {e}")

    return metadata


def generate_readme(
    output_dir: Path,
    competition: str,
    results: list[dict],
):
    """Generate an index README in the output directory."""
    lines = [
        f"# {competition} — Notebooks",
        "",
        f"*Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        f"Total notebooks: {len(results)}",
        "",
        "| # | Title | Author | Votes | Directory |",
        "|---|-------|--------|-------|-----------|",
    ]

    for i, r in enumerate(results, 1):
        title = (r.get("title") or "Untitled")[:60]
        author = (r.get("author") or "Unknown")[:25]
        votes = r.get("total_votes", "?")
        ref = r.get("ref", "")
        dirname = sanitize_dirname(ref)
        lines.append(
            f"| {i} | [{title}]({dirname}/) | {author} | {votes} | `{dirname}/` |"
        )

    with open(output_dir / "README.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSaved {len(results)} notebooks to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Kaggle competition notebooks and convert to Python scripts"
    )
    parser.add_argument("competition", help="Competition slug (e.g. neurogolf-2026)")
    parser.add_argument("--list", action="store_true", help="List notebooks without downloading")
    parser.add_argument("--top", type=int, metavar="N", help="Download top N notebooks by sort order")
    parser.add_argument("--kernel", type=str, metavar="REF", help="Download a specific kernel (format: owner/slug)")
    parser.add_argument("--search", type=str, default="", help="Filter by search term")
    parser.add_argument("--sort-by", type=str, default="votes", choices=list(SORT_OPTIONS), help="Sort field (default: votes)")
    parser.add_argument("--language", type=str, default=None, help="Language filter (default: all). Use 'python', 'r', 'julia'")
    parser.add_argument("--output", action="store_true", dest="pull_output", help="Also download kernel output files")
    parser.add_argument("--logs", action="store_true", dest="pull_logs", help="Also download execution logs")
    parser.add_argument("--output-dir", type=str, default="notebooks", help="Output directory (default: notebooks/)")
    parser.add_argument("--no-clean", action="store_true", help="Keep nbconvert markers in .py output")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to fetch (default: 10)")
    args = parser.parse_args()

    # Authenticate
    api = KaggleApi()
    try:
        api.authenticate()
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Ensure ~/.kaggle/kaggle.json exists with username and key.")
        sys.exit(1)

    output_dir = Path(args.output_dir)

    # --list mode
    if args.list:
        list_notebooks(api, args)
        return

    # Determine which kernels to fetch
    kernels_to_fetch: list = []

    if args.kernel:
        kernels_to_fetch = [args.kernel]
    elif args.top:
        sort_by = SORT_OPTIONS.get(args.sort_by, "voteCount")
        all_kernels: list = []
        page = 1
        while page <= args.max_pages and len(all_kernels) < args.top:
            batch = api.kernels_list(
                competition=args.competition,
                page=page,
                page_size=min(20, args.top - len(all_kernels) + 20),
                sort_by=sort_by,
                language=args.language,
                search=args.search or None,
            )
            if not batch:
                break
            all_kernels.extend(batch)
            page += 1

        kernels_to_fetch = [k.ref for k in all_kernels[: args.top] if k.ref]
    else:
        print("Specify --list, --top N, or --kernel owner/slug.")
        parser.print_help()
        sys.exit(1)

    if not kernels_to_fetch:
        print("No notebooks found matching criteria.")
        sys.exit(1)

    # Fetch each notebook
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for i, ref in enumerate(kernels_to_fetch, 1):
        print(f"[{i}/{len(kernels_to_fetch)}] {ref}")
        meta = fetch_notebook(
            api,
            ref,
            output_dir,
            pull_output=args.pull_output,
            pull_logs=args.pull_logs,
            clean=not args.no_clean,
        )
        if meta:
            results.append(meta)
        print()

    # Generate index
    generate_readme(output_dir, args.competition, results)


if __name__ == "__main__":
    main()
