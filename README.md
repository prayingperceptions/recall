[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# recall — Memory in a file.

Local-first agent memory. No server, no API key, no vector DB — a file you can read.

## The pain

Every agent framework reinvents memory badly. Hosted memory APIs are complex
and overkill for "just remember what the user told me last Tuesday." And
agents forget *everything* between runs.

## The fix

A Markdown file. You open it, you read it, you hand-edit it. `recall` gives it
decent retrieval scoring (keyword overlap + salience + recency decay) with
zero dependencies.

## Quickstart

```bash
pip install -e .
```

```python
from recall import Memory

mem = Memory("memory.md")
mem.remember("User deploys to Vercel on the hobby plan.", salience=0.7, tags=["deploy"])
mem.remember("x402 price is $0.005 per call.", salience=0.9, tags=["x402", "pricing"])

for hit in mem.recall("what does the API cost"):
    print(hit["score"], hit["text"])
```

## On-disk format (the spec)

Each entry is a `##` header line followed by free text, with a blank line
between entries:

```
## 2026-10-05 09:14:02 | salience=0.8 | tags: x402, pricing
The x402 micropayment price is $0.005 per call (~6 sats at $86k BTC).

## 2026-10-05 09:20:11 | salience=0.3
The user's dog is named Biscuit.
```

- Timestamp: `YYYY-MM-DD HH:MM:SS` (local time).
- `salience`: float in `[0, 1]` (clamped on write). Optional — defaults to 0.5.
- `tags`: comma-separated, optional.
- Text may span multiple lines; it ends at the next `##` header.

**Hand-editing is safe.** The parser is deliberately lenient: any line that
doesn't parse as an entry header is skipped silently. Timestamps that don't
parse, missing salience, missing tags — recall never crashes on a messy file.

## Scoring

`score = 0.5 * keyword_overlap + 0.3 * salience + 0.2 * recency`

- **keyword_overlap**: fraction of query words (lowercased, length > 2, tiny
  stopword set removed) that appear in the entry's text + tags.
- **salience**: the `0–1` value you pass to `remember()`.
- **recency**: exponential decay with a ~7-day half-life —
  `0.5 ** (age_days / half_life_days)`. Tune via `Memory(path, half_life_days=30)`.

The file is re-read on every `recall()` call, so external edits are always
picked up immediately.

## Jaw-drop demo

```bash
python examples/agent_loop.py
```

An agent loop that `remember()`s each observation and `recall()`s relevant
context before acting — ~20 lines, prints exactly what it recalls.

## License

MIT. See [LICENSE](LICENSE).
