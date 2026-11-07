"""Deterministic checker for common signs of AI-written text."""

import hashlib
import re
from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Any

from variety_mcp.history import History
from variety_mcp.rules import (
    CONTRAST,
    EM_DASH,
    EXCLAMATIONS,
    MAX_EXCLAMATIONS,
    OPENING_WORDS,
    REPEATED_OPENING,
    STOCK_PHRASE,
    STOCK_PHRASES,
    UNIFORM_SENTENCES,
    Rule,
)

EXCERPT_CONTEXT = 25
MIN_SENTENCES_FOR_RHYTHM = 5
# Human prose varies a lot from sentence to sentence; a spread this narrow reads as machine-even.
UNIFORM_VARIATION_LIMIT = 0.25
CONTRAST_SPAN = 80

# Built from code points so the source file itself stays free of the characters it hunts for.
EM_DASH_CHAR = chr(0x2014)
EN_DASH_CHAR = chr(0x2013)
CURLY_APOSTROPHE = chr(0x2019)
DASH_PATTERN = re.compile(f"{EM_DASH_CHAR}|(?<=\\s){EN_DASH_CHAR}(?=\\s)")
STOCK_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(phrase) for phrase in sorted(STOCK_PHRASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
CONTRAST_PATTERNS = (
    # "not just X, but Y", "not only X but also Y"
    re.compile(rf"\bnot (?:just|only|merely)\b[^.!?\n]{{1,{CONTRAST_SPAN}}}?[,;]?\s+but\b", re.IGNORECASE),
    # "it's not X, it's Y", "this isn't X. It's Y"
    re.compile(
        rf"\b(?:it|this|that)(?:'s not| is not| isn't)\b[^.!?\n]{{1,{CONTRAST_SPAN}}}?"
        r"[,;.]\s*(?:it|this|that)(?:'s| is)\b",
        re.IGNORECASE,
    ),
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
WORD = re.compile(r"[\w']+")


@dataclass(frozen=True)
class Issue:
    rule: str
    excerpt: str
    advice: str


def _issue(rule: Rule, excerpt: str) -> Issue:
    return Issue(rule.id, excerpt, rule.instruction)


def _around(text: str, match: re.Match[str]) -> str:
    snippet = text[max(0, match.start() - EXCERPT_CONTEXT) : match.end() + EXCERPT_CONTEXT]
    return " ".join(snippet.split())


def _dash_issues(text: str) -> list[Issue]:
    return [_issue(EM_DASH, _around(text, match)) for match in DASH_PATTERN.finditer(text)]


def _stock_phrase_issues(text: str) -> list[Issue]:
    return [_issue(STOCK_PHRASE, _around(text, match)) for match in STOCK_PATTERN.finditer(text)]


def _contrast_issues(text: str) -> list[Issue]:
    return [_issue(CONTRAST, _around(text, match)) for pattern in CONTRAST_PATTERNS for match in pattern.finditer(text)]


def _uniform_sentence_issues(text: str) -> list[Issue]:
    lengths = [len(sentence.split()) for sentence in SENTENCE_BREAK.split(text.strip()) if sentence.strip()]
    if len(lengths) < MIN_SENTENCES_FOR_RHYTHM:
        return []
    if pstdev(lengths) / mean(lengths) >= UNIFORM_VARIATION_LIMIT:
        return []
    summary = f"{len(lengths)} sentences of {min(lengths)} to {max(lengths)} words"
    return [_issue(UNIFORM_SENTENCES, summary)]


def _exclamation_issues(text: str) -> list[Issue]:
    marks = [match for match in re.finditer("!", text)]
    if len(marks) <= MAX_EXCLAMATIONS:
        return []
    return [_issue(EXCLAMATIONS, _around(text, marks[MAX_EXCLAMATIONS]))]


def _opening_issues(text: str, history: History, scope: str) -> list[Issue]:
    words = WORD.findall(text.lower())[:OPENING_WORDS]
    if len(words) < OPENING_WORDS:
        return []
    opening = " ".join(words)
    text_hash = hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()
    return [_issue(REPEATED_OPENING, opening)] if history.register_opening(scope, opening, text_hash) else []


def check_text(text: str, history: History, scope: str | None = None) -> dict[str, Any]:
    normalized = text.replace(CURLY_APOSTROPHE, "'")
    issues = [
        *_dash_issues(normalized),
        *_stock_phrase_issues(normalized),
        *_contrast_issues(normalized),
        *_uniform_sentence_issues(normalized),
        *_exclamation_issues(normalized),
    ]
    if scope is not None:
        issues.extend(_opening_issues(normalized, history, scope))
    return {"issues": [asdict(issue) for issue in issues], "ok": not issues}
