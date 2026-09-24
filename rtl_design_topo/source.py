"""Git source identity helpers used at candidate and execution boundaries."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


def current_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def capture_source_state(repo_root: Path, allow_dirty: bool) -> dict:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout
    if not status:
        return {"dirty": False}
    if not allow_dirty:
        raise RuntimeError("working tree is dirty; commit the candidate or pass --allow-dirty")

    digest = hashlib.sha256(status)
    digest.update(
        subprocess.run(
            ["git", "diff", "--binary", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    for encoded_path in sorted(path for path in untracked if path):
        digest.update(encoded_path)
        path = repo_root / encoded_path.decode("utf-8", errors="surrogateescape")
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {"dirty": True, "fingerprint_sha256": digest.hexdigest()}
