import json
import threading

import pytest

from mcp_variety.history import DEFAULT_WINDOW, ConfigError, History, HistoryError, state_file, window_from_env

PICK = {"approach": "story", "form": {"opener": "number"}}


def test_picks_persist_across_instances(tmp_path):
    path = tmp_path / "history.json"
    History(path, 12).record_pick("acme", "post", PICK, keep=12)
    assert History(path, 12).recent_picks("acme", "post") == [PICK]


def test_scopes_and_kinds_are_separate(history):
    history.record_pick("acme", "post", PICK, keep=12)
    assert history.recent_picks("other", "post") == []
    assert history.recent_picks("acme", "reply") == []


def test_scope_ignores_case_and_surrounding_spaces(history):
    history.record_pick(" Acme ", "post", PICK, keep=12)
    assert history.recent_picks("acme", "post") == [PICK]


def test_empty_scope_is_rejected(history):
    with pytest.raises(ValueError, match="scope"):
        history.recent_picks("  ", "post")


def test_only_the_last_picks_are_kept(history):
    for index in range(10):
        history.record_pick("acme", "post", {"approach": f"a{index}", "form": {}}, keep=4)
    assert [pick["approach"] for pick in history.recent_picks("acme", "post")] == ["a6", "a7", "a8", "a9"]


def test_writes_leave_no_temp_files(history):
    history.record_pick("acme", "post", PICK, keep=12)
    assert [item.name for item in history.path.parent.iterdir()] == ["history.json"]


def test_concurrent_writers_lose_nothing(history):
    threads_count, per_thread = 8, 10

    def work(worker):
        for index in range(per_thread):
            history.record_pick("acme", "post", {"approach": f"w{worker}-{index}", "form": {}}, keep=1000)

    threads = [threading.Thread(target=work, args=(worker,)) for worker in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(history.recent_picks("acme", "post")) == threads_count * per_thread
    assert json.loads(history.path.read_text())["scopes"]["acme"]


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        "",
        "[]",
        '{"scopes": []}',
        '{"scopes": {"a": {"picks": {}}}}',
        '{"scopes": {"a": {"picks": {"post": [1]}, "openings": []}}}',
    ],
)
def test_corrupt_file_raises_and_is_not_overwritten(history, content):
    history.path.parent.mkdir(parents=True)
    history.path.write_text(content)
    with pytest.raises(HistoryError, match="corrupt"):
        history.recent_picks("acme", "post")
    with pytest.raises(HistoryError):
        history.record_pick("acme", "post", PICK, keep=12)
    assert history.path.read_text() == content


def test_opening_flags_a_different_text_only(history):
    assert history.register_opening("acme", "last week i", "hash-a") is False
    assert history.register_opening("acme", "last week i", "hash-a") is False
    assert history.register_opening("acme", "last week i", "hash-b") is True
    assert history.register_opening("other", "last week i", "hash-c") is False


def test_only_the_last_openings_are_kept(tmp_path):
    history = History(tmp_path / "history.json", 3)
    for index in range(5):
        history.register_opening("acme", f"opening {index}", f"hash-{index}")
    assert history.register_opening("acme", "opening 0", "hash-new") is False
    assert history.register_opening("acme", "opening 4", "hash-new-2") is True


def test_state_file_uses_the_override(monkeypatch, tmp_path):
    monkeypatch.setenv("VARIETY_MCP_STATE_DIR", str(tmp_path))
    assert state_file() == tmp_path / "history.json"


def test_state_file_defaults_to_xdg_state_home(monkeypatch, tmp_path):
    monkeypatch.delenv("VARIETY_MCP_STATE_DIR", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert state_file() == tmp_path / "mcp-variety" / "history.json"


def test_window_defaults_and_reads_the_environment(monkeypatch):
    monkeypatch.delenv("VARIETY_MCP_WINDOW", raising=False)
    assert window_from_env() == DEFAULT_WINDOW
    monkeypatch.setenv("VARIETY_MCP_WINDOW", "20")
    assert window_from_env() == 20


@pytest.mark.parametrize("value", ["0", "-3", "many", ""])
def test_bad_window_is_a_clear_error(monkeypatch, value):
    monkeypatch.setenv("VARIETY_MCP_WINDOW", value)
    with pytest.raises(ConfigError, match="VARIETY_MCP_WINDOW"):
        window_from_env()
