"""~20-line integration pattern: an agent loop that remembers every
observation and recalls relevant context before acting.

Run:  python examples/agent_loop.py   (from the repo root)
Uses a temp file — never touches the repo directory.
"""

import tempfile
from recall import Memory

mem = Memory(tempfile.mktemp(suffix=".md"))

observations = [
    ("The user deploys everything to Vercel on the hobby plan.", 0.7, ["deploy"]),
    ("x402 micropayment price is $0.005 per call (~6 sats at $86k BTC).", 0.9, ["x402", "pricing"]),
    ("The user's dog is named Biscuit.", 0.2, ["personal"]),
]

for text, sal, tags in observations:
    mem.remember(text, salience=sal, tags=tags)   # remember() each observation
    print(f"remembered: {text[:50]}...")

print("\n--- agent is about to set a price for a new API ---")
for hit in mem.recall("what should the API price be", k=2):  # recall() before acting
    print(f"[{hit['score']:.2f}] {hit['text']}  (tags: {', '.join(hit['tags'])})")
