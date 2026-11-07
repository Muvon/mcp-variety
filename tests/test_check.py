import pytest

from variety_mcp.check import check_text
from variety_mcp.rules import STOCK_PHRASES

CLEAN = (
    "I burned two hours on a bug that turned out to be a typo. The config key said 'timout'. Not 'timeout'. "
    "Spelling, again. After that I added a check to the build that greps for the three misspellings we make most "
    "often. It has caught two since, both in pull requests from people who were sure they had typed it correctly. "
    "Worth ten minutes if your team writes a lot of config."
)
EVEN = (
    "We shipped the build. It passed all tests. The team was happy. Nobody found bugs. "
    "We went home early. Next week looks calm."
)
# Built from code points so the repo holds no em dash, not even in tests.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
CURLY_APOSTROPHE = chr(0x2019)


def rules(history, text, scope=None):
    return {issue["rule"] for issue in check_text(text, history, scope)["issues"]}


def test_clean_paragraph_passes(history):
    result = check_text(CLEAN, history)
    assert result == {"issues": [], "ok": True}


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (f"The plan works {EM_DASH} mostly.", "em_dash"),
        (f"The plan works {EN_DASH} mostly.", "em_dash"),
        ("Here's the thing about pricing.", "stock_phrase"),
        (f"Here{CURLY_APOSTROPHE}s the thing about pricing.", "stock_phrase"),
        ("Let's dive in and look at it.", "stock_phrase"),
        ("This is a real GAME-CHANGER for us.", "stock_phrase"),
        ("We delve into the logs every day.", "stock_phrase"),
        ("This is not just a tool, but a habit.", "contrast"),
        ("It's not a tool, it's a mindset.", "contrast"),
        ("It isn't about speed. It's about trust.", "contrast"),
        (EVEN, "uniform_sentences"),
        ("Great news! We shipped it! Try it today.", "exclamations"),
    ],
)
def test_each_rule_fires_on_a_positive_example(history, text, rule):
    assert rule in rules(history, text)


def test_issues_carry_excerpt_and_advice(history):
    issue = check_text(f"The plan works {EM_DASH} mostly, and we know it.", history)["issues"][0]
    assert "works" in issue["excerpt"]
    assert issue["advice"]
    assert check_text(f"The plan works {EM_DASH} mostly.", history)["ok"] is False


def test_hyphen_and_unspaced_en_dash_are_fine(history):
    assert rules(history, f"Pages 3{EN_DASH}5 cover the well-known setup.") == set()


def test_one_exclamation_mark_is_fine(history):
    assert "exclamations" not in rules(history, "We shipped it! Try it today.")


def test_few_sentences_are_never_uniform(history):
    assert "uniform_sentences" not in rules(history, "We shipped the build. It passed all tests. The team was happy.")


def test_a_stock_word_inside_another_word_is_fine(history):
    assert rules(history, "The delveloper docs are fine.") == set()


def test_stock_phrase_list_is_lowercase_and_unique():
    assert all(phrase == phrase.lower() for phrase in STOCK_PHRASES)
    assert len(set(STOCK_PHRASES)) == len(STOCK_PHRASES)
    assert len(STOCK_PHRASES) >= 60


def test_opening_repeat_flags_a_different_text(history):
    first = "Last week I shipped a thing nobody asked for."
    second = "Last week, I broke the build twice."
    assert "repeated_opening" not in rules(history, first, "acme")
    assert "repeated_opening" in rules(history, second, "acme")


def test_rechecking_the_same_text_does_not_flag_itself(history):
    text = "Last week I shipped a thing nobody asked for."
    assert "repeated_opening" not in rules(history, text, "acme")
    assert "repeated_opening" not in rules(history, text, "acme")


def test_opening_repeat_is_per_scope_and_needs_a_scope(history):
    text = "Last week I shipped a thing nobody asked for."
    other = "Last week I broke the build twice."
    rules(history, text, "acme")
    assert "repeated_opening" not in rules(history, other, "beta")
    assert "repeated_opening" not in rules(history, other)


def test_texts_with_fewer_words_than_an_opening_are_skipped(history):
    assert rules(history, "Done.", "acme") == set()
    assert rules(history, "Done.", "acme") == set()
