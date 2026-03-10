import os
import subprocess
from pathlib import Path

from scripts.download_languagetool_jre import MIN_LT_JAR_BYTES, verify_installation


def _create_embedded_layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    binaries_dir = tmp_path / "src-tauri" / "binaries"
    java_name = "java.exe" if os.name == "nt" else "java"
    java_bin = binaries_dir / "java-jre" / "bin" / java_name
    lt_jar = binaries_dir / "languagetool" / "languagetool-server.jar"
    java_bin.parent.mkdir(parents=True, exist_ok=True)
    lt_jar.parent.mkdir(parents=True, exist_ok=True)
    java_bin.write_bytes(b"java")
    lt_jar.write_bytes(b"x" * (MIN_LT_JAR_BYTES + 1))
    return binaries_dir, java_bin, lt_jar


def test_verify_installation_accepts_valid_bundled_services(monkeypatch, tmp_path: Path):
    binaries_dir, _java_bin, _lt_jar = _create_embedded_layout(tmp_path)

    monkeypatch.setattr(
        "scripts.download_languagetool_jre.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="", stderr='openjdk version "21"'
        ),
    )

    assert verify_installation(binaries_dir) is True


def test_verify_installation_rejects_non_executable_java(monkeypatch, tmp_path: Path):
    binaries_dir, _java_bin, _lt_jar = _create_embedded_layout(tmp_path)

    monkeypatch.setattr(
        "scripts.download_languagetool_jre.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr=""),
    )

    assert verify_installation(binaries_dir) is False


def test_verify_installation_rejects_small_languagetool_jar(monkeypatch, tmp_path: Path):
    binaries_dir, _java_bin, lt_jar = _create_embedded_layout(tmp_path)
    lt_jar.write_bytes(b"jar")

    monkeypatch.setattr(
        "scripts.download_languagetool_jre.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="", stderr='openjdk version "21"'
        ),
    )

    assert verify_installation(binaries_dir) is False
