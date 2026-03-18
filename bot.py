"""
bot.py — Production-ready Discord → Obsidian sync bot
 
Features:
  ✅ Mode 1: Bulk export (resume-safe via checkpoints)
  ✅ Mode 2: Live sync (event-driven, no polling loops)
  ✅ Smart filtering (ignores spam/noise)
  ✅ Duplicate prevention (message ID tracking)
  ✅ AI summarization (Anthropic Claude)
  ✅ Rate limit safe (delays + exponential backoff)
  ✅ Attachment download
  ✅ Auto Git push every N messages
  ✅ Auto index regeneration
"""
 
import os
import asyncio
import aiohttp
import discord
from pathlib import Path
 
import checkpoint
import filter as msg_filter
import formatter
import index_gen
import git_sync
from ai_summary import summarize
from config import (
    DISCORD_TOKEN, CATEGORY_IDS, VAULT_PATH,
    HISTORY_FETCH_DELAY, ATTACHMENTS_SUBFOLDER,
    GIT_PUSH_EVERY_N, ALLOWED_GUILD_IDS
)
import config
config.validate()   # ← fail fast if any secret is missing
 
# ── setup ─────────────────────────────────────────────────────────────────────
 
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
 
new_message_counter = 0   # messages since last git push
 
 
# ── helpers ───────────────────────────────────────────────────────────────────
 
async def download_attachment(session: aiohttp.ClientSession, att: discord.Attachment):
    dest = formatter.attachment_path(att.filename)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        async with session.get(att.url) as resp:
            if resp.status == 200:
                dest.write_bytes(await resp.read())
                print(f"  [attachment] Downloaded: {att.filename}")
    except Exception as e:
        print(f"  [warn] Attachment download failed ({att.filename}): {e}")
 
 
async def process_message(message: discord.Message, session: aiohttp.ClientSession):
    """Full pipeline: filter → download → summarize → write → checkpoint."""
    global new_message_counter
 
    # Duplicate check
    if checkpoint.is_duplicate(message.channel.name, message.id):
        return
 
    # Smart filter
    if not msg_filter.should_save(message):
        return
 
    # Download attachments
    for att in message.attachments:
        await download_attachment(session, att)
 
    # AI Summary (only for messages with real content)
    summary = ""
    if message.content and len(message.content) >= 100:
        summary = await summarize(message.content, message.channel.name)
 
    # Build and write note
    note_content = formatter.build_note(message, message.channel.name, summary)
    note_file    = formatter.note_path(message.channel.name, message)
    note_file.parent.mkdir(parents=True, exist_ok=True)
    note_file.write_text(note_content, encoding="utf-8")
 
    # Mark as saved
    checkpoint.mark_saved(message.id)
    checkpoint.set_last_id(message.channel.name, message.id)
 
    new_message_counter += 1
 
 
# ── bulk export ───────────────────────────────────────────────────────────────
 
async def bulk_export(category: discord.CategoryChannel):
    """
    Export all existing messages from every channel in the category.
    Resume-safe: skips already-saved messages using checkpoints.
    Rate-limit safe: adds delay between batches.
    """
    print(f"\n[export] Starting bulk export for category: '{category.name}'")
    total_saved = 0
 
    async with aiohttp.ClientSession() as session:
        for channel in category.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
 
            last_id = checkpoint.get_last_id(channel.name)
            print(f"\n[export] #{channel.name} — resuming from message ID: {last_id or 'beginning'}")
 
            count = 0
            skipped = 0
 
            try:
                async for message in channel.history(
                    limit=None,
                    oldest_first=True,
                    after=discord.Object(id=last_id) if last_id else None
                ):
                    if checkpoint.is_duplicate(channel.name, message.id):
                        skipped += 1
                        continue
 
                    await process_message(message, session)
                    count += 1
 
                    # Rate limit protection — pause every 100 messages
                    if count % 100 == 0:
                        print(f"  ... {count} saved, {skipped} skipped. Pausing...")
                        await asyncio.sleep(HISTORY_FETCH_DELAY)
 
            except discord.Forbidden:
                print(f"  [warn] No permission to read #{channel.name}, skipping.")
            except discord.HTTPException as e:
                print(f"  [error] HTTP error on #{channel.name}: {e}. Will retry next run.")
 
            print(f"  [export] #{channel.name} done — {count} saved, {skipped} skipped.")
            total_saved += count
 
    print(f"\n[export] Bulk export complete — {total_saved} messages saved total.")
    index_gen.regenerate()
    git_sync.commit_and_push("bulk export: initial sync")
 
 
# ── live sync ─────────────────────────────────────────────────────────────────
 
@client.event
async def on_message(message: discord.Message):
    global new_message_counter
 
    if message.author.bot:
        return
    if not isinstance(message.channel, discord.TextChannel):
        return
    if message.channel.category_id not in CATEGORY_IDS:
        return
 
    async with aiohttp.ClientSession() as session:
        await process_message(message, session)
 
    print(f"[live] #{message.channel.name} — new message saved (total since push: {new_message_counter})")
 
    # Regenerate index and push every N messages
    if new_message_counter >= GIT_PUSH_EVERY_N:
        index_gen.regenerate()
        git_sync.commit_and_push(f"live sync: {new_message_counter} new messages")
        new_message_counter = 0
 
 
# ── security ──────────────────────────────────────────────────────────────────
 
@client.event
async def on_guild_join(guild: discord.Guild):
    """Leave immediately if bot is added to an unauthorized server."""
    if guild.id not in ALLOWED_GUILD_IDS:
        print(f"[security] ⚠️  Unauthorized server: '{guild.name}' (ID: {guild.id}). Leaving...")
        await guild.leave()
        print(f"[security] Left '{guild.name}' successfully.")
 
 
# ── on_ready ──────────────────────────────────────────────────────────────────
 
@client.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"  Bot online: {client.user}")
    print(f"{'='*50}\n")
 
    # Security — leave any server that isn't in the allowed list
    for guild in client.guilds:
        if guild.id not in ALLOWED_GUILD_IDS:
            print(f"[security] ⚠️  Unauthorized server: '{guild.name}'. Leaving...")
            await guild.leave()
 
    # Setup
    Path(VAULT_PATH).mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, ATTACHMENTS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    git_sync.setup_repo()
 
    # Load saved IDs from existing vault (crash recovery)
    checkpoint.load_saved_ids_from_vault(VAULT_PATH)
 
    # Find all target categories across all guilds
    categories = []
    for guild in client.guilds:
        for cat in guild.categories:
            if cat.id in CATEGORY_IDS:
                categories.append(cat)
                print(f"[bot] Found category: '{cat.name}' (ID: {cat.id})")
 
    if not categories:
        print(f"[error] No categories found for IDs: {CATEGORY_IDS}")
        print("  → Check CATEGORY_IDS in config.py and confirm bot is in the server.")
        return
 
    if len(categories) < len(CATEGORY_IDS):
        found_ids = {c.id for c in categories}
        missing = [cid for cid in CATEGORY_IDS if cid not in found_ids]
        print(f"[warn] Could not find categories with IDs: {missing}")
 
    # Bulk export all categories one by one
    for category in categories:
        await bulk_export(category)
 
    print("\n[bot] ✅ All categories exported. Now listening for new messages...\n")
 
 
# ── entry ─────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
