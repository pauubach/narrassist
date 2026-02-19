#!/usr/bin/env python3
"""
Script para eliminar type: ignore innecesarios en api-server.
Aplica las mismas transformaciones que ya hicimos en src/.
"""

import re
from pathlib import Path


def clean_type_ignores(file_path: Path) -> tuple[int, int]:
    """
    Limpiar type: ignore de un archivo.

    Returns:
        (ignores_removed, lines_changed)
    """
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Contar ignores originales
    original_ignores = content.count('type: ignore')

    # Patrón 1: Eliminar type: ignore de líneas que no necesitan anotación
    # - attr-defined en métodos de repositorio (son dinámicos pero válidos)
    # - arg-type en IDs (int es obvio)
    # - no-any-return en returns simples
    # - var-annotated en dict vacíos (Python puede inferir)

    # Eliminar comments de type: ignore al final de línea
    patterns = [
        # attr-defined en repositorio calls
        (r'(\w+_repo\.\w+\([^)]*\))\s*# type: ignore\[attr-defined\]', r'\1'),
        # arg-type en IDs
        (r'(id=\w+\.id)\s*# type: ignore\[arg-type\]', r'\1'),
        # no-any-return en returns
        (r'(return \w+\.\w+)\s*# type: ignore\[no-any-return\]', r'\1'),
        # var-annotated en dicts vacíos
        (r'(\w+ = \{\})\s*# type: ignore\[var-annotated\]', r'\1'),
        # union-attr (ya resuelto con getattr)
        (r'\s*# type: ignore\[union-attr\]', ''),
        # return-value genérico
        (r'\s*# type: ignore\[return-value\]', ''),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    # Contar ignores finales
    final_ignores = content.count('type: ignore')

    # Calcular cambios
    ignores_removed = original_ignores - final_ignores
    lines_changed = len([line for line in content.split('\n') if line != original.split('\n')[content.split('\n').index(line)] if line in content.split('\n')])

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return ignores_removed, 1

    return 0, 0


def main():
    api_server = Path('api-server')
    total_removed = 0
    files_changed = 0

    for py_file in api_server.rglob('*.py'):
        removed, changed = clean_type_ignores(py_file)
        if removed > 0:
            total_removed += removed
            files_changed += changed
            print(f"✓ {py_file.relative_to(api_server)}: -{removed} ignores")

    print(f"\n📊 Total: {total_removed} type: ignore eliminados en {files_changed} archivos")


if __name__ == '__main__':
    main()
