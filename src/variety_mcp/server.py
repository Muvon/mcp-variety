"""The MCP server: three tools over stdio."""

import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from variety_mcp.check import check_text
from variety_mcp.history import ConfigError, History, state_file, window_from_env
from variety_mcp.kinds import Kind, KindDataError, load_kinds
from variety_mcp.protocol import HOSTED_OPTION, describe_kinds, describe_pick
from variety_mcp.select import choose

INSTRUCTIONS = (
    "Call variety_pick before writing each piece of a repeated writing job (posts, replies, emails and so on) "
    "and follow the protocol it returns. Use one stable scope label per account or project. "
    "Call variety_check on the draft before you hand it over. " + HOSTED_OPTION
)


def _get_kind(kinds: dict[str, Kind], name: str) -> Kind:
    if name not in kinds:
        raise ValueError(f"unknown kind '{name}'; valid kinds: {list(kinds)}")
    return kinds[name]


def create_server(history: History) -> FastMCP:
    kinds = load_kinds()
    server = FastMCP("variety-mcp", instructions=INSTRUCTIONS)

    @server.tool()
    def variety_pick(kind: str, scope: str, avoid: list[str] | None = None) -> dict[str, Any]:
        """Pick an approach and a form (opening, length, ending) for the next piece of writing.

        Call this before writing each piece of a repeated job. `kind` is one of the ids from variety_kinds.
        `scope` is a stable label for the account or project; picks never repeat a recent combination inside
        one scope. If the returned approach does not suit the input, call again with its id in `avoid`.
        Returns the chosen approach and form plus a plain-text `protocol` to follow while writing.
        """
        chosen = _get_kind(kinds, kind)
        recent = history.recent_picks(scope, chosen.id)
        pick = choose(chosen, recent, history.window, avoid or [])
        # Keep enough picks for both rules: the tuple window and the approach rotation.
        keep = max(history.window, len(chosen.approaches) - 1)
        history.record_pick(scope, chosen.id, pick.record(), keep)
        return describe_pick(chosen, scope.strip(), pick)

    @server.tool()
    def variety_kinds() -> dict[str, Any]:
        """List every kind of writing with its description, its approaches and the values of each form axis."""
        return describe_kinds(kinds)

    @server.tool()
    def variety_check(text: str, scope: str | None = None) -> dict[str, Any]:
        """Check a draft for common signs of AI writing.

        Flags em dashes, stock phrases, "not just X, but Y" constructions, evenly sized sentences and too many
        exclamation marks. With `scope`, it also flags an opening that matches a different recent text in that
        scope, then remembers this opening. Returns `issues` (rule, excerpt, advice) and `ok`.
        """
        return check_text(text, history, scope)

    return server


def main() -> None:
    try:
        history = History(state_file(), window_from_env())
        server = create_server(history)
    except (ConfigError, KindDataError) as error:
        sys.exit(f"variety-mcp: {error}")
    server.run(transport="stdio")
