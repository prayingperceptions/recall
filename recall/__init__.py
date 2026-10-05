"""recall — local-first agent memory. No server, no API key, no vector DB —
just a Markdown file you can open, read, and hand-edit."""

from .memory import Memory

__version__ = "0.1.0"
__all__ = ["Memory", "__version__"]
