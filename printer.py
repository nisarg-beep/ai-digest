# printer.py
# ─────────────────────────────────────────────────────────────────────────────
# Responsible for one thing only:
#   Step 7 — print a processed article result to the terminal
#
# Uses the rich library for clean, readable formatting.
# Every visual decision lives here — nothing in main.py or elsewhere
# should be doing print() calls for article output.
#
# Nothing in here touches Gemini, RSS feeds, or seen.json.
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime

from rich.console import Console
from rich.rule import Rule
from rich.text import Text
from rich.padding import Padding

console = Console()


# ── Public interface ──────────────────────────────────────────────────────────

def print_header() -> None:
    """
    Print the digest header once at the start of a run.
    Shows the current date so you know when the digest was generated.
    """
    today = datetime.now().strftime("%d %b %Y")

    console.print()
    console.print(Rule(style="bright_black"))
    console.print(
        Text(f"  AI DIGEST  —  {today}", style="bold white"),
    )
    console.print(Rule(style="bright_black"))
    console.print()


def print_article(result: dict, index: int) -> None:
    """
    Print a single processed article result to the terminal.

    Outputs in this order:
      - Index, title, source, and relevance score
      - 3-paragraph summary
      - LinkedIn draft, clearly boxed off for easy copy-paste

    Args:
        result : A result dict produced by gemini.summarize_and_draft().
                 Expected keys: title, url, source, score, summary, linkedin_draft.
        index  : The article's position in this run (1-based), shown as a counter.
    """
    # ── Header line ───────────────────────────────────────────────────────────
    console.print(
        Text(f"[{index}] ", style="bold bright_black") +
        Text(result["title"], style="bold white")
    )
    console.print(
        Text(f"    {result['source']}", style="dim") +
        Text("  |  Score: ", style="dim") +
        Text(str(result["score"]) + "/10", style=_score_colour(result["score"])) +
        Text(f"  |  {result['url']}", style="dim")
    )
    console.print()

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print(Text("  SUMMARY", style="bold cyan"))
    console.print()

    for paragraph in result["summary"].split("\n"):
        paragraph = paragraph.strip()
        if paragraph:
            console.print(Padding(Text(paragraph, style="white"), (0, 4)))
            console.print()

    # ── LinkedIn draft ────────────────────────────────────────────────────────
    console.print(Rule(" DRAFT  ", style="cyan", align="left"))
    console.print()
    console.print(Padding(Text(result["linkedin_draft"], style="bright_white"), (0, 4)))
    console.print()
    console.print(Rule(style="cyan", align="left"))
    console.print()


def print_no_results() -> None:
    """
    Print a message when the run produces no new articles above the threshold.
    Called by main.py when the final results list is empty.
    """
    console.print(
        Padding(
            Text("No new articles found above the relevance threshold.", style="dim"),
            (0, 2)
        )
    )
    console.print()


def print_footer(total_fetched: int, total_printed: int) -> None:
    """
    Print a short stats line at the end of a run.

    Args:
        total_fetched  : Total articles pulled from all feeds this run.
        total_printed  : Articles that passed the threshold and were printed.
    """
    console.print(Rule(style="bright_black"))
    console.print(
        Padding(
            Text(
                f"  {total_printed} article(s) shown  |  "
                f"{total_fetched - total_printed} dropped or already seen",
                style="dim"
            ),
            (0, 0)
        )
    )
    console.print(Rule(style="bright_black"))
    console.print()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _score_colour(score: int) -> str:
    """
    Map a relevance score to a rich colour string for terminal display.

    Args:
        score: Integer between 1 and 10.

    Returns:
        A rich-compatible colour string.
    """
    if score >= 9:
        return "bold green"
    if score >= 7:
        return "green"
    if score >= 5:
        return "yellow"
    return "red"