# gemini.py
# ─────────────────────────────────────────────────────────────────────────────
# Responsible for two things only:
#   Step 5 — call Gemini to score article relevance (1–10)
#   Step 6 — call Gemini to summarize and draft a LinkedIn post
#
# Uses the google-genai SDK (v2+), which is the current Google GenAI library.
# Client is initialised once and reused across all calls.
# Both calls retry up to MAX_RETRIES times on transient 503 errors.
#
# Nothing in here touches RSS feeds, seen.json, or the terminal.
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
import time

from google import genai
from google.genai import types
from google.api_core.exceptions import ServiceUnavailable
from dotenv import load_dotenv

from config import GEMINI_MODEL


# ── Initialisation ────────────────────────────────────────────────────────────

load_dotenv()

# Single client instance reused for every API call in this module
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Shared generation config — JSON output, low temperature for consistency
_generation_config = types.GenerateContentConfig(
    temperature=0.2,
    response_mime_type="application/json",
)

# Retry settings for transient 503 errors
MAX_RETRIES     = 3
RETRY_WAIT_SECS = 5


# ── Internal helpers ──────────────────────────────────────────────────────────

def _generate_with_retry(prompt: str) -> str:
    """
    Call Gemini with automatic retries on transient 503 errors.

    Waits RETRY_WAIT_SECS between each attempt. Raises the final exception
    if all retries are exhausted so the caller can handle it explicitly.

    Args:
        prompt: The full prompt string to send.

    Returns:
        The raw response text from Gemini.

    Raises:
        Exception: Re-raises the last error after MAX_RETRIES attempts.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=_generation_config,
            )
            return response.text

        except ServiceUnavailable as e:
            last_error = e
            print(f"  [gemini] 503 on attempt {attempt}/{MAX_RETRIES} — retrying in {RETRY_WAIT_SECS}s...")
            time.sleep(RETRY_WAIT_SECS)

        except Exception as e:
            # Non-transient error — no point retrying
            raise e

    raise last_error


# ── Step 5 ────────────────────────────────────────────────────────────────────

def score_relevance(article: dict) -> int:
    """
    Ask Gemini to score how relevant this article is to AI / ML (1–10).

    Uses only the title and the first 200 words of the body — this call
    is meant to be fast and cheap. Full body is reserved for step 6.

    Args:
        article: An article dict with 'title' and 'body' keys.

    Returns:
        Integer score between 1 and 10.
        Returns 0 if the response cannot be parsed, so the article is dropped.
    """
    excerpt = " ".join(article["body"].split()[:200])

    prompt = f"""
You are screening articles for an AI/ML digest aimed at professionals in the tech industry.

Rate the following article on a scale of 1 to 10 based on how relevant and valuable it is
to someone who follows AI research, large language models, and the AI industry closely.

Scoring guide:
  9–10 : Major breakthrough, important release, or highly insightful analysis
  7–8  : Solid AI/ML content worth reading
  5–6  : Loosely related to AI but not especially insightful
  1–4  : Off-topic, generic tech news, or low-quality content

Respond with a single valid JSON object and nothing else.

Format:
{{"score": <integer 1-10>, "reason": "<one sentence>"}}

Article title: {article["title"]}
Article excerpt: {excerpt}
""".strip()

    try:
        raw    = _generate_with_retry(prompt)
        parsed = json.loads(raw)
        score  = int(parsed["score"])

        return max(1, min(score, 10))

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  [gemini] Could not parse score response for: {article['title']} — {e}")
        return 0

    except Exception as e:
        print(f"  [gemini] Scoring API error for: {article['title']} — {e}")
        return 0


# ── Step 6 ────────────────────────────────────────────────────────────────────

def summarize_and_draft(article: dict) -> dict:
    """
    Ask Gemini to produce a 3-paragraph summary and a LinkedIn post draft.

    This is the more expensive call — it receives the full truncated body.
    Only called for articles that passed the relevance threshold in step 5.

    Args:
        article: An article dict with 'title', 'source', 'score', and 'body' keys.

    Returns:
        A result dict with the following keys:
        {
            "title"          : str  — original article title
            "url"            : str  — original article URL
            "source"         : str  — feed label
            "score"          : int  — relevance score from step 5
            "summary"        : str  — 3-paragraph plain-text summary
            "linkedin_draft" : str  — ready-to-edit LinkedIn post with hashtags
        }
        Returns None if the API call or parsing fails.
    """
    prompt = f"""
You are an expert AI/ML writer creating content for a professional LinkedIn audience.

Given the article below, produce two things:

1. SUMMARY — a 3-paragraph plain-text summary of the article.
   - Paragraph 1: What the article is about and why it matters
   - Paragraph 2: The key technical details or findings
   - Paragraph 3: Implications or takeaways for AI practitioners

2. LINKEDIN_DRAFT — a LinkedIn post ready to publish (with minor edits).
   - Start with a strong hook line (not "I just read...")
   - 3–4 short punchy paragraphs
   - End with a question to drive engagement
   - Include 4–5 relevant hashtags on the last line
   - Keep the total under 250 words

Respond with a single valid JSON object and nothing else.

Format:
{{
  "summary": "<3 paragraphs separated by newlines>",
  "linkedin_draft": "<full LinkedIn post text>"
}}

Article title  : {article["title"]}
Article source : {article["source"]}
Article body   :
{article["body"]}
""".strip()

    try:
        raw    = _generate_with_retry(prompt)
        parsed = json.loads(raw)

        return {
            "title"          : article["title"],
            "url"            : article["url"],
            "source"         : article["source"],
            "score"          : article.get("score", 0),
            "summary"        : parsed["summary"].strip(),
            "linkedin_draft" : parsed["linkedin_draft"].strip(),
        }

    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [gemini] Could not parse summary response for: {article['title']} — {e}")
        return None

    except Exception as e:
        print(f"  [gemini] Summary API error for: {article['title']} — {e}")
        return None