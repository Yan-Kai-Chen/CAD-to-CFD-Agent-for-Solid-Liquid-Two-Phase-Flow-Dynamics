from pathlib import Path

from fromcad2cfd_solidworks.paths import WORKSPACE_ROOT, is_under_workspace, unique_path


def test_workspace_root_exists():
    assert WORKSPACE_ROOT.exists()


def test_unique_path_stays_under_workspace():
    path = unique_path(WORKSPACE_ROOT / "06_logs" / "unit_test_path.txt")
    assert is_under_workspace(path)
    assert path.name.startswith("unit_test_path")

