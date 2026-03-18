"""
index_gen.py
Auto-generates 00-Index.md — a master table of contents for the vault.
Groups notes by channel, then by date.
"""

import os
from pathlib import Path
from datetime import datetime
from config import VAULT_PATH, NOTES_SUBFOLDER


def regenerate():
    """Rebuild the master index file."""
    library_path = Path(VAULT_PATH) / NOTES_SUBFOLDER
    index_path   = Path(VAULT_PATH) / "00-Index.md"

    if not library_path.exists():
        return

    lines = [
        "# 📚 Library Index",
        "",
        f"> Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "---",
        "",
    ]

    channel_dirs = sorted([d for d in library_path.iterdir() if d.is_dir()])

    for ch_dir in channel_dirs:
        notes = sorted(ch_dir.glob("*.md"), reverse=True)  # newest first
        if not notes:
            continue

        lines.append(f"## 📁 {ch_dir.name}")
        lines.append("")

        for note in notes:
            rel = os.path.relpath(note, Path(VAULT_PATH))
            # Extract date from filename for display
            name = note.stem
            lines.append(f"- [[{rel}|{name}]]")

        lines.append("")

    index_path.write_text("\n".join(lines), encoding="utf-8")
    print("[index] 00-Index.md regenerated.")
