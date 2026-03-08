#!/usr/bin/env python3
"""
Smoke test reproducible para la app desktop Tauri ya construida.

Objetivo:
- lanzar el binario desktop
- esperar a que el backend local responda en /api/health
- exigir readiness real si el payload expone backend_loaded
- finalizar la app y devolver codigo no cero si falla cualquier paso

No sustituye tests sobre instalador/DMG, pero elimina la dependencia de
validacion manual para el arranque basico de una build local o de CI.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_HEALTH_URL = "http://127.0.0.1:8008/api/health"
DEFAULT_TIMEOUT_SECONDS = 90.0
DEFAULT_STABLE_CHECKS = 2


def is_ready_health_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if "backend_loaded" in payload:
        return bool(payload.get("backend_loaded"))
    if "ready" in payload:
        return bool(payload.get("ready"))
    return True


def candidate_binary_paths(repo_root: Path) -> Iterable[Path]:
    product_variants = [
        "narrative-assistant",
        "Narrative Assistant",
    ]

    release_roots = [
        repo_root / "src-tauri" / "target" / "release",
        *sorted((repo_root / "src-tauri" / "target").glob("*-windows-msvc/release")),
        *sorted((repo_root / "src-tauri" / "target").glob("*-apple-darwin/release")),
    ]

    for root in release_roots:
        for name in product_variants:
            yield root / f"{name}.exe"
            yield root / name

        bundle_root = root / "bundle"
        if bundle_root.exists():
            for app_bundle in bundle_root.rglob("*.app"):
                macos_dir = app_bundle / "Contents" / "MacOS"
                if macos_dir.exists():
                    for candidate in macos_dir.iterdir():
                        if candidate.is_file():
                            yield candidate


def discover_binary(repo_root: Path) -> Path:
    for candidate in candidate_binary_paths(repo_root):
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No se encontro binario desktop construido. Usa --binary o construye la app primero."
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test del binario desktop Tauri")
    parser.add_argument("--binary", type=Path, help="Ruta explicita al binario desktop")
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
    binary = args.binary.resolve() if args.binary else discover_binary(repo_root)

    print(f"[smoke] Binario: {binary}")
    print(f"[smoke] Health: {args.health_url}")

    try:
        run_smoke(
            binary=binary,
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
