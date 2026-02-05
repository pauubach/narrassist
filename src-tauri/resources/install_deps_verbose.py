#!/usr/bin/env python3
"""
Instalador de dependencias con feedback verbose.
Muestra progreso detallado para cada paquete.
"""

import subprocess
import sys
import os
import re
import time
from pathlib import Path

# Paquetes principales en orden de instalación
# (nombre, tamaño aproximado en MB)
MAIN_PACKAGES = [
    ("numpy", 15),
    ("scipy", 40),
    ("pandas", 50),
    ("scikit-learn", 30),
    ("torch", 900),
    ("spacy", 30),
    ("transformers", 50),
    ("sentence-transformers", 20),
    ("fastapi", 5),
    ("uvicorn", 5),
]

def print_progress(current: int, total: int, package: str, status: str,
                   downloaded_mb: float = 0, total_mb: float = 0, speed_mbps: float = 0):
    """Imprime progreso en formato parseable por NSIS."""
    percent = int((current / total) * 100) if total > 0 else 0

    # Formato: PROGRESS|percent|current|total|package|status|downloaded|total_size|speed
    if downloaded_mb > 0 and total_mb > 0:
        print(f"PROGRESS|{percent}|{current}|{total}|{package}|{status}|{downloaded_mb:.1f}|{total_mb:.1f}|{speed_mbps:.1f}")
    else:
        print(f"PROGRESS|{percent}|{current}|{total}|{package}|{status}|||")
    sys.stdout.flush()


def parse_pip_output(line: str) -> dict:
    """Parsea la salida de pip para extraer información de progreso."""
    result = {}

    # Detectar descarga: "Downloading package-1.0.0.whl (123.4 MB)"
    download_match = re.search(r'Downloading\s+(\S+)\s+\(([0-9.]+)\s*(MB|KB|kB)\)', line)
    if download_match:
        result['downloading'] = download_match.group(1)
        size = float(download_match.group(2))
        unit = download_match.group(3).upper()
        if unit == 'KB':
            size /= 1024
        result['total_mb'] = size

    # Detectar progreso: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100.0/100.0 MB 15.2 MB/s"
    progress_match = re.search(r'([0-9.]+)/([0-9.]+)\s*(MB|KB)\s+([0-9.]+)\s*(MB|KB)/s', line)
    if progress_match:
        result['downloaded_mb'] = float(progress_match.group(1))
        result['total_mb'] = float(progress_match.group(2))
        result['speed_mbps'] = float(progress_match.group(4))
        if progress_match.group(5).upper() == 'KB':
            result['speed_mbps'] /= 1024

    # Detectar instalación: "Installing collected packages: torch, numpy"
    if 'Installing collected packages' in line:
        result['installing'] = True
        packages_match = re.search(r'Installing collected packages:\s+(.+)', line)
        if packages_match:
            result['packages'] = [p.strip() for p in packages_match.group(1).split(',')]

    # Detectar completado: "Successfully installed"
    if 'Successfully installed' in line:
        result['completed'] = True

    return result


def install_package(package: str, python_exe: str, current: int, total: int) -> bool:
    """Instala un paquete con feedback de progreso."""
    print_progress(current, total, package, "Descargando")

    env = os.environ.copy()
    env['PIP_PROGRESS_BAR'] = 'on'

    proc = subprocess.Popen(
        [python_exe, "-m", "pip", "install", package,
         "--progress-bar", "on", "--no-cache-dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    last_update = time.time()
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue

        parsed = parse_pip_output(line)

        if 'downloaded_mb' in parsed:
            print_progress(
                current, total, package, "Descargando",
                parsed.get('downloaded_mb', 0),
                parsed.get('total_mb', 0),
                parsed.get('speed_mbps', 0)
            )
            last_update = time.time()
        elif 'installing' in parsed:
            print_progress(current, total, package, "Instalando")
        elif 'completed' in parsed:
            print_progress(current, total, package, "Completado")

        # Actualizar cada 2 segundos aunque no haya cambios
        if time.time() - last_update > 2:
            print_progress(current, total, package, "Procesando")
            last_update = time.time()

    proc.wait()
    return proc.returncode == 0


def install_from_requirements(requirements_path: str, python_exe: str) -> bool:
    """Instala desde requirements.txt con progreso."""
    if not os.path.exists(requirements_path):
        print(f"ERROR|No se encontró {requirements_path}")
        return False

    # Leer y contar paquetes
    with open(requirements_path, 'r') as f:
        packages = [line.strip() for line in f
                   if line.strip() and not line.startswith('#') and not line.startswith('-')]

    total = len(packages)
    print(f"INFO|Instalando {total} paquetes desde {requirements_path}")

    # Instalar todos de una vez pero con progreso
    print_progress(0, total, "todos", "Iniciando")

    env = os.environ.copy()
    env['PIP_PROGRESS_BAR'] = 'on'

    proc = subprocess.Popen(
        [python_exe, "-m", "pip", "install", "-r", requirements_path,
         "--progress-bar", "on"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    current_pkg = 0
    current_name = "preparando"

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue

        parsed = parse_pip_output(line)

        if 'downloading' in parsed:
            current_name = parsed['downloading'].split('-')[0]  # Extraer nombre del paquete
            current_pkg = min(current_pkg + 1, total)
            print_progress(
                current_pkg, total, current_name, "Descargando",
                0, parsed.get('total_mb', 0), 0
            )
        elif 'downloaded_mb' in parsed:
            print_progress(
                current_pkg, total, current_name, "Descargando",
                parsed.get('downloaded_mb', 0),
                parsed.get('total_mb', 0),
                parsed.get('speed_mbps', 0)
            )
        elif 'installing' in parsed:
            print_progress(current_pkg, total, current_name, "Instalando")
        elif 'completed' in parsed:
            print_progress(total, total, "todos", "Completado")

    proc.wait()
    return proc.returncode == 0


def main():
    """Punto de entrada principal."""
    import argparse
    parser = argparse.ArgumentParser(description='Instalador de dependencias con progreso')
    parser.add_argument('--python', default=sys.executable, help='Ruta al ejecutable de Python')
    parser.add_argument('--requirements', help='Archivo requirements.txt')
    parser.add_argument('--package', help='Paquete individual a instalar')
    args = parser.parse_args()

    print("INFO|Iniciando instalación de dependencias...")
    print(f"INFO|Python: {args.python}")

    success = True

    if args.requirements:
        success = install_from_requirements(args.requirements, args.python)
    elif args.package:
        success = install_package(args.package, args.python, 1, 1)
    else:
        # Instalar paquetes principales uno por uno
        total = len(MAIN_PACKAGES)
        for i, (pkg, _) in enumerate(MAIN_PACKAGES, 1):
            if not install_package(pkg, args.python, i, total):
                print(f"ERROR|Fallo al instalar {pkg}")
                success = False
                break

    if success:
        print("INFO|Instalación completada exitosamente")
        return 0
    else:
        print("ERROR|La instalación falló")
        return 1


if __name__ == "__main__":
    sys.exit(main())
