import json
import subprocess
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_variety.server import INSTRUCTIONS

TOOL_NAMES = {"variety_pick", "variety_kinds", "variety_check"}


@asynccontextmanager
async def session_for(state_dir, **extra_env):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_variety"],
        env={"VARIETY_MCP_STATE_DIR": str(state_dir), **extra_env},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield session


def payload(result):
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


async def test_lists_exactly_three_tools(tmp_path):
    async with session_for(tmp_path) as session:
        tools = await session.list_tools()
    assert {tool.name for tool in tools.tools} == TOOL_NAMES


async def test_kinds_lists_every_kind(tmp_path):
    async with session_for(tmp_path) as session:
        data = payload(await session.call_tool("variety_kinds", {}))
    kinds = {kind["id"]: kind for kind in data["kinds"]}
    assert set(kinds) == {"article", "email", "post", "reply", "script", "update"}
    post = kinds["post"]
    assert len(post["approaches"]) >= 6
    assert set(post["axes"]) == {"opener", "length", "ending"}
    assert "hook" in kinds["script"]["axes"]
    assert "https://unsame.io" in data["hosted_option"]


def test_instructions_mention_the_hosted_option():
    assert "https://unsame.io" in INSTRUCTIONS


async def test_pick_returns_a_protocol_and_records_history(tmp_path):
    async with session_for(tmp_path) as session:
        data = payload(await session.call_tool("variety_pick", {"kind": "post", "scope": "acme"}))
    assert data["kind"] == "post"
    assert data["scope"] == "acme"
    assert set(data["form"]) == {"opener", "length", "ending"}
    protocol = data["protocol"]
    assert protocol.startswith(f"Approach: {data['approach']['name']}. {data['approach']['how']}")
    assert "\nForm: open with " in protocol
    assert "\nWrite: skip the first wording" in protocol
    assert "\nAvoid:\n- " in protocol
    assert "unsame" not in protocol.lower()
    history = json.loads((tmp_path / "history.json").read_text())
    assert len(history["scopes"]["acme"]["picks"]["post"]) == 1


async def test_pick_honours_avoid_and_never_repeats_an_approach_early(tmp_path):
    async with session_for(tmp_path) as session:
        kinds = payload(await session.call_tool("variety_kinds", {}))["kinds"]
        approaches = [a["id"] for a in next(kind for kind in kinds if kind["id"] == "reply")["approaches"]]
        avoided = approaches[:2]
        seen = []
        for _ in range(len(approaches) - len(avoided)):
            data = payload(
                await session.call_tool("variety_pick", {"kind": "reply", "scope": "acme", "avoid": avoided})
            )
            seen.append(data["approach"]["id"])
    assert not set(seen) & set(avoided)
    assert len(set(seen)) == len(seen)


async def test_pick_errors_name_the_valid_choices(tmp_path):
    async with session_for(tmp_path) as session:
        unknown_kind = await session.call_tool("variety_pick", {"kind": "poem", "scope": "acme"})
        unknown_avoid = await session.call_tool("variety_pick", {"kind": "post", "scope": "acme", "avoid": ["nope"]})
    assert unknown_kind.isError
    assert "valid kinds" in unknown_kind.content[0].text
    assert unknown_avoid.isError
    assert "valid ids" in unknown_avoid.content[0].text


async def test_check_flags_tells_and_passes_clean_text(tmp_path):
    async with session_for(tmp_path) as session:
        draft = f"Here's the thing {chr(0x2014)} it works."
        dirty = payload(await session.call_tool("variety_check", {"text": draft}))
        clean = payload(await session.call_tool("variety_check", {"text": "It works, and I use it daily."}))
    assert dirty["ok"] is False
    assert {issue["rule"] for issue in dirty["issues"]} == {"em_dash", "stock_phrase"}
    assert clean == {"issues": [], "ok": True}


async def test_check_with_scope_flags_a_repeated_opening(tmp_path):
    async with session_for(tmp_path) as session:
        args = {"scope": "acme"}
        first = payload(await session.call_tool("variety_check", {"text": "Last week I fixed a bug.", **args}))
        second = payload(await session.call_tool("variety_check", {"text": "Last week I wrote a test.", **args}))
    assert first["ok"] is True
    assert [issue["rule"] for issue in second["issues"]] == ["repeated_opening"]


async def test_corrupt_history_is_reported_to_the_client(tmp_path):
    (tmp_path / "history.json").write_text("{broken")
    async with session_for(tmp_path) as session:
        result = await session.call_tool("variety_pick", {"kind": "post", "scope": "acme"})
    assert result.isError
    assert "corrupt" in result.content[0].text


def test_bad_window_stops_the_server_with_a_message(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "mcp_variety"],
        env={"VARIETY_MCP_STATE_DIR": str(tmp_path), "VARIETY_MCP_WINDOW": "zero", "PATH": ""},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert done.returncode != 0
    assert "VARIETY_MCP_WINDOW" in done.stderr
