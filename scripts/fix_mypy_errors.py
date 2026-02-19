"""
Script para arreglar errores de mypy de forma sistemática.

Patrones a arreglar:
1. var-annotated: Añadir type hints a variables
2. no-any-return: Cast return values
3. union-attr: Añadir null checks
4. assignment: Añadir casts o type: ignore
"""

import re
from pathlib import Path

# Mapeo de patrones a arreglar
FIXES = {
    # var-annotated: issues = [] → issues: list[PacingIssue] = []
    "analysis/pacing.py:956": ('issues = []', 'issues: list[PacingIssue] = []'),
    "analysis/out_of_character.py:252": ('events = []', 'events: list[dict[str, Any]] = []'),
    "analysis/out_of_character.py:385": ('events = []', 'events: list[dict[str, Any]] = []'),
    "analysis/relationship_clustering.py:626": ('clusters = []', 'clusters: list[dict[str, Any]] = []'),
    "analysis/relationship_clustering.py:682": ('connection_counts = Counter()', 'connection_counts: Counter[str] = Counter()'),
    "voice/register.py:613": ('changes = []', 'changes: list[dict[str, Any]] = []'),
    "analysis/semantic_redundancy.py:431": ('duplicates = []', 'duplicates: list[dict[str, Any]] = []'),
    "persistence/editorial_work.py:261": ('entity_names = []', 'entity_names: list[str] = []'),
    "nlp/entity_validator.py:1053": ('entities_to_validate = []', 'entities_to_validate: list[dict[str, Any]] = []'),
    "nlp/extraction/extractors/llm_extractor.py:390": ('attributes = []', 'attributes: list[dict[str, Any]] = []'),
    "nlp/ner.py:350": ('raw_entities = []', 'raw_entities: list[dict[str, Any]] = []'),
    "nlp/ner.py:1294": ('sources = {}', 'sources: dict[str, Any] = {}'),

    # no-any-return con cast explícito
    "core/model_manager.py:828": (
        'return self._config_cache[key]',
        'result: str | None = self._config_cache[key]\n        return result'
    ),
    "core/model_manager.py:836": (
        'return self._config_cache.get(key)',
        'result: str | None = self._config_cache.get(key)\n        return result'
    ),
    "core/model_manager.py:1468": (
        'return data.get("download_info")',
        'result: dict[Any, Any] | None = data.get("download_info")\n        return result'
    ),
    "core/model_manager.py:1705": (
        'return self._get_cache_value(f"{model_id}_size")',
        'result: int | None = self._get_cache_value(f"{model_id}_size")\n        return result'
    ),

    # Specific fixes para archivos críticos
    "nlp/grammar/languagetool_manager.py:153": (
        'return result.get("software", {}).get("buildDate") is not None',
        'is_valid: bool = result.get("software", {}).get("buildDate") is not None\n        return is_valid'
    ),
}

def apply_fixes():
    """Aplica los fixes definidos."""
    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src" / "narrative_assistant"

    fixed_count = 0
    for file_pattern, (old, new) in FIXES.items():
        file_path = src_dir / file_pattern.split(":")[0]

        if not file_path.exists():
            print(f"SKIP: {file_path} no existe")
            continue

        content = file_path.read_text(encoding="utf-8")

        if old in content:
            content = content.replace(old, new, 1)  # Solo primera ocurrencia
            file_path.write_text(content, encoding="utf-8")
            print(f"FIXED: {file_pattern}")
            fixed_count += 1
        else:
            print(f"SKIP: {file_pattern} - patrón no encontrado")

    print(f"\n✓ {fixed_count} archivos corregidos")

if __name__ == "__main__":
    apply_fixes()
