#!/usr/bin/env python3
"""
Smoke test reproducible para la app desktop Tauri ya construida o empaquetada.

Modos soportados:
- binary: ejecuta el binario Tauri ya compilado
- windows-installer: instala el NSIS final en un directorio temporal y arranca la app instalada
- macos-dmg: monta el DMG final y arranca la app desde el bundle montado

Objetivo:
- lanzar la app desktop
- esperar a que el backend local responda en /api/health
- exigir readiness real si el payload expone backend_loaded
- finalizar la app y devolver codigo no cero si falla cualquier paso
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_HEALTH_URL = "http://127.0.0.1:8008/api/health"
DEFAULT_TIMEOUT_SECONDS = 90.0
DEFAULT_STABLE_CHECKS = 2

WINDOWS_BINARY_NAMES = (
    "Narrative Assistant.exe",
    "narrative-assistant.exe",
)


def is_ready_health_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if "backend_loaded" in payload:
        return bool(payload.get("backend_loaded"))
    if "ready" in payload:
        return bool(payload.get("ready"))
    return True


def candidate_binary_paths(repo_root: Path) -> list[Path]:
    product_variants = [
        "narrative-assistant",
        "Narrative Assistant",
    ]

    release_roots = [
        repo_root / "src-tauri" / "target" / "release",
        *sorted((repo_root / "src-tauri" / "target").glob("*-windows-msvc/release")),
        *sorted((repo_root / "src-tauri" / "target").glob("*-apple-darwin/release")),
    ]

    candidates: list[Path] = []
    for root in release_roots:
        for name in product_variants:
            candidates.append(root / f"{name}.exe")
            candidates.append(root / name)

        bundle_root = root / "bundle"
        if bundle_root.exists():
            for app_bundle in bundle_root.rglob("*.app"):
                candidates.extend(candidate_app_bundle_binaries(app_bundle))

    return candidates


def candidate_installer_paths(repo_root: Path, mode: str) -> list[Path]:
    if mode == "windows-installer":
        patterns = [
            "src-tauri/target/release/bundle/nsis/*.exe",
            "src-tauri/target/*-windows-msvc/release/bundle/nsis/*.exe",
        ]
    elif mode == "macos-dmg":
        patterns = [
            "src-tauri/target/release/bundle/dmg/*.dmg",
            "src-tauri/target/*-apple-darwin/release/bundle/dmg/*.dmg",
        ]
    else:
        raise ValueError(f"Modo de artefacto no soportado: {mode}")

    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(sorted(repo_root.glob(pattern)))
    return matches


def candidate_artifact_paths(repo_root: Path, mode: str) -> list[Path]:
    """Alias legacy mantenido para tests y llamadas antiguas."""
    return candidate_installer_paths(repo_root, mode)


def candidate_app_bundle_binaries(app_bundle: Path) -> list[Path]:
    macos_dir = app_bundle / "Contents" / "MacOS"
    if not macos_dir.exists():
        return []
    return [candidate for candidate in macos_dir.iterdir() if candidate.is_file()]


def discover_binary(repo_root: Path) -> Path:
    for candidate in candidate_binary_paths(repo_root):
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No se encontro binario desktop construido. Usa --binary o construye la app primero."
    )


def discover_artifact(repo_root: Path, mode: str) -> Path:
    for candidate in candidate_installer_paths(repo_root, mode):
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"No se encontro artefacto final para {mode}. Usa --artifact o construye la app primero."
    )


def poll_health(url: str, timeout_seconds: float, stable_checks: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    consecutive_ready = 0
    last_error: str | None = None

    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=5) as response:  # nosec B310 - URL local controlada
                if response.status != 200:
                    last_error = f"HTTP {response.status}"
                    time.sleep(1)
                    continue

                body = response.read()
                payload = json.loads(body.decode("utf-8", errors="replace"))
                if is_ready_health_payload(payload):
                    consecutive_ready += 1
                    if consecutive_ready >= stable_checks:
                        return
                else:
                    consecutive_ready = 0
                    last_error = "health OK pero backend no listo"
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            consecutive_ready = 0
            last_error = str(exc)

        time.sleep(1)

    raise TimeoutError(
        f"El backend local no estuvo listo tras {timeout_seconds:.0f}s. Ultimo error: {last_error or 'sin detalle'}"
    )


def terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def run_smoke(binary: Path, health_url: str, timeout_seconds: float, stable_checks: int) -> None:
    process = subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        poll_health(health_url, timeout_seconds=timeout_seconds, stable_checks=stable_checks)
    finally:
        terminate_process_tree(process)


def find_windows_installed_binary(install_dir: Path) -> Path:
    for name in WINDOWS_BINARY_NAMES:
        candidate = install_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate

    for candidate in sorted(install_dir.rglob("*.exe")):
        if candidate.name.lower().startswith("uninstall"):
            continue
        return candidate

    raise FileNotFoundError(
        f"No se encontro ejecutable instalado en {install_dir}"
    )


def wait_for_file_stable(path: Path, timeout_seconds: float = 30.0, stable_checks: int = 3) -> None:
    """Espera a que un archivo exista y su tamaño se estabilice varios ciclos."""
    deadline = time.monotonic() + timeout_seconds
    last_size: int | None = None
    consecutive_stable = 0

    while time.monotonic() < deadline:
        if path.exists() and path.is_file():
            size = path.stat().st_size
            if size > 0 and size == last_size:
                consecutive_stable += 1
                if consecutive_stable >= stable_checks:
                    return
            else:
                consecutive_stable = 0
                last_size = size
        time.sleep(1)

    raise TimeoutError(f"El archivo instalado no quedo estable a tiempo: {path}")


def find_windows_uninstaller(install_dir: Path) -> Path | None:
    for candidate in sorted(install_dir.rglob("uninstall*.exe")):
        if candidate.is_file():
            return candidate
    return None


def run_windows_installer_smoke(
    installer: Path,
    repo_root: Path,
    health_url: str,
    timeout_seconds: float,
    stable_checks: int,
) -> None:
    install_dir = repo_root / ".smoke-install"
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [str(installer), "/S", f"/D={install_dir}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        binary = find_windows_installed_binary(install_dir)
        wait_for_file_stable(binary)
        run_smoke(binary, health_url=health_url, timeout_seconds=timeout_seconds, stable_checks=stable_checks)
    finally:
        uninstaller = find_windows_uninstaller(install_dir)
        if uninstaller is not None:
            subprocess.run(
                [str(uninstaller), "/S"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        shutil.rmtree(install_dir, ignore_errors=True)


def find_macos_bundle_binary(mount_dir: Path) -> Path:
    app_bundles = sorted(mount_dir.glob("*.app"))
    for app_bundle in app_bundles:
        candidates = candidate_app_bundle_binaries(app_bundle)
        if candidates:
            return candidates[0]
    raise FileNotFoundError(f"No se encontro .app ejecutable dentro de {mount_dir}")


def run_macos_dmg_smoke(
    dmg_path: Path,
    repo_root: Path,
    health_url: str,
    timeout_seconds: float,
    stable_checks: int,
) -> None:
    mount_dir = repo_root / ".smoke-dmg-mount"
    if mount_dir.exists():
        shutil.rmtree(mount_dir, ignore_errors=True)
    mount_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "hdiutil",
                "attach",
                str(dmg_path),
                "-nobrowse",
                "-readonly",
                "-mountpoint",
                str(mount_dir),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        binary = find_macos_bundle_binary(mount_dir)
        run_smoke(binary, health_url=health_url, timeout_seconds=timeout_seconds, stable_checks=stable_checks)
    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount_dir), "-force"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(mount_dir, ignore_errors=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test desktop Tauri (binario o artefacto final)")
    parser.add_argument(
        "--mode",
        choices=["binary", "windows-installer", "macos-dmg"],
        default="binary",
        help="Modo de smoke a ejecutar",
    )
    parser.add_argument("--binary", type=Path, help="Ruta explicita al binario desktop")
    parser.add_argument("--artifact", type=Path, help="Ruta explicita al instalador/DMG final")
    parser.add_argument("--health-url", default=DEFAULT_HEALTH_URL, help="Endpoint de health local")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout total de arranque en segundos",
    )
    parser.add_argument(
        "--stable-checks",
        type=int,
        default=DEFAULT_STABLE_CHECKS,
        help="Numero de respuestas health consecutivas requeridas",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parent.parent

    try:
        if args.mode == "binary":
            binary = args.binary.resolve() if args.binary else discover_binary(repo_root)
            print(f"[smoke] Binario: {binary}")
            print(f"[smoke] Health: {args.health_url}")
            run_smoke(
                binary=binary,
                health_url=args.health_url,
                timeout_seconds=args.timeout,
                stable_checks=args.stable_checks,
            )
        elif args.mode == "windows-installer":
            artifact = args.artifact.resolve() if args.artifact else discover_artifact(repo_root, args.mode)
            print(f"[smoke] Instalador: {artifact}")
            print(f"[smoke] Health: {args.health_url}")
            run_windows_installer_smoke(
                installer=artifact,
                repo_root=repo_root,
                health_url=args.health_url,
                timeout_seconds=args.timeout,
                stable_checks=args.stable_checks,
            )
        else:
            artifact = args.artifact.resolve() if args.artifact else discover_artifact(repo_root, args.mode)
            print(f"[smoke] DMG: {artifact}")
            print(f"[smoke] Health: {args.health_url}")
            run_macos_dmg_smoke(
                dmg_path=artifact,
                repo_root=repo_root,
                health_url=args.health_url,
                timeout_seconds=args.timeout,
                stable_checks=args.stable_checks,
            )
    except Exception as exc:  # pragma: no cover - salida CLI
        print(f"[smoke] ERROR: {exc}", file=sys.stderr)
        return 1

    print("[smoke] OK: arranque desktop verificado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
