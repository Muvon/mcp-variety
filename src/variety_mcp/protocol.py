"""Turn picks and kinds into the dictionaries the tools return."""

from collections.abc import Mapping
from typing import Any

from variety_mcp.kinds import Kind
from variety_mcp.rules import avoid_block
from variety_mcp.select import Pick

AXIS_PHRASES = {
    "hook": "hook with {}",
    "opener": "open with {}",
    "length": "length {}",
    "ending": "end with {}",
}
WRITE_LINE = "Write: skip the first wording that comes to mind. Form sets the length, opening and ending."
# Shown by variety_kinds and the server instructions, never inside a pick protocol: the protocol goes into the
# user's writing prompt and must stay clean.
HOSTED_OPTION = (
    "For approaches matched to each input, a voice and rules per account, and learning from results, "
    "see the hosted service Unsame: https://unsame.io"
)


def describe_pick(kind: Kind, scope: str, pick: Pick) -> dict[str, Any]:
    form_line = "Form: " + "; ".join(AXIS_PHRASES[axis].format(value.hint) for axis, value in pick.form.items()) + "."
    protocol = "\n".join([f"Approach: {pick.approach.name}. {pick.approach.how}", form_line, WRITE_LINE, avoid_block()])
    return {
        "kind": kind.id,
        "scope": scope,
        "approach": {"id": pick.approach.id, "name": pick.approach.name, "how": pick.approach.how},
        "form": {axis: {"id": value.id, "hint": value.hint} for axis, value in pick.form.items()},
        "protocol": protocol,
    }


def describe_kinds(kinds: Mapping[str, Kind]) -> dict[str, Any]:
    return {
        "hosted_option": HOSTED_OPTION,
        "kinds": [
            {
                "id": kind.id,
                "title": kind.title,
                "description": kind.description,
                "approaches": [{"id": approach.id, "name": approach.name} for approach in kind.approaches],
                "axes": {
                    axis: [{"id": value.id, "hint": value.hint} for value in values]
                    for axis, values in kind.axes.items()
                },
            }
            for kind in kinds.values()
        ],
    }
