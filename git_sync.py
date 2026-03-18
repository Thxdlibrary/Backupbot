"""
git_sync.py
Handles Git operations: init, LFS setup, commit, push to GitHub.
Only runs when GITHUB_ENABLED=True.
"""

import os
import subprocess
from datetime import datetime
from config import (
    VAULT_PATH, GITHUB_REPO_URL, GITHUB_USERNAME,
    GITHUB_TOKEN, GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GITHUB_ENABLED
)


def _run(cmd: list[str], cwd: str = VAULT_PATH) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git error: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def setup_lfs():
    """Configure Git LFS for binary files."""
    try:
        _run(["git", "lfs", "install"])
    except RuntimeError:
        print("[git] Git LFS not found. Install with: apt install git-lfs")
        return

    gitattributes = os.path.join(VAULT_PATH, ".gitattributes")
    rules = (
        "*.png filter=lfs diff=lfs merge=lfs -text\n"
        "*.jpg filter=lfs diff=lfs merge=lfs -text\n"
        "*.jpeg filter=lfs diff=lfs merge=lfs -text\n"
        "*.gif filter=lfs diff=lfs merge=lfs -text\n"
        "*.webp filter=lfs diff=lfs merge=lfs -text\n"
        "*.pdf filter=lfs diff=lfs merge=lfs -text\n"
        "*.mp4 filter=lfs diff=lfs merge=lfs -text\n"
        "*.zip filter=lfs diff=lfs merge=lfs -text\n"
    )
    with open(gitattributes, "w") as f:
        f.write(rules)
    print("[git] Git LFS configured.")


def setup_repo():
    """One-time repo initialisation. Safe to call multiple times."""
    if not GITHUB_ENABLED:
        return

    os.makedirs(VAULT_PATH, exist_ok=True)
    setup_lfs()

    if not os.path.exists(os.path.join(VAULT_PATH, ".git")):
        _run(["git", "init"])
        print("[git] Repo initialised.")

    _run(["git", "config", "user.name",  GIT_AUTHOR_NAME])
    _run(["git", "config", "user.email", GIT_AUTHOR_EMAIL])

    remote_url = GITHUB_REPO_URL.replace(
        "https://", f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@"
    )
    try:
        _run(["git", "remote", "add", "origin", remote_url])
    except RuntimeError:
        _run(["git", "remote", "set-url", "origin", remote_url])

    # .gitignore
    gitignore = os.path.join(VAULT_PATH, ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(
                ".obsidian/workspace.json\n"
                ".obsidian/cache\n"
                ".checkpoint.json\n"    # don't version the checkpoint
            )

    print("[git] Setup complete.")


def commit_and_push(message: str = None):
    """Stage all, commit, and push. Skips if nothing changed."""
    if not GITHUB_ENABLED:
        return

    _run(["git", "add", "-A"])
    if not _run(["git", "status", "--porcelain"]):
        return  # Nothing to commit

    if not message:
        message = f"sync: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

    _run(["git", "commit", "-m", message])

    try:
        _run(["git", "push", "-u", "origin", "main"])
    except RuntimeError:
        _run(["git", "push", "-u", "origin", "master"])

    print(f"[git] Pushed → {message}")
