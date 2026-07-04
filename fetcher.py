# fetcher.py
# ─────────────────────────────────────────────────────────────────────────────
# Responsible for two things only:
#   Step 1 — pull article metadata from an RSS feed
#   Step 3 — fetch the full article body from the article URL
#
# Nothing in here touches Gemini, seen.json, or the terminal.
# ─────────────────────────────────────────────────────────────────────────────

import feedparser
import httpx
from bs4 import BeautifulSoup

from config import FETCH_TIMEOUT_SECONDS, MAX_WORDS


# ── Data shape ────────────────────────────────────────────────────────────────

# Every article flowing through the pipeline is a plain dict with these keys.
# Using a dict keeps it simple — no ORM, no dataclass magic.
#
# {
#     "title"    : str   — article headline
#     "url"      : str   — canonical article URL (used as unique identifier)
#     "source"   : str   — feed label from config.py (e.g. "Hugging Face")
#     "body"     : str   — full plain-text article body (added in step 3)
# }


# ── Step 1 ────────────────────────────────────────────────────────────────────

def fetch_feed(feed_label: str, feed_url: str) -> list[dict]:
    """
    Parse an RSS/Atom feed and return a list of article dicts.

    Each dict contains title, url, and source.
    The body field is NOT populated here — that happens in fetch_article_body().

    Args:
        feed_label: Human-readable name for this feed (from config.py).
        feed_url:   RSS/Atom URL to fetch.

    Returns:
        List of article dicts. Empty list if the feed is unreachable or empty.
    """
    parsed = feedparser.parse(feed_url)

    if parsed.bozo and not parsed.entries:
        # bozo=True means feedparser hit a parse error.
        # We still proceed if there are entries — some feeds are technically
        # malformed but still readable. We only bail if there's nothing at all.
        print(f"  [fetcher] Could not read feed: {feed_label}")
        return []

    articles = []

    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        url   = entry.get("link",  "").strip()

        if not title or not url:
            # Skip malformed entries that are missing the basics.
            continue

        articles.append({
            "title":  title,
            "url":    url,
            "source": feed_label,
            "body":   "",        # populated later in step 3
        })

    return articles


# ── Step 3 ────────────────────────────────────────────────────────────────────

def fetch_article_body(article: dict) -> dict:
    """
    Fetch the full HTML of an article URL, strip tags, and return clean text.

    Mutates the article dict in place by filling the 'body' field.
    Also truncates to MAX_WORDS so we never send a bloated payload to Gemini.

    Args:
        article: An article dict produced by fetch_feed(). Must have a 'url'.

    Returns:
        The same article dict with 'body' populated.
        If the request fails, 'body' stays as an empty string.
    """
    try:
        response = httpx.get(
            article["url"],
            timeout=FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"},
        )
        response.raise_for_status()

    except httpx.TimeoutException:
        print(f"  [fetcher] Timed out fetching: {article['url']}")
        return article

    except httpx.HTTPStatusError as e:
        print(f"  [fetcher] HTTP {e.response.status_code} for: {article['url']}")
        return article

    except httpx.RequestError as e:
        print(f"  [fetcher] Request error for {article['url']}: {e}")
        return article

    # Parse HTML and extract readable text
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove boilerplate tags that add noise but no content
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    plain_text = soup.get_text(separator=" ", strip=True)

    # Truncate to MAX_WORDS — first N words cover everything meaningful
    words      = plain_text.split()
    truncated  = " ".join(words[:MAX_WORDS])

    article["body"] = truncated
    return article