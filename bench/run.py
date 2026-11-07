"""Baseline benchmark: does a mcp-variety protocol make repeated texts less alike?

For each input it writes TEXTS_PER_CONDITION texts with a plain prompt and TEXTS_PER_CONDITION texts whose prompt
starts with a protocol from a real `variety_pick` call, then compares how alike the texts are.

Run: uv run python bench/run.py
Needs the `claude` CLI. Generated texts are cached in bench/out/outputs.json, so a rerun only fills gaps.
Delete bench/out/ to start over. This folder is for development and is not part of the wheel.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from pathlib import Path
from statistics import mean

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_variety.check import CURLY_APOSTROPHE, check_text
from mcp_variety.history import DEFAULT_WINDOW, STATE_DIR_ENV, History

BENCH_DIR = Path(__file__).parent
INPUTS_FILE = BENCH_DIR / "inputs.toml"
OUT_DIR = BENCH_DIR / "out"
CACHE_FILE = OUT_DIR / "outputs.json"
STATE_DIR = OUT_DIR / "state"
RESULTS_FILE = BENCH_DIR / "results.md"

MODEL = "sonnet"
TEXTS_PER_CONDITION = 6
PARALLEL_GENERATIONS = 6
GENERATION_TIMEOUT_SECONDS = 300
CONDITIONS = ("plain", "protocol")
WORDS_IN_OPENING = 3
WORDS_IN_PHRASE = 3
# Replaces Claude Code's own system prompt so the run sees only the task, with no coding-agent instructions.
SYSTEM_PROMPT = "You write text on request. Reply with the text itself and nothing else."
WORD = re.compile(r"[\w']+")


@dataclass(frozen=True)
class Input:
    id: str
    kind: str
    text: str


def load_inputs() -> list[Input]:
    raw = tomllib.loads(INPUTS_FILE.read_text(encoding="utf-8"))
    return [Input(**item) for item in raw["inputs"]]


def load_cache() -> dict[str, dict[str, str]]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    # The pick history must match the cached protocols, so it is only kept while the cache exists.
    shutil.rmtree(STATE_DIR, ignore_errors=True)
    return {"protocols": {}, "texts": {}}


def save_cache(cache: dict[str, dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    temp = CACHE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, CACHE_FILE)


def sample_key(item: Input, condition: str, index: int) -> str:
    return f"{item.id}/{condition}/{index}"


def task_prompt(item: Input) -> str:
    return f"Write a {item.kind} about: {item.text}\n\nReturn only the text of the {item.kind}, with no introduction."


async def fetch_missing_protocols(inputs: list[Input], cache: dict[str, dict[str, str]]) -> None:
    """Call variety_pick through the real server, one scope per input, so no combination repeats inside an input."""
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_variety"], env={STATE_DIR_ENV: str(STATE_DIR)}
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for item in inputs:
            for index in range(TEXTS_PER_CONDITION):
                key = sample_key(item, "protocol", index)
                if key in cache["protocols"]:
                    continue
                result = await session.call_tool("variety_pick", {"kind": item.kind, "scope": item.id})
                if result.isError:
                    raise RuntimeError(f"variety_pick failed for {item.id}: {result.content}")
                cache["protocols"][key] = json.loads(result.content[0].text)["protocol"]
                save_cache(cache)


def generate(prompt: str) -> str:
    # An empty folder and project-only settings keep CLAUDE.md files, hooks and skills out of the run.
    with tempfile.TemporaryDirectory() as workdir:
        done = subprocess.run(
            [
                "claude",
                "-p",
                "--model",
                MODEL,
                "--tools",
                "",
                "--setting-sources",
                "project",
                "--disable-slash-commands",
                "--strict-mcp-config",
                "--no-session-persistence",
                "--system-prompt",
                SYSTEM_PROMPT,
                prompt,
            ],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=GENERATION_TIMEOUT_SECONDS,
            check=False,
        )
    if done.returncode != 0 or not done.stdout.strip():
        raise RuntimeError(f"claude failed (exit {done.returncode}): {done.stderr.strip()}")
    return done.stdout.strip()


def fill_missing_texts(inputs: list[Input], cache: dict[str, dict[str, str]]) -> None:
    jobs: dict[str, str] = {}
    for item in inputs:
        for condition in CONDITIONS:
            for index in range(TEXTS_PER_CONDITION):
                key = sample_key(item, condition, index)
                if key in cache["texts"]:
                    continue
                prompt = task_prompt(item)
                if condition == "protocol":
                    prompt = f"{cache['protocols'][key]}\n\n{prompt}"
                jobs[key] = prompt
    print(f"{len(jobs)} generations to run, {len(inputs) * len(CONDITIONS) * TEXTS_PER_CONDITION - len(jobs)} cached")
    lock = threading.Lock()
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=PARALLEL_GENERATIONS) as pool:
        futures = {pool.submit(generate, prompt): key for key, prompt in jobs.items()}
        for done_count, future in enumerate(as_completed(futures), start=1):
            key = futures[future]
            try:
                text = future.result()
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                failures.append(f"{key}: {error}")
                continue
            with lock:
                cache["texts"][key] = text
                save_cache(cache)
            print(f"[{done_count}/{len(jobs)}] {key}")
    if failures:
        raise SystemExit("generation failed, rerun to fill the gaps:\n" + "\n".join(failures))


def words(text: str) -> list[str]:
    return WORD.findall(text.lower().replace(CURLY_APOSTROPHE, "'"))


def phrases(text: str) -> set[tuple[str, ...]]:
    tokens = words(text)
    return set(zip(*(tokens[offset:] for offset in range(WORDS_IN_PHRASE)), strict=False))


def same_opening_rate(texts: list[str]) -> float:
    openings = [tuple(words(text)[:WORDS_IN_OPENING]) for text in texts]
    return mean(first == second for first, second in combinations(openings, 2))


def shared_phrase_rate(texts: list[str], input_text: str) -> float:
    """Average share of a text's 3-word phrases that also occur in another text. Phrases from the input do not count."""
    from_input = phrases(input_text)
    own = [phrases(text) - from_input for text in texts]
    shares = []
    for index, mine in enumerate(own):
        others = set().union(*(theirs for other, theirs in enumerate(own) if other != index))
        shares.append(len(mine & others) / len(mine) if mine else 0.0)
    return mean(shares)


