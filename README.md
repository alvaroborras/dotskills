# dotskills

Personal collection of [Claude Code](https://claude.ai/code) / [Codex CLI](https://github.com/openai/codex) skills for AI-assisted software development.

## Skills

### Workflow & Quality

| Skill | Description |
|---|---|
| `create-plan` | Generate concise plans for coding tasks |
| `ask-user-question` | Interactive clarification with structured Q&A |
| `code-simplifier` | Simplify code for clarity without changing behavior |
| `tdd` | Test-driven development with red-green-refactor loop |
| `linus-reviewer` | Code review with strict architectural integrity |
| `grill-me` | Interview the user relentlessly about a plan or design |
| `occam` | Apply Occam's Razor — simplify, reduce complexity |

### Python

| Skill | Description |
|---|---|
| `py-code-health` | Dead code, duplicate code, unused imports |
| `py-complexity` | Reduce cyclomatic and cognitive complexity |
| `py-git-hooks` | Pre-commit hooks for ruff, mypy, basedpyright |
| `py-modernize` | Modernize to Python 3.13+, uv, latest patterns |
| `py-quality-setup` | Configure ruff, mypy, basedpyright |
| `py-refactor` | Orchestrate multi-dimensional Python refactoring |
| `py-security` | Security vulnerability detection and remediation |
| `py-test-quality` | Test coverage and mutation testing |
| `python-performance-optimization` | Profile and optimize with cProfile, pyinstrument, memory profilers |
| `python-quality` | Ruff formatting and linting, type checking |
| `python-simplifier` | Simplify overly complex Python code |

### Autonomous Workflows

| Skill | Description |
|---|---|
| `autoresearch` | Autonomous goal-directed iteration |
| `autoresearch-debug` | Scientific method bug hunting |
| `autoresearch-fix` | Autonomous repair loop for failing tests |
| `autoresearch-learn` | Codebase learning and documentation |
| `autoresearch-plan` | Convert goals into validated configurations |
| `autoresearch-predict` | Multi-persona swarm analysis |
| `autoresearch-scenario` | Use cases, edge cases, failure exploration |
| `autoresearch-security` | STRIDE, OWASP, adversarial security audit |
| `autoresearch-ship` | Structured shipping workflow |

### Specialized

| Skill | Description |
|---|---|
| `agentic-data-science-competition` | Kaggle competition workflow automation |
| `building-pydantic-ai-agents` | Build AI agents with Pydantic AI |
| `caveman` | Ultra-compressed communication mode |
| `defuddle` | Extract clean content from web pages |
| `find-skills` | Discover and install skills |
| `instrumentation` | Pydantic Logfire observability |
| `json-canvas` | Create and edit JSON Canvas files |
| `optimize-for-gpu` | GPU-accelerate Python with CuPy, Numba, Warp |
| `pointbreak` | IDE debugger MCP tools |

### Kaggle Modules

The `skills/modules/` directory contains supporting modules for Kaggle workflows:

- `badge-collector` — Automate Kaggle badge progression
- `comp-report` — Competition research and reporting
- `kllm` — Kaggle interaction via kagglehub, kaggle-cli, MCP
- `registration` — Account and credential setup

## Structure

```
skills/
  <skill-name>/
    SKILL.md          # Skill instructions
    references/       # Detailed reference material
    scripts/          # Supporting scripts
    agents/           # Agent definitions
    assets/           # Static assets
```

Each skill is a self-contained directory with at minimum a `SKILL.md` file containing the skill's system prompt.

## License

MIT — see individual skill directories for any additional licenses on bundled content.
