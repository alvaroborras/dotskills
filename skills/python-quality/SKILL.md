---
name: python-quality
description: Prefer Ruff for formatting and linting, and ty for type checking, in Python projects. Use when editing Python files, validating Python changes, or when the user asks for formatting, lint fixes, or type checks.
---

# Python Quality

Use this skill whenever the task involves Python code quality work.

## Defaults

- Prefer **Ruff** for formatting and linting.
- Prefer **ty** for type checking.
- Use the project's existing configuration from `pyproject.toml`, `ruff.toml`, and `ty.toml`.
- Do not switch to Black, isort, mypy, or pyright unless the user explicitly asks or the repository clearly requires them.
- Default to the smallest relevant scope:
  - edited files first
  - then the affected package or module if needed
  - the whole repository only when asked or when validating the full project

## Choose the runner

Before running commands, quickly inspect the repository:

1. If the project uses `uv` (`uv.lock` exists, or repo docs/config clearly indicate uv), prefer:
   - `uv run ruff ...`
   - `uv run ty ...`
2. Else if it uses Poetry (`poetry.lock`), prefer:
   - `poetry run ruff ...`
   - `poetry run ty ...`
3. Else if it uses Pipenv (`Pipfile`), prefer:
   - `pipenv run ruff ...`
   - `pipenv run ty ...`
4. Otherwise, if the tools are on `PATH`, use:
   - `ruff ...`
   - `ty ...`

If Ruff or ty are unavailable, say so clearly and ask before installing anything or substituting other tools.

## Standard commands

Replace `<paths>` with the smallest appropriate set of files or directories.

### Format

```bash
<runner> ruff format <paths>
```

### Lint with fixes

```bash
<runner> ruff check --fix <paths>
```

### Lint verification

```bash
<runner> ruff check <paths>
```

### Type check

```bash
<runner> ty check <paths>
```

## Typical workflow after Python edits

1. Read repo config if needed (`pyproject.toml`, `ruff.toml`, `ty.toml`).
2. Format the edited Python files with Ruff.
3. If appropriate, apply safe Ruff fixes:
   ```bash
   <runner> ruff check --fix <paths>
   ```
4. Re-run Ruff checks to verify:
   ```bash
   <runner> ruff check <paths>
   ```
5. Run ty on the same scope, or on a slightly wider scope if imports or package boundaries require it:
   ```bash
   <runner> ty check <paths>
   ```

## Reporting

- Summarize the commands you ran.
- If Ruff or ty report issues, show the important errors briefly.
- If a fix would touch unrelated files, ask first.
- If the user only asked for formatting, do not automatically expand to full-repo linting or type checking unless asked.

## Notes

- For full-project validation, repo-specific wrappers like `make lint`, `just check`, or similar are fine if they clearly wrap Ruff and ty.
- For targeted edits, prefer direct Ruff and ty commands over broader wrapper scripts.
