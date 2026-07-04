---
name: pyrefly-cli
description: Run PyRefly's CLI type checker for Python changes. Use when Codex creates or modifies Python files, changes API/function signatures, updates imports, or needs a fast static-analysis gate before finishing work.
---

# PyRefly CLI

Use PyRefly as a type checker in the coding loop. It is not a formatter and does not replace tests.

## Workflow

1. From the project root, inspect local guidance first: `AGENTS.md`, `pyrefly.toml`, or `[tool.pyrefly]` in `pyproject.toml`.
2. Run the command specified by the repo. If none is specified, run:

   ```bash
   pyrefly check
   ```

3. If the repo uses a rollout preset, preserve it. Common gates include:

   ```bash
   pyrefly check --preset basic
   pyrefly check --summarize-errors
   ```

4. Fix type errors caused by your changes and run PyRefly again.
5. Report the command and result. If failures remain, identify whether they are pre-existing, outside touched files, or blocked by missing dependencies.

## Path Issues

If `pyrefly` resolves to the wrong environment, prefer the active project Python or environment manager:

```bash
python3 -m pip install --upgrade pyrefly
python3 -m pyrefly check
```

If `python3 -m pyrefly` is unavailable but the environment has a direct binary, use that binary path and mention it in the result.

## File-Scoped Checks

When local guidance asks for touched-file checks, pass the changed files explicitly:

```bash
pyrefly check --preset basic path/to/file.py
```

Remember that PyRefly's per-file mode may ignore `project-includes` and `project-excludes` while still using other config options.
