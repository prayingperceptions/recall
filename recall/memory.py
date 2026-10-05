"""Core of recall: a Markdown file as agent memory.

On-disk format (the spec — hand-edit freely, the parser is lenient):

    ## 2026-10-05 09:14:02 | salience=0.8 | tags: x402, pricing
    <the text, possibly multi-line>

    ## 2026-10-05 09:20:11 | salience=0.3
    <another entry, tags optional>

Blank line between entries. Anything that doesn't parse as an entry is
silently skipped on read — never crashes.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

HEADER_RE = re.compile(
    r"^##\s+(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
    r"(?:\s*\|\s*salience\s*=\s*(?P<salience>[-+]?\d*\.?\d+))?"
    r"(?:\s*\|\s*tags\s*:\s*(?P<tags>[^\n]*))?"
    r"\s*$"
)

STOPWORDS = frozenset(
    "a an the and or of to in on for is are was were be been it its this that "
    "with as at by from i you he she we they me him her us them my your our "
    "what when where which who how why do does did not no yes if then than "
    "so but into out up down about over after before between".split()
)


def _words(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z0-9]+", text.lower())
        if len(w) > 2 and w not in STOPWORDS
    }


class Memory:
    """Append-only memory backed by a single Markdown file."""

    def __init__(self, path: str | Path = "memory.md", half_life_days: float = 7.0):
        self.path = Path(path)
        self.half_life_days = half_life_days

    # ------------------------------------------------------------------ write

    def remember(self, text: str, salience: float = 0.5, tags: list[str] | None = None) -> None:
        """Append an entry. Salience is clamped to [0, 1]."""
        salience = max(0.0, min(1.0, float(salience)))
        tags = [t.strip() for t in (tags or []) if t and t.strip()]
        ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        header = f"## {ts} | salience={salience:g}"
        if tags:
            header += f" | tags: {', '.join(tags)}"
        block = header + "\n" + text.rstrip("\n") + "\n"
        exists = self.path.exists()
        with self.path.open("a", encoding="utf-8") as f:
            if exists and self.path.stat().st_size > 0:
                f.write("\n")  # blank line between entries
            f.write(block)

    # ------------------------------------------------------------------ read

    def _load(self) -> list[dict]:
        """Parse the file leniently: skip anything that isn't an entry."""
        if not self.path.exists():
            return []
        raw = self.path.read_text(encoding="utf-8", errors="replace")
        entries: list[dict] = []
        lines = raw.split("\n")
        i = 0
        while i < len(lines):
            m = HEADER_RE.match(lines[i])
            if not m:
                i += 1
                continue
            ts_str = m.group("ts")
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                i += 1
                continue
            try:
                salience = max(0.0, min(1.0, float(m.group("salience") or 0.5)))
            except ValueError:
                salience = 0.5
            tags = [
                t.strip()
                for t in (m.group("tags") or "").split(",")
                if t.strip()
            ]
            i += 1
            body: list[str] = []
            while i < len(lines) and not HEADER_RE.match(lines[i]):
                body.append(lines[i])
                i += 1
            text = "\n".join(body).strip()
            entries.append(
                {"text": text, "salience": salience, "tags": tags,
                 "ts": ts.isoformat(sep=" ", timespec="seconds")}
            )
        return entries

    # ------------------------------------------------------------------ score

    def _recency(self, ts_iso: str, now: datetime | None = None) -> float:
        try:
            ts = datetime.fromisoformat(ts_iso)
        except ValueError:
            return 0.0
        now = now or datetime.now()
        age_days = max(0.0, (now - ts.replace(tzinfo=None)).total_seconds() / 86400.0)
        half_life = max(self.half_life_days, 1e-9)
        return 0.5 ** (age_days / half_life)

    def _keyword(self, query: str, entry: dict) -> float:
        qwords = _words(query)
        if not qwords:
            return 0.0
        hay = _words(entry["text"] + " " + " ".join(entry["tags"]))
        return len(qwords & hay) / len(qwords)

    def score(self, query: str, entry: dict) -> float:
        """score = 0.5 * keyword_overlap + 0.3 * salience + 0.2 * recency

        - keyword_overlap: fraction of query words (lowercased, len > 2,
          stopwords removed) found in the entry text + tags.
        - recency: exponential decay, 0.5 ** (age_days / half_life_days),
          default half-life 7 days.
        """
        return (
            0.5 * self._keyword(query, entry)
            + 0.3 * entry["salience"]
            + 0.2 * self._recency(entry["ts"])
        )

    def recall(self, query: str, k: int = 5) -> list[dict]:
        """Top-k entries for a query, each dict with text/salience/tags/ts/score."""
        entries = self._load()  # read the file on every call: always fresh
        for e in entries:
            e["score"] = self.score(query, e)
        entries.sort(key=lambda e: e["score"], reverse=True)
        return entries[: max(0, k)]
