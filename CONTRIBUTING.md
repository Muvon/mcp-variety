# Contributing to mcp-variety

Bug reports, ideas and pull requests are welcome. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting Bugs

Use the bug report form. Include the tool call that failed (tool name and arguments), the error text, and your Python, mcp-variety and AI client versions. Report security issues privately as described in [SECURITY.md](SECURITY.md).

## Suggesting Features

Use the feature request form. Describe the writing job and the problem first, then the change you have in mind.

## Development Setup

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer.

```sh
git clone https://github.com/muvon/mcp-variety.git
cd mcp-variety
uv sync
uv run ruff check
uv run ruff format --check
uv run pytest -q
```

To try a build the way a client runs it:

```sh
uv build
uv run python scripts/smoke_wheel.py dist/*.whl
```

## Where Things Live

- `src/mcp_variety/server.py`: the MCP tools.
- `src/mcp_variety/kinds/*.toml`: the approaches and form choices for each kind. Most content changes go here.
- `src/mcp_variety/rules.py` and `check.py`: the writing rules and the draft checker.
- `src/mcp_variety/history.py`: the per-scope history file.
- `bench/`: the benchmark behind the measured result in the README.

## Pull Requests

1. Fork the repository and create a branch.
2. Add or update tests in `tests/` for any behavior change.
3. Make sure ruff and pytest pass.
4. Update `README.md` and `CHANGELOG.md` for user-facing changes.
5. Use [Conventional Commits](https://www.conventionalcommits.org/) messages, such as `feat(check): flag repeated closings`.
6. Disclose material AI help in the pull request and in an `Assisted-by: <tool>` commit trailer.
