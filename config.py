# ============================================================
#  CONFIGURATION
#  ⚠️  Repo is PUBLIC — all secrets are loaded from environment
#  variables, never hardcoded here.
#
#  Set these on your VPS before running the bot:
#
#    export DISCORD_TOKEN="your_token"
#    export OPENROUTER_API_KEY="your_key"
#    export GITHUB_TOKEN="your_pat"
#
#  Or add them to your systemd service file (see README).
# ============================================================

import os

DISCORD_TOKEN   = "MTQ4Mzc4NzgxMzAyMjQ2NjI0MQ.GvpPbj.nMQVCK3qBofL6x5AQ2Fnew7dBVmNHSerk-5jes"
# Add all your category IDs here (right-click category in Discord → Copy ID)
CATEGORY_IDS    = [
    1406552157003583509,   # Category 1 — General Library
    1479351372309594203,   # Category 2 — Hinduism Library
    1479349422503755906,   # Category 3 — Islamic Library
]

# --- Openrouter API(for Summarization)
OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEYsk-or-v1-bc7b3a0dd80ac22ef422beab9a03f950aca726e6eb36ef14f278e1166d150173"
OPENROUTER_MODEL   = "anthropic/claude-sonnet-4-5"

# --- Obsidian Vault (absolute path on VPS) ---
VAULT_PATH = "D:\My work\Unofficial\Backup Bot\vaultpath"

# --- GitHub (for .md backup) ---
GITHUB_REPO_URL  = "https://github.com/Thxdlibrary/Backupbot.git"
GITHUB_USERNAME  = "Thxdlibrary"
GITHUB_TOKEN     = os.getenv("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")
GIT_AUTHOR_NAME  = "Backup Obsidian Bot"
GIT_AUTHOR_EMAIL = "fortuneteller715@gmail.com"

# --- Smart Filtering ---
MIN_MESSAGE_LENGTH           = 30
ALWAYS_SAVE_WITH_ATTACHMENTS = True

# --- Rate Limiting (be nice to Discord API) ---
HISTORY_FETCH_DELAY = 0.5    # seconds between batches during bulk export
BULK_FETCH_LIMIT    = 100    # messages per API call (max 100)

# --- Git ---
GIT_PUSH_EVERY_N = 10        # commit+push after every N new messages

# --- Folder names inside vault ---
NOTES_SUBFOLDER       = "Library"
ATTACHMENTS_SUBFOLDER = "Attachments"
CHECKPOINT_FILE       = ".last_message_ids.json"

# --- Validate secrets on startup ---
def validate():
    missing = []
    if not DISCORD_TOKEN:       missing.append("DISCORD_TOKEN")
    if not OPENROUTER_API_KEY:  missing.append("OPENROUTER_API_KEY")
    if not GITHUB_TOKEN:        missing.append("GITHUB_TOKEN")
    if missing:
        raise EnvironmentError(
            f"\n[config] ❌ Missing environment variables: {', '.join(missing)}\n"
            f"  Set them with: export VARIABLE_NAME='value'\n"
            f"  Or add them to your systemd service file.\n"
        )