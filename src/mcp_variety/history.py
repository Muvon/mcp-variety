"""Per-scope history of recent picks and recent openings, kept in one JSON file."""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, TypedDict

DEFAULT_WINDOW = 12
STATE_DIR_ENV = "VARIETY_MCP_STATE_DIR"
WINDOW_ENV = "VARIETY_MCP_WINDOW"
APP_DIR = "mcp-variety"
HISTORY_FILE = "history.json"


class ConfigError(ValueError):
    """An environment variable holds an unusable value."""


class HistoryError(RuntimeError):
    """The history file exists but cannot be read."""


class PickRecord(TypedDict):
    approach: str
    form: dict[str, str]


class OpeningRecord(TypedDict):
    words: str
    text_hash: str


def state_file() -> Path:
    override = os.environ.get(STATE_DIR_ENV)
    if override:
        return Path(override).expanduser() / HISTORY_FILE
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / APP_DIR / HISTORY_FILE


def window_from_env() -> int:
    raw = os.environ.get(WINDOW_ENV)
    if raw is None:
        return DEFAULT_WINDOW
    try:
        window = int(raw)
    except ValueError:
        window = 0
    if window < 1:
        raise ConfigError(f"{WINDOW_ENV} must be a whole number of at least 1, got '{raw}'")
    return window


def _scope_key(scope: str) -> str:
    # Case and surrounding spaces are not part of an account name, so "Acme " and "acme" share one history.
    key = scope.strip().casefold()
    if not key:
        raise ValueError("scope must not be empty")
    return key


def _is_pick(item: Any) -> bool:
    return isinstance(item, dict) and isinstance(item.get("approach"), str) and isinstance(item.get("form"), dict)


def _is_opening(item: Any) -> bool:
    return isinstance(item, dict) and isinstance(item.get("words"), str) and isinstance(item.get("text_hash"), str)


def _validate(data: Any) -> None:
    scopes = data.get("scopes") if isinstance(data, dict) else None
    if not isinstance(scopes, dict):
        raise ValueError("missing 'scopes' object")
    for name, entry in scopes.items():
        if not (
            isinstance(entry, dict) and isinstance(entry.get("picks"), dict) and isinstance(entry.get("openings"), list)
        ):
            raise ValueError(f"scope '{name}' has the wrong shape")
        for kind, picks in entry["picks"].items():
            if not (isinstance(picks, list) and all(_is_pick(pick) for pick in picks)):
                raise ValueError(f"picks of kind '{kind}' in scope '{name}' have the wrong shape")
        if not all(_is_opening(opening) for opening in entry["openings"]):
            raise ValueError(f"openings in scope '{name}' have the wrong shape")


def _entry(data: dict[str, Any], key: str) -> dict[str, Any]:
    return data["scopes"].setdefault(key, {"picks": {}, "openings": []})


class History:
    """Every call reads the file, changes it and replaces it atomically, so a reader never sees a half-written file.

    The lock serializes calls inside one process. Two processes writing at the same moment can still lose one update.
    """

    def __init__(self, path: Path, window: int) -> None:
        self.path = path
        self.window = window
        self._lock = threading.RLock()

    def recent_picks(self, scope: str, kind: str) -> list[PickRecord]:
        key = _scope_key(scope)
        with self._lock:
            entry = self._read()["scopes"].get(key)
        return list(entry["picks"].get(kind, [])) if entry else []

    def record_pick(self, scope: str, kind: str, record: PickRecord, keep: int) -> None:
        key = _scope_key(scope)
        with self._lock:
            data = self._read()
            picks = _entry(data, key)["picks"].setdefault(kind, [])
            picks.append(record)
            del picks[:-keep]
            self._write(data)

    def register_opening(self, scope: str, words: str, text_hash: str) -> bool:
        """Return True when a different text in this scope already has these opening words, then remember this one.

        The hash lets the same text be checked twice without flagging itself.
        """
        key = _scope_key(scope)
        with self._lock:
            data = self._read()
            openings = _entry(data, key)["openings"]
            repeated = any(item["words"] == words and item["text_hash"] != text_hash for item in openings)
            if not any(item["text_hash"] == text_hash for item in openings):
                openings.append({"words": words, "text_hash": text_hash})
                del openings[: -self.window]
                self._write(data)
        return repeated

    def _read(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"scopes": {}}
        try:
            data = json.loads(raw)
            _validate(data)
        except ValueError as error:
            raise HistoryError(
                f"history file {self.path} is corrupt ({error}). Fix or delete it; mcp-variety does not overwrite it."
            ) from error
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(dir=self.path.parent, prefix=".history-", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
            os.replace(temp_name, self.path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
