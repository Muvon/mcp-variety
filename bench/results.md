# Baseline benchmark

Date: 2026-11-07. Model: Claude Sonnet (`claude -p --model sonnet`, no tools).
Samples: 8 inputs (post and reply, 4 each) x 2 conditions x 6 texts = 96 texts.

Without: the prompt is `Write a <kind> about: <input>`. With: the same prompt, prefixed with the `protocol` from a real `variety_pick` call (one scope per input, fresh state folder).

## Mean over all inputs

| Measure | Without mcp-variety | With mcp-variety |
|---|---|---|
| Same opening (share of text pairs with the same first 3 words) | 58.3% | 2.5% |
| Shared 3-word phrases (share of a text's phrases found in another text) | 46.7% | 7.4% |
| `variety_check` issues per text | 0.10 | 0.04 |

## Per input

| Input | Same opening without | Same opening with | Shared phrases without | Shared phrases with | Issues without | Issues with |
|---|---|---|---|---|---|---|
| post-offline-mode | 40.0% | 6.7% | 22.0% | 5.4% | 0.17 | 0.00 |
| post-bakery | 6.7% | 0.0% | 33.9% | 7.5% | 0.00 | 0.17 |
| post-rebrand | 100.0% | 0.0% | 29.7% | 4.9% | 0.17 | 0.00 |
| post-log-tool | 40.0% | 0.0% | 38.6% | 3.4% | 0.00 | 0.00 |
| reply-logout-bug | 100.0% | 0.0% | 81.2% | 6.1% | 0.17 | 0.00 |
| reply-price-rise | 40.0% | 0.0% | 45.9% | 15.1% | 0.00 | 0.00 |
| reply-currencies | 100.0% | 6.7% | 73.8% | 14.3% | 0.33 | 0.17 |
| reply-remote-juniors | 40.0% | 6.7% | 48.6% | 2.3% | 0.00 | 0.00 |

## How the numbers are computed

- Same opening: all 15 pairs of texts for one input; a pair counts when the first 3 words match after lowercasing and removing punctuation.
- Shared phrases: for each text, the share of its 3-word phrases that also appear in at least one other text of the same input. Phrases that appear in the input itself are left out.
- Issues: the number of problems `variety_check` reports for a text, without a scope.
- Each measure is computed per input, then averaged over the inputs.

## Reproduce

```sh
uv sync
uv run python bench/run.py
```

Texts are cached in `bench/out/outputs.json` (git-ignored). Delete `bench/out/` to generate them again.
