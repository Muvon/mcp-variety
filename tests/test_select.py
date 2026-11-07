import math

import pytest

from mcp_variety.kinds import load_kinds
from mcp_variety.select import AvoidError, choose

WINDOW = 12
PICKS = 300
KINDS = load_kinds()


def simulate(kind, count, window=WINDOW, avoid=()):
    recent = []
    picks = []
    for _ in range(count):
        pick = choose(kind, recent, window, avoid)
        recent.append(pick.record())
        picks.append(pick)
    return picks


def tuple_of(pick):
    return (pick.approach.id, *(value.id for value in pick.form.values()))


@pytest.mark.parametrize("kind_id", sorted(KINDS))
def test_no_tuple_repeats_inside_the_window(kind_id):
    tuples = [tuple_of(pick) for pick in simulate(KINDS[kind_id], PICKS)]
    for index, current in enumerate(tuples):
        assert current not in tuples[max(0, index - WINDOW) : index]


@pytest.mark.parametrize("kind_id", sorted(KINDS))
def test_approaches_rotate_before_any_repeats(kind_id):
    kind = KINDS[kind_id]
    ids = [pick.approach.id for pick in simulate(kind, PICKS)]
    size = len(kind.approaches)
    for start in range(len(ids) - size + 1):
        assert len(set(ids[start : start + size])) == size


@pytest.mark.parametrize("kind_id", sorted(KINDS))
def test_every_approach_and_axis_value_gets_used(kind_id):
    kind = KINDS[kind_id]
    picks = simulate(kind, PICKS)
    assert {pick.approach.id for pick in picks} == {approach.id for approach in kind.approaches}
    for axis, values in kind.axes.items():
        assert {pick.form[axis].id for pick in picks} == {value.id for value in values}


def test_script_picks_include_a_hook():
    pick = choose(KINDS["script"], [], WINDOW)
    assert list(pick.form) == ["hook", "opener", "length", "ending"]


def test_avoid_is_honoured():
    kind = KINDS["post"]
    avoided = ["story", "hot-take", "listicle"]
    picks = simulate(kind, PICKS, avoid=avoided)
    assert not {pick.approach.id for pick in picks} & set(avoided)


def test_avoid_keeps_the_tuple_rule():
    kind = KINDS["post"]
    only = [approach.id for approach in kind.approaches[1:]]
    tuples = [tuple_of(pick) for pick in simulate(kind, PICKS, avoid=only)]
    for index, current in enumerate(tuples):
        assert current not in tuples[max(0, index - WINDOW) : index]


def test_unknown_avoid_id_lists_valid_ids():
    with pytest.raises(AvoidError, match=r"unknown approach ids \['nope'\].*valid ids: \['story'"):
        choose(KINDS["post"], [], WINDOW, ["nope"])


def test_avoiding_everything_is_an_error():
    every_id = [approach.id for approach in KINDS["post"].approaches]
    with pytest.raises(AvoidError, match="excludes every approach"):
        choose(KINDS["post"], [], WINDOW, every_id)


def test_tiny_tuple_space_still_returns_a_pick():
    # A window larger than the whole tuple space cannot satisfy the no-repeat rule, but must not crash.
    kind = KINDS["post"]
    space = len(kind.approaches) * math.prod(len(values) for values in kind.axes.values())
    assert len(simulate(kind, space + 5, window=space * 2)) == space + 5


def test_records_from_another_version_never_match():
    kind = KINDS["post"]
    stale = [{"approach": "story", "form": {"opener": "number"}}]
    assert choose(kind, stale, WINDOW).approach.id in {approach.id for approach in kind.approaches}
