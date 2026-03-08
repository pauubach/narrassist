from pathlib import Path

import subprocess

from scripts.smoke_desktop_app import (
    candidate_artifact_paths,
    candidate_binary_paths,
    candidate_app_bundle_binaries,
    discover_artifact,
    discover_binary,
    find_windows_installed_binary,
    is_ready_health_payload,
    run_macos_dmg_smoke,
    run_windows_installer_smoke,
)


def test_is_ready_health_payload_requires_backend_loaded_when_present():
    assert is_ready_health_payload({"backend_loaded": True}) is True
    assert is_ready_health_payload({"backend_loaded": False}) is False
    assert is_ready_health_payload({"ready": True}) is True
    assert is_ready_health_payload({"ready": False}) is False
    assert is_ready_health_payload({"status": "ok"}) is True


def test_discover_binary_prefers_existing_release_binary(tmp_path: Path):
    release_dir = tmp_path / "src-tauri" / "target" / "release"
    release_dir.mkdir(parents=True)
    binary = release_dir / "narrative-assistant.exe"
    binary.write_bytes(b"stub")

    assert discover_binary(tmp_path) == binary


def test_candidate_binary_paths_includes_windows_release_paths(tmp_path: Path):
    paths = candidate_binary_paths(tmp_path)
    expected = tmp_path / "src-tauri" / "target" / "release" / "narrative-assistant.exe"
    assert expected in paths


def test_candidate_artifact_paths_include_windows_nsis(tmp_path: Path):
    installer_dir = tmp_path / "src-tauri" / "target" / "release" / "bundle" / "nsis"
    installer_dir.mkdir(parents=True)
    installer = installer_dir / "Narrative-Assistant-Setup.exe"
    installer.write_bytes(b"stub")

    paths = candidate_artifact_paths(tmp_path, "windows-installer")

    assert installer in paths
    assert discover_artifact(tmp_path, "windows-installer") == installer


def test_candidate_artifact_paths_include_macos_dmg(tmp_path: Path):
    dmg_dir = tmp_path / "src-tauri" / "target" / "release" / "bundle" / "dmg"
    dmg_dir.mkdir(parents=True)
    dmg = dmg_dir / "Narrative Assistant_0.11.12_aarch64.dmg"
    dmg.write_bytes(b"stub")

    paths = candidate_artifact_paths(tmp_path, "macos-dmg")

    assert dmg in paths
    assert discover_artifact(tmp_path, "macos-dmg") == dmg


def test_candidate_app_bundle_binaries_lists_bundle_executable(tmp_path: Path):
    app_dir = tmp_path / "Narrative Assistant.app" / "Contents" / "MacOS"
    app_dir.mkdir(parents=True)
    executable = app_dir / "Narrative Assistant"
    executable.write_bytes(b"stub")

    assert candidate_app_bundle_binaries(app_dir.parent.parent) == [executable]


def test_find_windows_installed_binary_prefers_main_executable(tmp_path: Path):
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    binary = install_dir / "Narrative Assistant.exe"
    binary.write_bytes(b"stub")
    uninstaller = install_dir / "uninstall.exe"
    uninstaller.write_bytes(b"stub")

    assert find_windows_installed_binary(install_dir) == binary


def test_run_windows_installer_smoke_installs_runs_and_cleans(monkeypatch, tmp_path: Path):
    installer = tmp_path / "Narrative-Assistant-Setup.exe"
    installer.write_bytes(b"stub")
    calls: list[list[str]] = []
    ran_binary: list[Path] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[0] == str(installer):
            install_arg = next(part for part in command if str(part).startswith("/D="))
            install_dir = Path(str(install_arg)[3:])
            install_dir.mkdir(parents=True, exist_ok=True)
            (install_dir / "Narrative Assistant.exe").write_bytes(b"app")
            (install_dir / "uninstall.exe").write_bytes(b"uninstall")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("scripts.smoke_desktop_app.subprocess.run", fake_run)
    monkeypatch.setattr(
        "scripts.smoke_desktop_app.run_smoke",
        lambda binary, **kwargs: ran_binary.append(binary),
    )

    run_windows_installer_smoke(
        installer=installer,
        repo_root=tmp_path,
        health_url="http://127.0.0.1:8008/api/health",
        timeout_seconds=5,
        stable_checks=1,
    )

    assert ran_binary == [tmp_path / ".smoke-install" / "Narrative Assistant.exe"]
    assert any(command[0] == str(installer) for command in calls)
    assert any("uninstall.exe" in command[0].lower() for command in calls)
    assert not (tmp_path / ".smoke-install").exists()


def test_run_macos_dmg_smoke_mounts_runs_and_detaches(monkeypatch, tmp_path: Path):
    dmg = tmp_path / "Narrative Assistant.dmg"
    dmg.write_bytes(b"stub")
    calls: list[list[str]] = []
    ran_binary: list[Path] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[:2] == ["hdiutil", "attach"]:
            mount_dir = Path(command[-1])
            executable = mount_dir / "Narrative Assistant.app" / "Contents" / "MacOS" / "Narrative Assistant"
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"app")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("scripts.smoke_desktop_app.subprocess.run", fake_run)
    monkeypatch.setattr(
        "scripts.smoke_desktop_app.run_smoke",
        lambda binary, **kwargs: ran_binary.append(binary),
    )

    run_macos_dmg_smoke(
        dmg_path=dmg,
        repo_root=tmp_path,
        health_url="http://127.0.0.1:8008/api/health",
        timeout_seconds=5,
        stable_checks=1,
    )

    expected_binary = (
        tmp_path
        / ".smoke-dmg-mount"
        / "Narrative Assistant.app"
        / "Contents"
        / "MacOS"
        / "Narrative Assistant"
    )
    assert ran_binary == [expected_binary]
    assert any(command[:2] == ["hdiutil", "attach"] for command in calls)
    assert any(command[:2] == ["hdiutil", "detach"] for command in calls)
    assert not (tmp_path / ".smoke-dmg-mount").exists()
