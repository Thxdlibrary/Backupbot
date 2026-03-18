"""
ai_summary.py
Uses Anthropic Claude API to summarize long Discord messages.
Only runs when AI_ENABLED=True and message is longer than AI_MIN_LENGTH.
"""

import anthropic
from config import AI_ENABLED, ANTHROPIC_API_KEY, AI_MIN_LENGTH

# Initialize client once
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if AI_ENABLED else None


def summarize(content: str, channel_name: str) -> str | None:
    """
    Summarize a long message. Returns summary string or None if skipped.
    Only runs if:
      - AI is enabled
      - Content is longer than AI_MIN_LENGTH characters
    """
    if not AI_ENABLED or not _client:
        return None

    if len(content) < AI_MIN_LENGTH:
        return None

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"This message is from a Discord study library channel called #{channel_name}.\n\n"
                        f"Message:\n{content}\n\n"
                        "Write a concise 2-3 sentence summary of the key points. "
                        "Focus on what is being shared or explained. "
                        "Do not start with 'This message' or 'The user'."
                    )
                }
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[ai] Summarization failed: {e}")
        return None
