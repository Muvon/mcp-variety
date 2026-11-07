"""Pick an approach and a form at random while avoiding recent repeats."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from variety_mcp.history import PickRecord
from variety_mcp.kinds import AXIS_ORDER, Approach, AxisValue, Kind

# Picks must not be predictable, so draw from the operating system instead of a seeded generator.
SYSTEM_RANDOM = random.SystemRandom()


class AvoidError(ValueError):
    """The avoid list names an unknown approach or excludes every approach."""


@dataclass(frozen=True)
class Pick:
    approach: Approach
    form: dict[str, AxisValue]

    def record(self) -> PickRecord:
        return {"approach": self.approach.id, "form": {axis: value.id for axis, value in self.form.items()}}


def choose(
    kind: Kind,
    recent: Sequence[PickRecord],
    window: int,
    avoid: Sequence[str] = (),
    rng: random.Random = SYSTEM_RANDOM,
) -> Pick:
    """Pick uniformly among allowed approaches not used lately, and among forms not used lately with that approach.

    `recent` lists earlier picks of this kind in this scope, oldest first.
    """
    valid_ids = [approach.id for approach in kind.approaches]
    unknown = sorted(set(avoid) - set(valid_ids))
    if unknown:
        raise AvoidError(f"unknown approach ids {unknown} for kind '{kind.id}'; valid ids: {valid_ids}")
    allowed = [approach for approach in kind.approaches if approach.id not in avoid]
    if not allowed:
        raise AvoidError(f"avoid excludes every approach of kind '{kind.id}'; valid ids: {valid_ids}")

    rotation = len(kind.approaches) - 1
    recently_used = {record["approach"] for record in recent[-rotation:]}
    fresh = [approach for approach in allowed if approach.id not in recently_used] or allowed

    axis_names = [name for name in AXIS_ORDER if name in kind.axes]
    combos = list(product(*(kind.axes[name] for name in axis_names)))
    # A record with a missing axis (written by another version) gets a None slot and never matches.
    used = {(record["approach"], tuple(record["form"].get(name) for name in axis_names)) for record in recent[-window:]}

    for pool in (fresh, allowed):
        for approach in rng.sample(pool, len(pool)):
            unused = [combo for combo in combos if (approach.id, tuple(value.id for value in combo)) not in used]
            if unused:
                return Pick(approach, dict(zip(axis_names, rng.choice(unused), strict=True)))
    # Every tuple of every allowed approach was used inside the window (only possible with a window
    # larger than the tuple space), so the no-repeat rule cannot hold any more.
    return Pick(rng.choice(allowed), dict(zip(axis_names, rng.choice(combos), strict=True)))
