"""Recoverable pre-change snapshots for local file tools."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .models import ToolValidationError


class SnapshotStore:
    def __init__(self, root: Path | str, storage: Path | str) -> None:
        self.root = Path(root).resolve()
        self.storage = Path(storage).resolve()
        if self.storage != self.root and self.root not in self.storage.parents:
            raise ValueError("snapshot storage must be inside the project root")
        self.storage.mkdir(parents=True, exist_ok=True)

    def capture(self, path: Path) -> str:
        snapshot_id = uuid.uuid4().hex
        existed = path.is_file()
        content = path.read_bytes() if existed else b""
        (self.storage / f"{snapshot_id}.bin").write_bytes(content)
        metadata = {"path": path.relative_to(self.root).as_posix(), "existed": existed}
        (self.storage / f"{snapshot_id}.json").write_text(json.dumps(metadata), encoding="utf-8")
        return snapshot_id

    def restore(self, snapshot_id: str) -> dict[str, object]:
        if not snapshot_id or any(char not in "0123456789abcdef" for char in snapshot_id):
            raise ToolValidationError("invalid snapshot id")
        metadata_path = self.storage / f"{snapshot_id}.json"
        if not metadata_path.is_file():
            raise ToolValidationError("snapshot does not exist")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        path = (self.root / metadata["path"]).resolve()
        if path != self.root and self.root not in path.parents:
            raise ToolValidationError("snapshot path escapes project root")
        if metadata["existed"]:
            atomic_write(path, (self.storage / f"{snapshot_id}.bin").read_bytes())
        elif path.exists():
            path.unlink()
        return {"snapshot_id": snapshot_id, "path": metadata["path"], "restored": True}


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
