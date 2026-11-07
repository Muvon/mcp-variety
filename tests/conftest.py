import pytest

from variety_mcp.history import History

TEST_WINDOW = 12


@pytest.fixture
def history(tmp_path):
    return History(tmp_path / "state" / "history.json", TEST_WINDOW)
