from pathlib import Path

from src.utils.shared_workspace import SharedWorkspace


def test_shared_workspace_creates_operational_folders(tmp_path: Path) -> None:
    workspace = SharedWorkspace.from_root(tmp_path / "ProgramaETL")

    workspace.ensure_exists()

    assert workspace.input_dir.is_dir()
    assert workspace.output_dir.is_dir()
    assert workspace.archive_dir.is_dir()
    assert workspace.logs_dir.is_dir()
