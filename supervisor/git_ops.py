"""
Git operations for ChoirOS.

Checkpoints, commits, and artifact delivery.
"""

import fnmatch
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import get_store


# Root of the git repo
REPO_ROOT = Path(__file__).parent.parent
CHOIRIGNORE_PATH = REPO_ROOT / ".choirignore"

DEFAULT_CHOIR_IGNORE_PATTERNS = [
    "*.log",
    "*.tmp",
    "node_modules/",
    "dist/",
    "build/",
    ".env*",
    "*.sqlite-journal",
    "__pycache__/",
    ".choir/",
]


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


def load_choirignore() -> list[str]:
    """Load ignore patterns from .choirignore if present."""
    if not CHOIRIGNORE_PATH.exists():
        return DEFAULT_CHOIR_IGNORE_PATTERNS

    patterns = []
    for line in CHOIRIGNORE_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)

    return patterns or DEFAULT_CHOIR_IGNORE_PATTERNS


def is_ignored(path: str, patterns: list[str]) -> bool:
    """Return True if path matches any ignore pattern."""
    normalized = path.replace("\\", "/")

    for pattern in patterns:
        if pattern.endswith("/"):
            if normalized.startswith(pattern) or normalized.startswith(pattern.rstrip("/")):
                return True
        if fnmatch.fnmatch(normalized, pattern):
            return True

    return False


def filter_ignored_files(status: dict) -> dict:
    """Filter status entries using .choirignore patterns."""
    patterns = load_choirignore()
    keys = ["modified", "added", "deleted", "untracked"]

    ignored = []
    filtered = {}
    for key in keys:
        filtered[key] = []
        for path in status[key]:
            if is_ignored(path, patterns):
                ignored.append(path)
            else:
                filtered[key].append(path)

    filtered["ignored"] = sorted(set(ignored))
    filtered["clean"] = all(len(filtered[key]) == 0 for key in keys)
    return filtered


def stage_paths(paths: list[str]) -> subprocess.CompletedProcess:
    """Stage only the provided paths."""
    if not paths:
        return subprocess.CompletedProcess(args=["git", "add"], returncode=0)
    return git_run("add", "-A", "--", *paths)


def is_reachable_commit(sha: str) -> bool:
    """Return True if commit is valid and reachable from HEAD."""
    if not sha or len(sha) < 7:
        return False

    if git_run("cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return False

    return git_run("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0


def get_diff_preview(sha: str) -> str:
    """Get a summary of changes between sha and HEAD."""
    result = git_run("diff", "--stat", f"{sha}..HEAD")
    return result.stdout if result.returncode == 0 else result.stderr


def git_revert(sha: str, dry_run: bool = True) -> dict:
    """Safely reset to a commit with backup and preview."""
    if not is_reachable_commit(sha):
        return {
            "success": False,
            "error": f"Commit {sha} is not reachable from HEAD",
        }

    backup_branch = f"backup-before-revert-{int(time.time())}"
    backup_result = git_run("branch", backup_branch)
    if backup_result.returncode != 0:
        return {
            "success": False,
            "error": f"Failed to create backup branch: {backup_result.stderr}",
        }

    preview = get_diff_preview(sha)
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "backup_branch": backup_branch,
            "changes": preview,
        }

    result = git_run("reset", "--hard", sha)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git reset failed: {result.stderr}",
            "backup_branch": backup_branch,
        }

    return {
        "success": True,
        "reverted_to": sha,
        "message": f"Reverted to {sha}",
        "backup_branch": backup_branch,
        "changes": preview,
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
    filtered_status = filter_ignored_files(status)
    if filtered_status["clean"]:
        return {
            "success": True,
            "message": "Nothing to commit after applying .choirignore",
            "commit_sha": get_head_sha(),
            "changes": filtered_status,
        }

    paths_to_stage = (
        filtered_status["modified"]
        + filtered_status["added"]
        + filtered_status["deleted"]
        + filtered_status["untracked"]
    )

    # Stage filtered changes
    result = stage_paths(paths_to_stage)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git add failed: {result.stderr}",
        }

    # Commit
    result = git_run("commit", "-m", message)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"git commit failed: {result.stderr}",
        }

    # Get the new commit SHA
    commit_sha = get_head_sha()
    if not commit_sha:
        return {
            "success": False,
            "error": "Unable to determine commit SHA",
        }

    # Record in event store
    store.record_checkpoint(commit_sha, message)

    return {
        "success": True,
        "message": message,
        "commit_sha": commit_sha,
        "changes": filtered_status,
    }


def push(remote: str = "origin", branch: Optional[str] = None) -> dict:
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
