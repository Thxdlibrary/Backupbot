"""
formatter.py
Converts a Discord message into a clean Obsidian-ready Markdown note.
Each message gets its own .md file named by date + first words of content.
"""

import re
import os
import aiohttp
import discord
from datetime import timezone
from pathlib import Path

from config import VAULT_PATH, NOTES_SUBFOLDER, ATTACHMENTS_SUBFOLDER
from ai_summary import summarize


def safe_filename(text: str, max_len: int = 40) -> str:
    """Create a safe filename from text."""
    text = re.sub(r'[\\/*?:"<>|#\[\]]', "", text)
    text = re.sub(r'\s+', "-", text.strip())
    return text[:max_len].rstrip("-")


def note_path(channel_name: str, msg: discord.Message) -> Path:
    """
    Returns the full path for a message's note file.
    Format: vault/Library/<channel>/<YYYY-MM-DD>-<slug>.md
    """
    dt = msg.created_at.astimezone(timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")

    # Build slug from message content or attachment name
    if msg.content:
        slug = safe_filename(msg.content[:50])
    elif msg.attachments:
        slug = safe_filename(msg.attachments[0].filename)
    else:
        slug = str(msg.id)

    filename = f"{date_str}-{slug}.md" if slug else f"{date_str}-{msg.id}.md"
    return Path(VAULT_PATH) / NOTES_SUBFOLDER / channel_name / filename


def attachment_dest(filename: str) -> Path:
    """Returns destination path for a downloaded attachment."""
    return Path(VAULT_PATH) / ATTACHMENTS_SUBFOLDER / filename


def auto_tags(msg: discord.Message, channel_name: str) -> list[str]:
    """Generate tags from channel name and content keywords."""
    tags = [channel_name.lower().replace(" ", "-")]

    content = (msg.content or "").lower()

    # Resource type tags
    if msg.attachments:
        for att in msg.attachments:
            if att.filename.endswith(".pdf"):
                tags.append("pdf")
            elif att.content_type and att.content_type.startswith("image"):
                tags.append("image")

    if any(w in content for w in ["http://", "https://", "www."]):
        tags.append("link")
    if any(w in content for w in ["important", "note", "remember", "key"]):
        tags.append("important")
    if any(w in content for w in ["summary", "summarize", "overview"]):
        tags.append("summary")

    return list(set(tags))


async def download_attachment(session: aiohttp.ClientSession, att: discord.Attachment) -> str | None:
    """Download attachment to vault and return its relative path."""
    dest = attachment_dest(att.filename)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        return str(os.path.relpath(dest, Path(VAULT_PATH)))

    try:
        async with session.get(att.url) as resp:
            if resp.status == 200:
                dest.write_bytes(await resp.read())
                return str(os.path.relpath(dest, Path(VAULT_PATH)))
    except Exception as e:
        print(f"[warn] Could not download {att.filename}: {e}")
    return None


async def build_note(msg: discord.Message, channel_name: str, session: aiohttp.ClientSession) -> tuple[Path, str]:
    """
    Build the full Markdown content for a message.
    Returns (file_path, markdown_content).
    """
    dt = msg.created_at.astimezone(timezone.utc)
    tags = auto_tags(msg, channel_name)
    tag_str = " ".join(f"#{t}" for t in tags)

    lines = []

    # --- Frontmatter ---
    lines += [
        "---",
        f"date: {dt.strftime('%Y-%m-%d')}",
        f"time: {dt.strftime('%H:%M')} UTC",
        f"channel: #{channel_name}",
        f"author: {msg.author.display_name}",
        f"discord_id: {msg.id}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]

    # --- Title ---
    lines += [
        f"# Message from {msg.author.display_name}",
        "",
        f"**Date:** {dt.strftime('%Y-%m-%d')}  ",
        f"**Channel:** #{channel_name}  ",
        f"**Tags:** {tag_str}",
        "",
        "---",
        "",
    ]

    # --- Content ---
    if msg.content:
        lines += [msg.content, ""]

    # --- AI Summary ---
    if msg.content:
        summary = summarize(msg.content, channel_name)
        if summary:
            lines += [
                "---",
                "",
                "## 🤖 AI Summary",
                "",
                summary,
                "",
            ]

    # --- Embeds (links) ---
    if msg.embeds:
        lines += ["---", "", "## 🔗 Links", ""]
        for embed in msg.embeds:
            if embed.url:
                title = embed.title or embed.url
                lines.append(f"- [{title}]({embed.url})")
            if embed.description:
                lines.append(f"  > {embed.description[:300]}")
        lines.append("")

    # --- Attachments ---
    if msg.attachments:
        lines += ["---", "", "## 📎 Attachments", ""]
        for att in msg.attachments:
            rel_path = await download_attachment(session, att)
            if rel_path:
                if att.content_type and att.content_type.startswith("image"):
                    lines.append(f"![[{rel_path}]]")
                else:
                    lines.append(f"[[{rel_path}]]")
            else:
                lines.append(f"- {att.filename} *(download failed)*")
        lines.append("")

    path = note_path(channel_name, msg)
    return path, "\n".join(lines)
