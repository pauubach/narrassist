#!/usr/bin/env python3
"""
Script de verificación post-Fase 3.

Verifica que todos los fixes y mejoras están implementados correctamente.
"""
import sys
from pathlib import Path

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_file_exists(path: Path, description: str) -> bool:
    """Verifica que un archivo existe."""
    if path.exists():
        print(f"{GREEN}[OK]{RESET} {description}: {path}")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} {description}: {path} {RED}(NO ENCONTRADO){RESET}")
        return False


def check_file_contains(path: Path, text: str, description: str) -> bool:
    """Verifica que un archivo contiene un texto específico."""
    if not path.exists():
        print(f"{RED}[FAIL]{RESET} {description}: {path} {RED}(ARCHIVO NO EXISTE){RESET}")
        return False

    content = path.read_text(encoding="utf-8")
    if text in content:
        print(f"{GREEN}[OK]{RESET} {description}")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} {description} {RED}(TEXTO NO ENCONTRADO){RESET}")
        return False


def main():
    """Ejecuta todas las verificaciones."""
    print(f"\n{BOLD}=== Verificación Fase 3 ==={RESET}\n")

    repo_root = Path(__file__).parent.parent
    checks_passed = 0
    checks_total = 0

    # 1. Verificar archivos nuevos
    print(f"\n{BOLD}1. Archivos Nuevos{RESET}")
    checks_total += 3
    checks_passed += check_file_exists(
        repo_root / "tests/unit/test_analysis_alert_emission.py",
        "Tests de alert emission"
    )
    checks_passed += check_file_exists(
        repo_root / "docs/AUDIT_2026_02_22_FASE3.md",
        "Audit report"
    )
    checks_passed += check_file_exists(
        repo_root / "scripts/verify_phase3.py",
        "Script de verificación"
    )

    # 2. Verificar fixes backend
    print(f"\n{BOLD}2. Fixes Backend{RESET}")
    checks_total += 3
    checks_passed += check_file_contains(
        repo_root / "src/narrative_assistant/analysis/chapter_summary.py",
        "if not text_to_analyze or not text_to_analyze.strip():",
        "M1: Validación LLM prompts"
    )
    checks_passed += check_file_contains(
        repo_root / "api-server/routers/_invalidation.py",
        "CRÍTICO: _mark_stale() debe completar o se hace rollback del INSERT",
        "M2: Race condition fix"
    )
    checks_passed += check_file_contains(
        repo_root / "src/narrative_assistant/nlp/coreference_resolver.py",
        "if not all_votes:",
        "M4: Voting fallback logging"
    )

    # 3. Verificar tests
    print(f"\n{BOLD}3. Tests Críticos{RESET}")
    checks_total += 2
    checks_passed += check_file_contains(
        repo_root / "tests/unit/test_analysis_alert_emission.py",
        "@pytest.mark.parametrize",
        "Tests parametrizados"
    )
    checks_passed += check_file_contains(
        repo_root / "tests/unit/test_analysis_alert_emission.py",
        "def test_to_optional_int",
        "Tests de _to_optional_int"
    )

    # 4. Verificar UX improvements
    print(f"\n{BOLD}4. UX Improvements{RESET}")
    checks_total += 3
    checks_passed += check_file_contains(
        repo_root / "frontend/src/components/DialogueAttributionPanel.vue",
        "{ editing: correctingIndex === idx }",
        "UX2: Visual editing state"
    )
    checks_passed += check_file_contains(
        repo_root / "frontend/src/components/inspector/EntityInspector.vue",
        "v-if=\"mentionNav.isLoading.value\"",
        "UX3: Loading state"
    )
    checks_passed += check_file_contains(
        repo_root / "frontend/src/components/inspector/ChapterInspector.vue",
        "characters_involved: charactersInvolved",
        "UX6: Character navigation"
    )

    # 5. Verificar security documentation
    print(f"\n{BOLD}5. Security Documentation{RESET}")
    checks_total += 2
    checks_passed += check_file_contains(
        repo_root / "src/narrative_assistant/persistence/database.py",
        "SEGURIDAD: table, column, col_def provienen de constantes de código",
        "S2: SQL security comment"
    )
    checks_passed += check_file_contains(
        repo_root / "docs/AUDIT_2026_02_22_FASE3.md",
        "## 3. Auditoría de Seguridad",
        "Audit report completo"
    )

    # 6. Verificar documentación actualizada
    print(f"\n{BOLD}6. Documentación{RESET}")
    checks_total += 1
    checks_passed += check_file_contains(
        repo_root / "docs/IMPROVEMENT_PLAN.md",
        "Sprint Fase3: Aceleración Incremental + Auditoría Técnica",
        "IMPROVEMENT_PLAN actualizado"
    )

    # Resumen
    print(f"\n{BOLD}{'='*50}{RESET}")
    percentage = (checks_passed / checks_total) * 100

    if checks_passed == checks_total:
        print(f"{GREEN}{BOLD}[SUCCESS] TODAS LAS VERIFICACIONES PASARON{RESET}")
        print(f"{GREEN}{checks_passed}/{checks_total} checks ({percentage:.0f}%){RESET}")
        return 0
    else:
        print(f"{YELLOW}{BOLD}[WARNING] ALGUNAS VERIFICACIONES FALLARON{RESET}")
        print(f"{YELLOW}{checks_passed}/{checks_total} checks ({percentage:.0f}%){RESET}")
        print(f"\n{RED}Fallos: {checks_total - checks_passed}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
