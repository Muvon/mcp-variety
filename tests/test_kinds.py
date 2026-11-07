import copy

import pytest

from mcp_variety.kinds import (
    AXIS_ORDER,
    MAX_AXIS_VALUES,
    MIN_APPROACHES,
    MIN_AXIS_VALUES,
    REQUIRED_AXES,
    KindDataError,
    load_kinds,
    parse_kind,
)

KIND_IDS = ["article", "email", "post", "reply", "script", "update"]


def valid_raw():
    return {
        "title": "Test",
        "description": "A test kind.",
        "approaches": [{"id": f"a{i}", "name": f"Approach {i}", "how": "Do the thing."} for i in range(MIN_APPROACHES)],
        "axes": {
            axis: [{"id": f"{axis}{i}", "hint": "a hint"} for i in range(MIN_AXIS_VALUES)] for axis in REQUIRED_AXES
        },
    }


def test_ships_the_expected_kinds():
    assert sorted(load_kinds()) == KIND_IDS


@pytest.mark.parametrize("kind_id", KIND_IDS)
def test_kind_file_satisfies_the_rules(kind_id):
    kind = load_kinds()[kind_id]
    assert kind.title
    assert kind.description
    assert len(kind.approaches) >= MIN_APPROACHES
    assert len({approach.id for approach in kind.approaches}) == len(kind.approaches)
    for axis in REQUIRED_AXES:
        values = kind.axes[axis]
        assert MIN_AXIS_VALUES <= len(values) <= MAX_AXIS_VALUES
        assert len({value.id for value in values}) == len(values)
        assert all(value.hint for value in values)
    assert set(kind.axes) <= set(AXIS_ORDER)


def test_only_script_has_a_hook():
    kinds = load_kinds()
    assert [kind_id for kind_id, kind in kinds.items() if "hook" in kind.axes] == ["script"]


def test_valid_raw_parses():
    assert parse_kind("test", valid_raw()).id == "test"


def broken(change):
    raw = copy.deepcopy(valid_raw())
    change(raw)
    return raw


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda raw: raw["approaches"].pop(), "at least"),
        (lambda raw: raw["approaches"][1].update(id="a0"), "duplicate"),
        (lambda raw: raw["approaches"][0].update(how="Open with a joke."), "mentions 'Open'"),
        (lambda raw: raw["approaches"][0].update(how="Keep it short."), "mentions 'short'"),
        (lambda raw: raw["approaches"][0].update(name=""), "'name'"),
        (lambda raw: raw["approaches"][0].update(id="Bad Id"), "lowercase"),
        (lambda raw: raw["axes"].pop("ending"), "missing axes"),
        (lambda raw: raw["axes"].update(tone=[]), "unknown axes"),
        (lambda raw: raw["axes"]["opener"].pop(), "needs"),
        (
            lambda raw: raw["axes"]["opener"].extend({"id": f"x{i}", "hint": "h"} for i in range(MAX_AXIS_VALUES)),
            "needs",
        ),
        (lambda raw: raw["axes"]["length"][1].update(id="length0"), "duplicate"),
        (lambda raw: raw["axes"]["length"][0].update(hint=" "), "'hint'"),
        (lambda raw: raw.pop("title"), "'title'"),
    ],
)
def test_broken_data_fails_with_a_clear_error(change, message):
    with pytest.raises(KindDataError, match=message):
        parse_kind("test", broken(change))