def issues_per_text(texts: list[str]) -> float:
    with tempfile.TemporaryDirectory() as folder:
        history = History(Path(folder) / "history.json", DEFAULT_WINDOW)
        return mean(len(check_text(text, history)["issues"]) for text in texts)


def measure(inputs: list[Input], cache: dict[str, dict[str, str]]) -> dict[str, dict[str, dict[str, float]]]:
    results: dict[str, dict[str, dict[str, float]]] = {}
    for item in inputs:
        results[item.id] = {}
        for condition in CONDITIONS:
            texts = [cache["texts"][sample_key(item, condition, index)] for index in range(TEXTS_PER_CONDITION)]
            results[item.id][condition] = {
                "opening": same_opening_rate(texts),
                "phrases": shared_phrase_rate(texts, item.text),
                "issues": issues_per_text(texts),
            }
    return results


def average(results: dict[str, dict[str, dict[str, float]]], condition: str, metric: str) -> float:
    return mean(per_condition[condition][metric] for per_condition in results.values())


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render(inputs: list[Input], results: dict[str, dict[str, dict[str, float]]]) -> str:
    total = len(inputs) * len(CONDITIONS) * TEXTS_PER_CONDITION
    lines = [
        "# Baseline benchmark",
        "",
        f"Date: {date.today().isoformat()}. Model: Claude Sonnet (`claude -p --model {MODEL}`, no tools).",
        f"Samples: {len(inputs)} inputs (post and reply, {len(inputs) // 2} each) x {len(CONDITIONS)} conditions x "
        f"{TEXTS_PER_CONDITION} texts = {total} texts.",
        "",
        "Without: the prompt is `Write a <kind> about: <input>`. With: the same prompt, prefixed with the `protocol` "
        "from a real `variety_pick` call (one scope per input, fresh state folder).",
        "",
        "## Mean over all inputs",
        "",
        "| Measure | Without mcp-variety | With mcp-variety |",
        "|---|---|---|",
        "| Same opening (share of text pairs with the same first 3 words) | "
        f"{percent(average(results, 'plain', 'opening'))} | {percent(average(results, 'protocol', 'opening'))} |",
        "| Shared 3-word phrases (share of a text's phrases found in another text) | "
        f"{percent(average(results, 'plain', 'phrases'))} | {percent(average(results, 'protocol', 'phrases'))} |",
        "| `variety_check` issues per text | "
        f"{average(results, 'plain', 'issues'):.2f} | {average(results, 'protocol', 'issues'):.2f} |",
        "",
        "## Per input",
        "",
        "| Input | Same opening without | Same opening with | Shared phrases without | Shared phrases with "
        "| Issues without | Issues with |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in inputs:
        plain, with_protocol = results[item.id]["plain"], results[item.id]["protocol"]
        lines.append(
            f"| {item.id} | {percent(plain['opening'])} | {percent(with_protocol['opening'])} "
            f"| {percent(plain['phrases'])} | {percent(with_protocol['phrases'])} "
            f"| {plain['issues']:.2f} | {with_protocol['issues']:.2f} |"
        )
    lines += [
        "",
        "## How the numbers are computed",
        "",
        f"- Same opening: all {TEXTS_PER_CONDITION * (TEXTS_PER_CONDITION - 1) // 2} pairs of texts for one input; a "
        f"pair counts when the first {WORDS_IN_OPENING} words match after lowercasing and removing punctuation.",
        f"- Shared phrases: for each text, the share of its {WORDS_IN_PHRASE}-word phrases that also appear in at "
        "least one other text of the same input. Phrases that appear in the input itself are left out.",
        "- Issues: the number of problems `variety_check` reports for a text, without a scope.",
        "- Each measure is computed per input, then averaged over the inputs.",
        "",
        "## Reproduce",
        "",
        "```sh",
        "uv sync",
        "uv run python bench/run.py",
        "```",
        "",
        "Texts are cached in `bench/out/outputs.json` (git-ignored). Delete `bench/out/` to generate them again.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    inputs = load_inputs()
    cache = load_cache()
    asyncio.run(fetch_missing_protocols(inputs, cache))
    fill_missing_texts(inputs, cache)
    results = measure(inputs, cache)
    report = render(inputs, results)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
