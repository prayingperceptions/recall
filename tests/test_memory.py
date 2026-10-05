import os
import tempfile
from datetime import datetime, timedelta

import pytest

from recall import Memory


@pytest.fixture
def mem():
    return Memory(tempfile.mktemp(suffix=".md"))


def test_remember_recall_roundtrip(mem):
    mem.remember("The launch code is blue-42.", salience=0.9, tags=["codes"])
    hits = mem.recall("what is the launch code")
    assert hits, "recall should find the remembered entry"
    assert "blue-42" in hits[0]["text"]
    assert hits[0]["tags"] == ["codes"]
    assert hits[0]["salience"] == pytest.approx(0.9)
    assert "score" in hits[0]


def test_recent_salient_beats_old_trivial():
    path = tempfile.mktemp(suffix=".md")
    mem = Memory(path)
    # Seed an OLD, low-salience entry on the same topic
    old_ts = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {old_ts} | salience=0.1 | tags: pricing\n")
        f.write("Old pricing note: everything costs one dollar.\n\n")
    # New, high-salience entry on the same topic
    mem.remember("Current pricing: x402 calls cost $0.005 each.", salience=0.95, tags=["pricing"])
    hits = mem.recall("pricing for x402 calls", k=5)
    assert len(hits) == 2
    assert "$0.005" in hits[0]["text"], "recent + salient entry should rank first"
    assert hits[0]["score"] > hits[1]["score"]


def test_recall_returns_at_most_k(mem):
    for i in range(10):
        mem.remember(f"note number {i} about databases", salience=0.5)
    assert len(mem.recall("databases", k=3)) == 3
    assert len(mem.recall("databases", k=0)) == 0


def test_file_survives_reload():
    path = tempfile.mktemp(suffix=".md")
    Memory(path).remember("persist me", salience=0.7, tags=["t1", "t2"])
    mem2 = Memory(path)  # brand-new instance, same file
    hits = mem2.recall("persist")
    assert len(hits) == 1
    assert hits[0]["text"] == "persist me"
    assert hits[0]["tags"] == ["t1", "t2"]


def test_garbled_lines_do_not_crash(mem):
    with open(mem.path, "a", encoding="utf-8") as f:
        f.write("random human notes at the top\n")
        f.write("## not a real header\n")
        f.write("## 2026-13-99 99:99:99 | salience=oops\n")
        f.write("## 2026-10-01 12:00:00 | salience=0.8\n")
        f.write("A valid entry buried in the mess.\n")
    hits = mem.recall("valid entry")  # must not raise
    assert any("buried in the mess" in h["text"] for h in hits)


def test_salience_clamped(mem):
    mem.remember("clamped high", salience=5.0)
    mem.remember("clamped low", salience=-1.0)
    hits = {h["text"]: h for h in mem.recall("clamped", k=5)}
    assert hits["clamped high"]["salience"] == 1.0
    assert hits["clamped low"]["salience"] == 0.0


def test_empty_file_recalls_nothing(mem):
    assert mem.recall("anything") == []
