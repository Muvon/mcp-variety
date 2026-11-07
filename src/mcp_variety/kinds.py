"""Load and validate the built-in writing patterns (one TOML file per kind)."""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any

REQUIRED_AXES = ("opener", "length", "ending")
# Order in which axes appear in the protocol. The hook, when a kind has one, comes first.
AXIS_ORDER = ("hook", "opener", "length", "ending")
MIN_APPROACHES = 10
MIN_AXIS_VALUES = 4
MAX_AXIS_VALUES = 6
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# The form (opening, length, ending) is drawn separately from the approach, so an approach text that
# talks about any of them would clash with some axis value.
FORM_WORDS = re.compile(
    r"\b(open(?:s|ing)?|start(?:s|ing)?|begin(?:s|ning)?|end(?:s|ing)?|finish(?:es)?|conclude[sd]?|closing"
    r"|short|long|brief|words?|sentences?|paragraphs?|seconds?)\b",
    re.IGNORECASE,
)


class KindDataError(ValueError):
    """A kind file breaks the data rules."""


@dataclass(frozen=True)
class Approach:
    id: str
    name: str
    how: str


@dataclass(frozen=True)
class AxisValue:
    id: str
    hint: str


@dataclass(frozen=True)
class Kind:
    id: str
    title: str
    description: str
    approaches: tuple[Approach, ...]
    axes: Mapping[str, tuple[AxisValue, ...]]


def _text(table: Mapping[str, Any], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KindDataError(f"{where}: '{key}' must be a non-empty string")
    return value.strip()


def _tables(raw: Any, key: str, where: str) -> list[Mapping[str, Any]]:
    items = raw.get(key) if isinstance(raw, Mapping) else None
    if not isinstance(items, list) or not all(isinstance(item, Mapping) for item in items):
        raise KindDataError(f"{where}: '{key}' must be a list of tables")
    return items


def _identifier(table: Mapping[str, Any], where: str) -> str:
    value = _text(table, "id", where)
    if not ID_PATTERN.match(value):
        raise KindDataError(
            f"{where}: id '{value}' must be lowercase letters, digits and hyphens, starting with a letter or digit"
        )
    return value


def _require_unique(ids: list[str], where: str) -> None:
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise KindDataError(f"{where}: duplicate ids {duplicates}")


def _parse_approach(table: Mapping[str, Any], where: str) -> Approach:
    approach = Approach(
        id=_identifier(table, where),
        name=_text(table, "name", where),
        how=_text(table, "how", where),
    )
    form_word = FORM_WORDS.search(approach.how)
    if form_word:
        raise KindDataError(
            f"{where}: approach '{approach.id}' text mentions '{form_word.group(0)}'; "
            "opening, length and ending belong to the axes"
        )
    return approach


def _parse_axis(values: list[Mapping[str, Any]], where: str) -> tuple[AxisValue, ...]:
    if not MIN_AXIS_VALUES <= len(values) <= MAX_AXIS_VALUES:
        raise KindDataError(f"{where}: needs {MIN_AXIS_VALUES} to {MAX_AXIS_VALUES} values, found {len(values)}")
    parsed = tuple(AxisValue(id=_identifier(value, where), hint=_text(value, "hint", where)) for value in values)
    _require_unique([value.id for value in parsed], where)
    return parsed


def parse_kind(kind_id: str, raw: Mapping[str, Any]) -> Kind:
    where = f"kind '{kind_id}'"
    approach_tables = _tables(raw, "approaches", where)
    approaches = tuple(_parse_approach(table, f"{where} approach") for table in approach_tables)
    if len(approaches) < MIN_APPROACHES:
        raise KindDataError(f"{where}: needs at least {MIN_APPROACHES} approaches, found {len(approaches)}")
    _require_unique([approach.id for approach in approaches], f"{where} approaches")

    raw_axes = raw.get("axes")
    if not isinstance(raw_axes, Mapping):
        raise KindDataError(f"{where}: 'axes' must be a table")
    unknown = sorted(set(raw_axes) - set(AXIS_ORDER))
    if unknown:
        raise KindDataError(f"{where}: unknown axes {unknown}")
    missing = [name for name in REQUIRED_AXES if name not in raw_axes]
    if missing:
        raise KindDataError(f"{where}: missing axes {missing}")
    axes = {
        name: _parse_axis(_tables(raw_axes, name, where), f"{where} axis '{name}'")
        for name in AXIS_ORDER
        if name in raw_axes
    }
    return Kind(
        id=kind_id,
        title=_text(raw, "title", where),
        description=_text(raw, "description", where),
        approaches=approaches,
        axes=axes,
    )


def load_kinds() -> dict[str, Kind]:
    directory = resources.files("mcp_variety") / "kinds"
    kinds: dict[str, Kind] = {}
    for entry in sorted(directory.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".toml"):
            continue
        kind_id = entry.name.removesuffix(".toml")
        try:
            raw = tomllib.loads(entry.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise KindDataError(f"kind '{kind_id}': invalid TOML: {error}") from error
        kinds[kind_id] = parse_kind(kind_id, raw)
    if not kinds:
        raise KindDataError("no kind files found in the package")
    return kinds
