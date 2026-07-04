# ai-digest
# AI Digest

A lightweight CLI tool that pulls the latest articles from AI/ML RSS feeds, scores them for relevance using Gemini, and prints a clean summary alongside a LinkedIn-ready draft — directly in your terminal.

No cloud infrastructure. No background processes. Runs when you run it.

---

## How it works

Every article goes through a strict 7-step pipeline:

```
RSS Feeds → Deduplicate → Fetch Body → Truncate → Score → Summarize → Print
```

1. **Fetch** — pulls article metadata from configured RSS feeds via `feedparser`
2. **Deduplicate** — checks a local `seen.json` file so you never see the same article twice
3. **Fetch body** — retrieves the full article HTML and strips it to plain text via `httpx` + `BeautifulSoup`
4. **Truncate** — caps the body at 3,000 words before any API call
5. **Score** — sends the title and a short excerpt to Gemini Flash for a relevance score (1–10); anything below the configured threshold is dropped
6. **Summarize** — sends the full truncated body to Gemini for a 3-paragraph summary and a LinkedIn post draft
7. **Print** — outputs everything to the terminal via `rich`; marks the article as seen

The two-call Gemini architecture is intentional. The scoring call is cheap and fast — it acts as a gate so you only pay for summarization on articles that actually matter.

---

## Terminal output

```
────────────────────────────────────────────────────────────
  AI DIGEST  —  17 Jun 2026
────────────────────────────────────────────────────────────

[1] Gemini 2.5 Ultra sets new benchmark on AIME 2025
    Google DeepMind  |  Score: 9/10  |  https://...

  SUMMARY

    Google DeepMind has published results showing Gemini 2.5 Ultra
    achieving 92% on the AIME 2025 benchmark, surpassing competing
    models from OpenAI and Anthropic...

    ...

── DRAFT ───────────────────────────────────────────

    The math reasoning race just shifted again.

    Google's Gemini 2.5 Ultra scored 92% on AIME 2025 — a benchmark
    that stumped most frontier models just 12 months ago...

    What does this mean for AI in education and scientific research?

    #AI #GoogleDeepMind #LLM #MachineLearning #GenerativeAI

────────────────────────────────────────────────────────────
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.11+ | |
| RSS parsing | `feedparser` | Handles RSS and Atom formats cleanly |
| HTTP client | `httpx` | Timeout control, redirect handling, clean error types |
| HTML parsing | `beautifulsoup4` | Reliable tag stripping to plain text |
| AI | Gemini 1.5 Flash via `google-genai` | Fast, cheap, sufficient quality for summarization |
| Terminal output | `rich` | Readable formatted output with colour |
| Config | `python-dotenv` | Keeps the API key out of source code |
| Deduplication | `seen.json` (flat file) | Zero infrastructure, survives restarts |

---

## Project structure

```
ai_digest/
  ├── main.py           # Entry point — orchestrates all 7 steps
  ├── config.py         # All configuration lives here and nowhere else
  ├── fetcher.py        # Steps 1 & 3 — RSS fetch and article body retrieval
  ├── deduplicator.py   # Step 2 — seen.json read/write and URL hashing
  ├── gemini.py         # Steps 5 & 6 — relevance scoring and summarization
  ├── printer.py        # Step 7 — all terminal output via rich
  ├── seen.json         # Auto-created on first run
  ├── requirements.txt
  └── .env              # GEMINI_API_KEY (not committed)
```

Each file has exactly one responsibility. If something breaks, you know which file to open.

---

## Prerequisites

- Python 3.11+
- A Google AI Studio API key — free tier at [aistudio.google.com](https://aistudio.google.com) covers typical usage comfortably

---

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/your-username/ai-digest.git
cd ai-digest
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Add your API key**

Create a `.env` file in the project root:

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

**4. Run**

```bash
python main.py
```

---

## Usage

### Normal run — pulls from all configured RSS feeds

```bash
python main.py
```

Fetches all feeds, skips anything already seen, scores and summarizes new articles, prints to terminal.

### Test mode — feed a single article URL directly

```bash
python main.py --url "https://openai.com/blog/gpt-4o-mini"
```

Bypasses RSS fetch and deduplication entirely. Jumps straight to body fetch → score → summarize → print. Nothing is written to `seen.json` so you can re-run the same URL freely.

Useful for testing prompt quality or verifying the pipeline is working before a full run.

---

## Configuration

All configurable values live in `config.py`. This is the only file you need to touch to change behaviour.

```python
# The Gemini model used for both API calls
GEMINI_MODEL = "gemini-1.5-flash"

# Articles scoring below this are dropped before summarization
RELEVANCE_THRESHOLD = 7

# Max words sent to Gemini per article — controls cost and latency
MAX_WORDS = 3000

# Seconds before an article fetch times out
FETCH_TIMEOUT_SECONDS = 10

# RSS feeds to pull from — add or remove entries freely
RSS_FEEDS = [
    {"label": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml"},
    {"label": "Hugging Face",    "url": "https://huggingface.co/blog/feed.xml"},
    ...
]
```

### Recommended feeds for daily content

| Source | URL |
|---|---|
| The Rundown AI | `https://www.therundown.ai/rss` |
| Import AI (Jack Clark) | `https://importai.substack.com/feed` |
| Ahead of AI (Sebastian Raschka) | `https://magazine.sebastianraschka.com/feed` |
| Hugging Face | `https://huggingface.co/blog/feed.xml` |
| Google DeepMind | `https://deepmind.google/blog/rss.xml` |
| OpenAI | `https://openai.com/blog/rss.xml` |
| Andrej Karpathy | `https://karpathy.substack.com/feed` |
| The Batch (Andrew Ng) | `https://www.deeplearning.ai/the-batch/feed/` |

---

## Cost

Gemini 1.5 Flash is used for both calls. At typical usage — 50 articles per day, ~2,000 tokens each — you stay well inside the free tier (1M tokens/day on Google AI Studio).

If you scale to hundreds of articles daily, expect costs under $1/month.

---

## Optional: run on a schedule

To get a morning digest automatically without thinking about it, add a cron job on your Mac:

```bash
# Open crontab
crontab -e

# Run every day at 8:00 AM — output appended to digest.log
0 8 * * * cd /path/to/ai-digest && python main.py >> digest.log 2>&1
```

No code changes needed. The script is stateless between runs — `seen.json` handles continuity.

---

## Error handling

| Scenario | Behaviour |
|---|---|
| Feed unreachable | Skipped with a warning, other feeds continue |
| Article body fetch fails | Skipped, not marked as seen — retried next run |
| Gemini 503 (high demand) | Retried up to 3 times with a 5s wait between attempts |
| Gemini returns unparseable JSON | Skipped with a warning, not marked as seen |
| Article scores below threshold | Marked as seen, not printed |

---

## Resetting seen articles

To reprocess articles you've already seen:

```bash
echo "[]" > seen.json
```

---
