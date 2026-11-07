# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Do not open a public issue. Email security@muvon.io with:

- a description of the vulnerability;
- steps to reproduce;
- the possible impact;
- a suggested fix, if you have one.

You get an acknowledgment within 48 hours and an assessment within 7 days. The fix timeline depends on severity. We credit you in the advisory if you want.

## What the Server Can Access

- **Network**: none. The server speaks MCP over stdio only and opens no port.
- **Files**: it reads its own built-in pattern files and reads and writes one file, `history.json`, in `VARIETY_MCP_STATE_DIR` (default `$XDG_STATE_HOME/mcp-variety` or `~/.local/state/mcp-variety`).
- **History content**: `history.json` holds the scope labels you pass, the recent picks and the first three words and a hash of each checked text. It holds no full drafts.
