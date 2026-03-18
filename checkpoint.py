"""
checkpoint.py
Tracks the last saved message ID per channel.
Prevents duplicates and allows safe bot restarts.
"""

import json
import os
from config import CHECKPOINT_FILE


def load() -> dict:
    """Load checkpoint data. Returns empty dict if file doesn't exist."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {}


def save(data: dict):
    """Persist checkpoint data to disk."""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_last_id(channel_id: int) -> int | None:
    """Get the last saved message ID for a channel."""
    data = load()
    val = data.get(str(channel_id))
    return int(val) if val else None


def set_last_id(channel_id: int, message_id: int):
    """Update the last saved message ID for a channel."""
    data = load()
    data[str(channel_id)] = str(message_id)
    save(data)


def is_duplicate(channel_id: int, message_id: int) -> bool:
    """Return True if this message was already saved."""
    last = get_last_id(channel_id)
    return last is not None and message_id <= last
