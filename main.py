# main.py
# ─────────────────────────────────────────────────────────────────────────────
# Entry point. Orchestrates the full pipeline in the exact order of the flow:
#
#   Step 1 — fetch article metadata from RSS feeds
#   Step 2 — skip articles already seen in previous runs
#   Step 3 — fetch the full article body
#   Step 4 — truncation is handled inside fetcher.fetch_article_body()
#   Step 5 — score relevance with Gemini (fast, cheap call)
#   Step 6 — summarize and draft LinkedIn post with Gemini (full call)
#   Step 7 — print to terminal, mark as seen
#
# Usage:
#   python main.py                        # normal run via RSS feeds
#   python main.py --url <article_url>    # test mode — feed a single URL directly
#
# This file contains no business logic of its own.
# Every step delegates entirely to its responsible module.
# ─────────────────────────────────────────────────────────────────────────────

import argparse

from config import RSS_FEEDS, RELEVANCE_THRESHOLD
from fetcher import fetch_feed, fetch_article_body
from deduplicator import is_new, mark_as_seen
from gemini import score_relevance, summarize_and_draft
from printer import print_header, print_article, print_no_results, print_footer


# ── Test mode — single URL ────────────────────────────────────────────────────

def run_single_url(url: str) -> None:
    """
    Test mode: skip RSS fetch and deduplication, process one article directly.

    Jumps straight to step 3 using the provided URL.
    Nothing is written to seen.json so you can re-run the same URL freely.

    Args:
        url: The full article URL to process.
    """
    print_header()

    # Build a minimal article dict — same shape as what fetch_feed() produces
    article = {
        "title":  url,   # placeholder until we have the real title
        "url":    url,
        "source": "Manual",
        "body":   "",
    }

    # ── Step 3 & 4: Fetch full body ───────────────────────────────────────────
    article = fetch_article_body(article)

    if not article["body"]:
        print(f"  [main] Could not fetch body for: {url}")
        return

    # ── Step 5: Score relevance ───────────────────────────────────────────────
    score = score_relevance(article)
    article["score"] = score

    print(f"  [main] Relevance score: {score}/10")

    if score < RELEVANCE_THRESHOLD:
        print(f"  [main] Score below threshold ({RELEVANCE_THRESHOLD}) — would be dropped in normal run.")
        print(f"  [main] Continuing anyway for testing purposes.")

    # ── Step 6: Summarize and draft ───────────────────────────────────────────
    result = summarize_and_draft(article)

    if result is None:
        print(f"  [main] Summarization failed.")
        return

    # ── Step 7: Print — do NOT mark as seen in test mode ─────────────────────
    print_article(result, index=1)
    print_footer(total_fetched=1, total_printed=1)


# ── Normal mode — RSS feeds ───────────────────────────────────────────────────

def run() -> None:
    """
    Execute the full digest pipeline from RSS fetch to terminal output.
    """
    print_header()

    total_fetched = 0
    total_printed = 0
    article_index = 1

    for feed in RSS_FEEDS:

        # ── Step 1: Fetch article metadata from this feed ─────────────────────
        articles = fetch_feed(feed["label"], feed["url"])

        for article in articles:
            total_fetched += 1

            # ── Step 2: Skip if already seen in a previous run ────────────────
            if not is_new(article):
                continue

            # ── Step 3 & 4: Fetch full body (truncation handled inside) ───────
            article = fetch_article_body(article)

            if not article["body"]:
                # Body fetch failed — skip without marking as seen so we retry
                # next run in case it was a transient network issue
                continue

            # ── Step 5: Score relevance — drop anything below threshold ───────
            score = score_relevance(article)
            article["score"] = score

            if score < RELEVANCE_THRESHOLD:
                # Not relevant enough — mark as seen so we don't re-evaluate it
                mark_as_seen(article)
                continue

            # ── Step 6: Summarize and generate LinkedIn draft ─────────────────
            result = summarize_and_draft(article)

            if result is None:
                # Gemini call failed — do not mark as seen, retry next run
                continue

            # ── Step 7: Print to terminal, then mark as seen ──────────────────
            print_article(result, article_index)
            mark_as_seen(article)

            article_index += 1
            total_printed += 1

    # ── End of run summary ────────────────────────────────────────────────────
    if total_printed == 0:
        print_no_results()

    print_footer(total_fetched, total_printed)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Digest — daily AI/ML article summarizer")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Test mode: feed a single article URL directly, bypassing RSS and deduplication.",
    )
    args = parser.parse_args()

    if args.url:
        run_single_url(args.url)
    else:
        run()