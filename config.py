# config.py
# ─────────────────────────────────────────────────────────────────────────────
# Single source of truth for all configuration values.
# If you want to tweak behaviour — feeds, thresholds, limits — this is the
# only file you ever need to touch.
# ─────────────────────────────────────────────────────────────────────────────

# ── Gemini ────────────────────────────────────────────────────────────────────

# Model used for both Gemini calls (Flash = fast + cheap, good enough for this)
GEMINI_MODEL = "gemini-2.5-flash"

# ── Scoring (Step 5) ──────────────────────────────────────────────────────────

# Articles scoring below this are dropped before the summarization call
RELEVANCE_THRESHOLD = 5

# ── Article body (Step 3 & 4) ─────────────────────────────────────────────────

# Max words to send to Gemini — covers any real article without burning tokens
MAX_WORDS = 3000

# Seconds to wait before timing out an article HTTP request
FETCH_TIMEOUT_SECONDS = 10

# ── RSS Feeds (Step 1) ────────────────────────────────────────────────────────
# Add or remove feeds here. Each entry is a plain RSS/Atom URL.
# The label is only used for display in the terminal output.

RSS_FEEDS = [
    {
        "label": "The Rundown AI",
        "url": "https://www.therundown.ai/rss",
    },
    {
        "label": "Import AI (Jack Clark)",
        "url": "https://importai.substack.com/feed",
    },
    {
        "label": "Ahead of AI (Sebastian Raschka)",
        "url": "https://magazine.sebastianraschka.com/feed",
    },
    {
        "label": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml",
    },
    {
        "label": "Google DeepMind",
        "url": "https://deepmind.google/blog/rss.xml",
    },
    {
        "label": "OpenAI",
        "url": "https://openai.com/blog/rss.xml",
    },
    {
        "label": "Andrej Karpathy (Substack)",
        "url": "https://karpathy.substack.com/feed",
    },
    {
        "label": "The Batch (Andrew Ng)",
        "url": "https://www.deeplearning.ai/the-batch/feed/",
    },
]

# ── Storage (Step 2) ──────────────────────────────────────────────────────────

# Path to the file that tracks already-seen article URLs
SEEN_FILE_PATH = "seen.json"