# deduplicator.py
# ─────────────────────────────────────────────────────────────────────────────
# Responsible for one thing only:
#   Step 2 — track which articles have already been seen across runs
#
# Uses a flat JSON file (seen.json) that stores a set of URL hashes.
# Hashing the URL instead of storing raw URLs keeps the file compact
# and avoids any encoding issues with special characters in URLs.
#
# Nothing in here touches Gemini, RSS feeds, or the terminal.
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import json
import os
from config import SEEN_FILE_PATH


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_seen() -> set[str]:
    """
    Load the set of seen URL hashes from disk.

    Returns:
        Set of hash strings. Empty set if the file doesn't exist yet
        (i.e. first ever run).
    """
    if not os.path.exists(SEEN_FILE_PATH):
        return set()

    with open(SEEN_FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # json stores lists, not sets — convert back on load
    return set(data)


def _save_seen(seen: set[str]) -> None:
    """
    Persist the current set of seen URL hashes to disk.

    Args:
        seen: The full set of hashes to write.
    """
    with open(SEEN_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, indent=2)


def _hash_url(url: str) -> str:
    """
    Return a short SHA-256 hex digest of a URL.

    Args:
        url: The canonical article URL.

    Returns:
        A 16-character hex string — unique enough for our purposes.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


# ── Public interface ──────────────────────────────────────────────────────────

def is_new(article: dict) -> bool:
    """
    Check whether an article has been seen in a previous run.

    Args:
        article: An article dict with at least a 'url' key.

    Returns:
        True if this article is new (not yet in seen.json).
        False if it has been seen before.
    """
    seen    = _load_seen()
    url_hash = _hash_url(article["url"])
    return url_hash not in seen


def mark_as_seen(article: dict) -> None:
    """
    Add an article's URL hash to seen.json so it is skipped on future runs.

    Call this only after the article has been fully processed and printed —
    not before, so a crash mid-run doesn't silently swallow articles.

    Args:
        article: An article dict with at least a 'url' key.
    """
    seen     = _load_seen()
    url_hash = _hash_url(article["url"])
    seen.add(url_hash)
    _save_seen(seen)