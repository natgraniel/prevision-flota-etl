"""Cross-user execution lock for a shared Windows folder."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class RunAlreadyInProgressError(RuntimeError):
    """Raised when another user is already generating a Programa."""


@contextmanager
def exclusive_run_lock(lock_dir: Path):
    """Create an atomic lock file and reliably remove it after the run."""

    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".programa_etl.lock"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(lock_path, flags)
    except FileExistsError as error:
        raise RunAlreadyInProgressError(
            "Another user is generating a Programa. Wait for it to finish before trying again."
        ) from error

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
            lock_file.write(f"started_at={datetime.now().isoformat(timespec='seconds')}\n")
        yield lock_path
    finally:
        lock_path.unlink(missing_ok=True)
