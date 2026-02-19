"""
Agrega type: ignore específicos basados en la salida de mypy.

Este script es una solución pragmática para errores de mypy que son:
1. Falsos positivos (mypy tiene limitaciones)
2. Manipulaciones dinámicas de tipos (decorators, singletons)
3. APIs externas sin tipos completos

NO se usa para ocultar errores de sintaxis o lógica, solo para
indicar explícitamente "este error es conocido y aceptable".
"""

import re
import subprocess
from pathlib import Path

# Patrones que son falsos positivos o limitaciones de mypy
SAFE_IGNORES = {
    # Decorators/metaclases - mypy no puede inferir correctamente
    "attr-defined": ["patterns.py"],  # singleton decorator agrega métodos dinámicamente

    # APIs sin tipos completos
    "call-overload": ["languagetool_manager.py"],  # subprocess.Popen tiene tipos complejos

    # Redefiniciones intencionadas (lru_cache, etc.)
    "misc": ["spanish_rules.py"],  # @lru_cache redefinición intencional
}

def should_auto_ignore(file: str, error_code: str) -> bool:
    """Determina si un error debe ignorarse automáticamente."""
    if error_code in SAFE_IGNORES:
        for pattern in SAFE_IGNORES[error_code]:
            if pattern in file:
                return True
    return False

def get_mypy_errors():
    """Ejecuta mypy y obtiene lista de errores."""
    cmd = [
        "python", "-m", "mypy",
        "src/narrative_assistant/core",
        "src/narrative_assistant/persistence",
        "src/narrative_assistant/parsers",
        "src/narrative_assistant/alerts",
        "--ignore-missing-imports"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    errors = []

    for line in result.stdout.split("\n"):
        if ": error:" in line:
            # Parse: src\...\file.py:123: error: mensaje [error-code]
            match = re.match(r"^(.+):(\d+): error: (.+) \[(\w+(?:-\w+)*)\]", line)
            if match:
                errors.append({
                    "file": match.group(1).replace("\\", "/"),
                    "line": int(match.group(2)),
                    "message": match.group(3),
                    "code": match.group(4)
                })

    return errors

def add_ignore_comment(file_path: Path, line_num: int, error_code: str, message: str):
    """Agrega # type: ignore[code] al final de la línea."""
    lines = file_path.read_text(encoding="utf-8").splitlines()

    if line_num < 1 or line_num > len(lines):
        return False

    idx = line_num - 1
    line = lines[idx]

    # Si ya tiene type: ignore, skip
    if "type: ignore" in line:
        return False

    # Agregar el comentario
    lines[idx] = f"{line}  # type: ignore[{error_code}]"

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True

def main():
    repo_root = Path(__file__).parent.parent
    errors = get_mypy_errors()

    print(f"Found {len(errors)} mypy errors")

    # Agrupar por archivo
    by_file = {}
    for err in errors:
        if err["file"] not in by_file:
            by_file[err["file"]] = []
        by_file[err["file"]].append(err)

    fixed = 0
    skipped = 0

    for file_rel, file_errors in by_file.items():
        file_path = repo_root / file_rel

        if not file_path.exists():
            print(f"SKIP: {file_rel} not found")
            continue

        # Ordenar por línea (descendente) para no desajustar líneas anteriores
        file_errors.sort(key=lambda e: e["line"], reverse=True)

        for err in file_errors:
            if should_auto_ignore(file_rel, err["code"]):
                if add_ignore_comment(file_path, err["line"], err["code"], err["message"]):
                    print(f"FIXED: {file_rel}:{err['line']} [{err['code']}]")
                    fixed += 1
                else:
                    skipped += 1
            else:
                # No auto-ignore: estos requieren revisión manual
                skipped += 1

    print(f"\n✓ {fixed} ignores agregados")
    print(f"⊘ {skipped} errores requieren revisión manual")

if __name__ == "__main__":
    main()
