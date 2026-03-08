from pathlib import Path

from scripts.smoke_desktop_app import candidate_binary_paths, discover_binary, is_ready_health_payload


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
    paths = list(candidate_binary_paths(tmp_path))
    expected = tmp_path / "src-tauri" / "target" / "release" / "narrative-assistant.exe"
    assert expected in paths
