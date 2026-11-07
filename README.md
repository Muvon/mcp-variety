<div align="center">

# mcp-variety

**A local MCP server that gives an AI a different approach and form for each piece of a repeated writing job**

[![CI](https://github.com/muvon/mcp-variety/actions/workflows/ci.yml/badge.svg)](https://github.com/muvon/mcp-variety/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-variety.svg)](https://pypi.org/project/mcp-variety/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-stdio-green.svg)](https://modelcontextprotocol.io)

[Install](#install) · [Tools](#tools) · [Measured result](#measured-result) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

MCP Registry: [`io.github.Muvon/mcp-variety`](https://registry.modelcontextprotocol.io)

</div>

<!-- mcp-name: io.github.Muvon/mcp-variety -->

---

An AI that writes the same kind of text again and again (social posts, replies, emails) falls into habits: the same opening, the same structure, the same closing line. mcp-variety is a small MCP server that runs on your machine and breaks those habits. Before each new piece, the AI calls it and gets one approach and one form (how to open, how long, how to end), picked at random so that no recent combination repeats for the same account or project. In a test with Claude Sonnet, the share of texts that started with the same three words fell from 58.3% to 2.5% ([details](#measured-result)). The server also ships plain rules against common AI-writing tells and a checker for drafts, and it uses no model, no network and no account.

mcp-variety is the free, local option. [Unsame](https://unsame.io) is the hosted one that matches each input to a fitting approach.

## Example

The AI calls `variety_pick` with `kind: "post"` and `scope: "acme"` (the label of an account or project). It gets back:

```
Approach: Lesson learned. Share one mistake or surprise, what it cost, and what you do differently now.
Form: open with a specific number or result; length about three sentences; end with a question the reader can answer in a line.
Write: skip the first wording that comes to mind. Form sets the length, opening and ending.
Avoid:
- Use no em dashes and no spaced en dashes. Use a period, a comma or a colon instead.
- Skip stock phrases such as "here's the thing", "let's dive in", "game-changer". Say the plain thing.
- Do not build sentences like "not just X, but Y" or "it's not X, it's Y". Say the point once, directly.
- Vary the sentence length. Mix very short sentences with longer ones.
- Use at most 1 exclamation mark per text.
- Do not begin with the same first 3 words as your recent texts in this scope.
```

The next call for `acme` gets a different approach, and no combination of approach, opening, length and ending repeats within the last 12 picks. If the approach does not fit the input, the AI calls again and lists that approach in `avoid`.

## Install

The server needs [uv](https://docs.astral.sh/uv/). `uvx` downloads and runs it, so there is nothing to install by hand. The commands pin version 0.1.0.

Claude Code:

```sh
claude mcp add variety -- uvx mcp-variety==0.1.0
```

Claude Desktop, in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "variety": {
      "command": "uvx",
      "args": ["mcp-variety==0.1.0"]
    }
  }
}
```

Octomind has a `variety` capability in octomind-tap. Its default provider is this server: it runs `uvx mcp-variety==0.1.0` over stdio under the server name `variety`, so there is nothing to add by hand. To use Unsame instead, set this in your Octomind config:

```toml
[capabilities]
variety = "unsame"
```

In Claude Code or Claude Desktop, tell the AI in your instructions to call `variety_pick` before writing each piece, to follow the protocol, and to run `variety_check` on the draft. In Octomind the `writing-variety` skill already says this.

### Settings

| Variable | Default | Meaning |
|---|---|---|
| `VARIETY_MCP_STATE_DIR` | `$XDG_STATE_HOME/mcp-variety`, or `~/.local/state/mcp-variety` | Folder that holds `history.json` |
| `VARIETY_MCP_WINDOW` | `12` | How many recent picks and openings are remembered per scope |

If `history.json` is damaged, the tools return an error that names the file. The server does not reset it for you.

## Tools

`variety_pick(kind, scope, avoid=None)` picks an approach and a form for the next piece and records the pick. `kind` is one of the kinds below. `scope` is a stable label for the account or project. `avoid` is an optional list of approach ids to skip. The result holds the approach, the form and the `protocol` text. Unknown ids in `avoid` return an error that lists the valid ones.

`variety_kinds()` lists every kind with its description, its approaches and the values of each form axis.

`variety_check(text, scope=None)` checks a draft and returns `ok` and a list of `issues`, each with the rule, an excerpt and advice. It flags:

- em dashes and spaced en dashes;
- about 60 stock phrases such as "here's the thing", "let's dive in" and "delve";
- "not just X, but Y" and "it's not X, it's Y" constructions;
- five or more sentences of almost the same length;
- more than one exclamation mark;
- with `scope`, an opening (first three words) that matches a different recent text in that scope. The opening is then remembered. Checking the same text twice does not flag it against itself.

Kinds: `post` (social post), `reply` (comment, mention or customer message), `article` (blog article), `email` (newsletter or outreach), `script` (short video, with an extra hook axis) and `update` (product update or release note). Each has 11 or 12 approaches, taken from common writing frameworks such as problem-agitate-solve, before-after-bridge and situation-complication-question-answer, and 5 or 6 choices of opening, length and ending.

## Measured result

We asked Claude Sonnet (`claude -p --model sonnet`, no tools) for 6 texts per input, for 8 inputs (4 posts, 4 replies): once with a plain prompt and once with the protocol from a real `variety_pick` call in front of it. 96 texts in total. Same opening is the share of text pairs whose first 3 words match. Shared phrases is the share of a text's 3-word phrases that also appear in another text for the same input. Both are averaged over the inputs.

| Measure | Without mcp-variety | With mcp-variety |
|---|---|---|
| Same opening | 58.3% | 2.5% |
| Shared 3-word phrases | 46.7% | 7.4% |
| `variety_check` issues per text | 0.10 | 0.04 |

The sample is small (one model, 8 inputs). The inputs, the method and the per-input numbers are in [`bench/results.md`](bench/results.md); `uv run python bench/run.py` repeats the run.

## When you need more than random picks

mcp-variety keeps texts from repeating each other. It does not choose for a given input, and it has no memory of what worked:

- It does not read your input. The pick is random, so it can suggest an approach that does not fit; `avoid` is how the AI asks again.
- The menus are fixed and generic. You cannot add your own approaches without editing the package files, and there are no voice or always/never rules per account.
- It does not learn. Nothing about which texts worked changes later picks.

[Unsame](https://unsame.io) is a hosted service built for these gaps. You write a playbook per goal with your own approaches, your voice and your always/never rules. An AI judge matches each input to a fitting approach, and the playbook learns from the results you report. It is closed source and runs on Unsame's servers. mcp-variety stays free and local.

## Development

```sh
uv sync
uv run ruff check
uv run ruff format --check
uv run pytest -q
uv build
uv run python scripts/smoke_wheel.py dist/*.whl   # starts the built wheel and lists its tools
uv run python bench/run.py                          # the benchmark; needs the claude CLI
```

## Contributing

Bug reports, ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See `LICENSE`.
