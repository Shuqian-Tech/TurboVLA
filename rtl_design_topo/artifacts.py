"""Content-addressed local artifact storage."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from .models import ArtifactRef


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, kind: str, content: bytes) -> ArtifactRef:
        digest = hashlib.sha256(content).hexdigest()
        destination = self.root / digest[:2] / digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
                handle.write(content)
                temporary = Path(handle.name)
            os.replace(temporary, destination)
        return ArtifactRef(kind, digest, str(destination), len(content))

    def put_text(self, kind: str, content: str) -> ArtifactRef:
        return self.put_bytes(kind, content.encode("utf-8"))

    def put_file(self, kind: str, source: Path) -> ArtifactRef:
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as input_handle, tempfile.NamedTemporaryFile(
            dir=self.root, delete=False
        ) as output_handle:
            temporary = Path(output_handle.name)
            while chunk := input_handle.read(1024 * 1024):
                digest.update(chunk)
                output_handle.write(chunk)
                size += len(chunk)
        hex_digest = digest.hexdigest()
        destination = self.root / hex_digest[:2] / hex_digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            temporary.unlink()
        else:
            os.replace(temporary, destination)
        return ArtifactRef(kind, hex_digest, str(destination), size)
