"""
Git operations for ChoirOS.

Checkpoints, commits, and artifact delivery.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import get_store


# Root of the git repo
REPO_ROOT = Path(__file__).parent.parent


def git_run(*args, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    """Run a git command."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True
    )


def get_head_sha() -> Optional[str]:
    """Get the current HEAD commit SHA."""
    result = git_run("rev-parse", "HEAD")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_status() -> dict:
    """Get git status summary."""
    result = git_run("status", "--porcelain")
    
    lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    
    modified = []
    added = []
    deleted = []
    untracked = []
    
    for line in lines:
        if not line:
            continue
        status = line[:2]
        filepath = line[3:]
        
        if status[0] == "M" or status[1] == "M":
            modified.append(filepath)
        elif status[0] == "A":
            added.append(filepath)
        elif status[0] == "D" or status[1] == "D":
            deleted.append(filepath)
        elif status[0] == "?":
            untracked.append(filepath)
    
    return {
        "modified": modified,
        "added": added,
        "deleted": deleted,
        "untracked": untracked,
        "clean": len(lines) == 0
    }


def checkpoint(message: Optional[str] = None) -> dict:
    """
    Create a git checkpoint (add all + commit).
    
    Returns dict with commit info or error.
    """
    store = get_store()
    
    # Generate message if not provided
    if message is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        last_seq = store.get_latest_seq()
        message = f"checkpoint: {timestamp} (event seq {last_seq})"
    
    # Check if there are changes
    status = get_status()
    if status["clean"]:
        return {
            "success": True,
            "message": "Nothing to commit, working tree clean",
            "commit_sha": get_head_sha()
        }
    
    # Stage all changes
    result = git_run("add", "-A")
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git add failed: {result.stderr}"
        }
    
    # Commit
    result = git_run("commit", "-m", message)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git commit failed: {result.stderr}"
        }
    
    # Get the new commit SHA
    commit_sha = get_head_sha()
    
    # Record in event store
    store.record_checkpoint(commit_sha, message)
    
    return {
        "success": True,
        "message": message,
        "commit_sha": commit_sha,
        "changes": status
    }


def push(remote: str = "origin", branch: str = None) -> dict:
    """
    Push to remote.
    
    Returns dict with result.
    """
    if branch is None:
        # Get current branch
        result = git_run("branch", "--show-current")
        branch = result.stdout.strip() or "main"
    
    result = git_run("push", remote, branch)
    
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git push failed: {result.stderr}"
        }
    
    return {
        "success": True,
        "remote": remote,
        "branch": branch,
        "message": result.stdout or "Pushed successfully"
    }


def log(n: int = 10) -> list[dict]:
    """Get recent commits."""
    result = git_run(
        "log", 
        f"-{n}", 
        "--pretty=format:%H|%s|%ai|%an"
    )
    
    if result.returncode != 0:
        return []
    
    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            commits.append({
                "sha": parts[0],
                "message": parts[1],
                "date": parts[2],
                "author": parts[3]
            })
    
    return commits


def diff(ref: str = "HEAD") -> str:
    """Get diff against a reference."""
    result = git_run("diff", ref)
    return result.stdout
