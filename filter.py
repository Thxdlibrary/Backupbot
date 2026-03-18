"""
filter.py
Decides whether a Discord message is worth saving.
Filters out spam, filler, and low-value content.
"""

import discord
from config import MIN_MESSAGE_LENGTH, FILLER_WORDS


def is_worth_saving(msg: discord.Message) -> bool:
    """
    Returns True if the message contains useful content.
    Filters out:
      - Bot messages
      - Very short messages (below MIN_MESSAGE_LENGTH)
      - Pure filler/emoji messages
      - System messages (joins, pins etc.)
    Always saves messages with attachments or embeds regardless of text.
    """

    # Always ignore bots
    if msg.author.bot:
        return False

    # Always save messages with attachments (PDFs, images, files)
    if msg.attachments:
        return True

    # Always save messages with rich embeds (links with previews)
    if msg.embeds:
        return True

    # Ignore Discord system messages
    if msg.type != discord.MessageType.default and msg.type != discord.MessageType.reply:
        return False

    content = msg.content.strip()

    # Ignore empty messages
    if not content:
        return False

    # Ignore pure filler words
    if content.lower() in FILLER_WORDS:
        return False

    # Ignore very short messages
    if len(content) < MIN_MESSAGE_LENGTH:
        return False

    return True
