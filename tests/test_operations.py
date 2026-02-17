import os
from pathlib import Path

from KOV.tools.operations import (
    delete_file,
    list_dir,
    read_file,
    run_shell,
    write_file,
)


def _set_workspace(tmp_path: Path) -> None:
    os.environ["KOV_WORKSPACE_ROOT"] = str(tmp_path)


def test_write_then_read_file(tmp_path: Path):
    _set_workspace(tmp_path)
    result = write_file({"path": "notes.txt", "content": "hello"})
    assert result["ok"] is True

    read_result = read_file("notes.txt")
    assert read_result["ok"] is True
    assert read_result["data"] == "hello"


def test_path_escape_is_blocked(tmp_path: Path):
    _set_workspace(tmp_path)
    result = read_file("../outside.txt")
    assert result["ok"] is False
    assert "outside workspace root" in result["error"]


def test_list_dir_returns_entries(tmp_path: Path):
    _set_workspace(tmp_path)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    result = list_dir(".")
    assert result["ok"] is True
    assert result["data"] == ["a.txt", "b.txt"]


def test_delete_file_with_confirmation(tmp_path: Path, monkeypatch):
    _set_workspace(tmp_path)
    target = tmp_path / "delete_me.txt"
    target.write_text("x", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = delete_file("delete_me.txt")
    assert result["ok"] is True
    assert not target.exists()


def test_run_shell_blocks_non_allowlisted_command(tmp_path: Path):
    _set_workspace(tmp_path)
    result = run_shell("bash -lc 'echo hello'")
    assert result["ok"] is False
    assert "not in the allowlist" in result["error"]


def test_run_shell_executes_allowlisted_command(tmp_path: Path):
    _set_workspace(tmp_path)
    result = run_shell("echo hello")
    assert result["ok"] is True
    assert result["meta"]["succeeded"] is True
    assert "hello" in result["data"]
