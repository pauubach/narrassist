import platform
from pathlib import Path

from narrative_assistant.nlp.grammar import languagetool_manager as ltm


def _reset_lt_state() -> None:
    ltm._manager = None
    ltm._installing = False
    ltm._install_progress = None


def _create_bundled_lt_install(resource_dir: Path) -> Path:
    binaries_dir = resource_dir / "binaries"
    lt_dir = binaries_dir / "languagetool"
    lt_dir.mkdir(parents=True, exist_ok=True)
    (lt_dir / "languagetool-server.jar").write_text("jar", encoding="utf-8")

    java_dir = binaries_dir / "java-jre" / "bin"
    java_dir.mkdir(parents=True, exist_ok=True)
    java_name = "java.exe" if platform.system() == "Windows" else "java"
    java_bin = java_dir / java_name
    java_bin.write_text("bin", encoding="utf-8")
    if platform.system() != "Windows":
        java_bin.chmod(0o755)

    return binaries_dir


def test_manager_prefers_bundled_installation_in_embedded_mode(monkeypatch, tmp_path: Path):
    _reset_lt_state()
    resource_dir = tmp_path / "resources"
    binaries_dir = _create_bundled_lt_install(resource_dir)

    monkeypatch.setenv("NA_EMBEDDED", "1")
    monkeypatch.setenv("NA_RESOURCE_DIR", str(resource_dir))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))

    manager = ltm.LanguageToolManager()

    assert manager.is_installed is True
    assert manager._lt_dir == binaries_dir / "languagetool"
    assert manager._java_dir == binaries_dir / "java-jre"


def test_get_java_command_prefers_bundled_java_in_embedded_mode(monkeypatch, tmp_path: Path):
    _reset_lt_state()
    resource_dir = tmp_path / "resources"
    binaries_dir = _create_bundled_lt_install(resource_dir)
    java_name = "java.exe" if platform.system() == "Windows" else "java"
    expected_java = binaries_dir / "java-jre" / "bin" / java_name

    monkeypatch.setenv("NA_EMBEDDED", "1")
    monkeypatch.setenv("NA_RESOURCE_DIR", str(resource_dir))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))

    calls: list[str] = []

    class _Result:
        def __init__(self, returncode: int):
            self.returncode = returncode

    def fake_run(command, **kwargs):
        calls.append(str(command[0]))
        return _Result(0)

    monkeypatch.setattr(ltm.subprocess, "run", fake_run)

    manager = ltm.LanguageToolManager()
    command = manager._get_java_command()

    assert command == str(expected_java)
    assert calls == [str(expected_java)]


def test_start_lt_installation_short_circuits_when_bundled_install_exists(
    monkeypatch, tmp_path: Path
):
    _reset_lt_state()
    resource_dir = tmp_path / "resources"
    _create_bundled_lt_install(resource_dir)

    monkeypatch.setenv("NA_EMBEDDED", "1")
    monkeypatch.setenv("NA_RESOURCE_DIR", str(resource_dir))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))

    success, message = ltm.start_lt_installation()
    progress = ltm.get_install_progress()

    assert success is True
    assert "disponible" in message.lower()
    assert ltm.is_lt_installing() is False
    assert progress is not None
    assert progress.phase == "completed"
