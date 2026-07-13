"""Filesystem layout used when the application runs from a shared folder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SharedWorkspace:
    root: Path
    input_dir: Path
    output_dir: Path
    archive_dir: Path
    logs_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> "SharedWorkspace":
        root = root.expanduser().resolve()
        return cls(
            root=root,
            input_dir=root / "input",
            output_dir=root / "output",
            archive_dir=root / "archive",
            logs_dir=root / "logs",
        )

    def ensure_exists(self) -> None:
        for folder in (self.root, self.input_dir, self.output_dir, self.archive_dir, self.logs_dir):
            folder.mkdir(parents=True, exist_ok=True)
