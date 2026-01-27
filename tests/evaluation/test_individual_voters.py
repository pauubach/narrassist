# -*- coding: utf-8 -*-
"""
Test individual de cada votante para ortografía.

Ejecuta cada votante de forma aislada para medir:
- Precisión: TP / (TP + FP) - de los errores que detecta, cuántos son reales
- Recall: TP / (TP + FN) - de los errores reales, cuántos detecta
- F1: Media armónica de precisión y recall

Esto permite identificar fortalezas y debilidades de cada votante
para optimizar el sistema de votación.
"""

import os
from pathlib import Path

# Setup Java 17 BEFORE any imports that might need it
java17_paths = [
    r"C:\Program Files\Microsoft\jdk-17.0.17.10-hotspot",
    r"C:\Program Files\Eclipse Adoptium\jdk-17",
    r"C:\Program Files\Java\jdk-17",
    "/usr/lib/jvm/java-17-openjdk",
]
for java_path in java17_paths:
    if Path(java_path).exists():
        os.environ['JAVA_HOME'] = java_path
        bin_path = f"{java_path}\\bin" if os.name == 'nt' else f"{java_path}/bin"
        os.environ['PATH'] = bin_path + os.pathsep + os.environ.get('PATH', '')
        break

import sys
import logging
from dataclasses import dataclass, field
from typing import Optional
import re
import time

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class VoterTestResult:
    """Resultado de evaluar un votante individual."""
    voter_name: str

    # Contadores
    true_positives: int = 0   # Errores reales detectados correctamente
    false_positives: int = 0  # Palabras correctas marcadas como error
    false_negatives: int = 0  # Errores reales no detectados
    true_negatives: int = 0   # Palabras correctas no marcadas

    # Detalles
    tp_words: list[str] = field(default_factory=list)
    fp_words: list[str] = field(default_factory=list)
    fn_words: list[str] = field(default_factory=list)

    # Timing
    time_seconds: float = 0.0

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    def __str__(self) -> str:
        return (
            f"{self.voter_name}:\n"
            f"  Precision: {self.precision:.1%} ({self.true_positives} TP, {self.false_positives} FP)\n"
            f"  Recall:    {self.recall:.1%} ({self.true_positives} TP, {self.false_negatives} FN)\n"
            f"  F1:        {self.f1:.1%}\n"
            f"  Time:      {self.time_seconds:.2f}s"
        )


def load_gold_standard_errors() -> dict[str, str]:
    """Cargar errores del gold standard de ortografía.

    Returns:
        Dict[error_word, correction]
    """
    # Import from local file
    sys.path.insert(0, str(Path(__file__).parent))
    from gold_standards import GOLD_ERRORES_ORTOGRAFICOS

    errors = {}
    for error in GOLD_ERRORES_ORTOGRAFICOS.orthography_errors:
        errors[error.text.lower()] = error.correction.lower()

    return errors


def load_test_text() -> str:
    """Cargar texto de prueba de ortografía."""
    test_file = Path(__file__).parent.parent.parent / "test_books" / "evaluation_tests" / "prueba_ortografia.txt"

    with open(test_file, 'r', encoding='utf-8') as f:
        return f.read()


def extract_words(text: str) -> list[tuple[str, int, int]]:
    """Extraer palabras del texto con posiciones.

    Returns:
        List of (word, start, end)
    """
    # Ignorar la sección de notas al final
    notes_start = text.find("Notas del autor:")
    if notes_start > 0:
        text = text[:notes_start]

    word_pattern = re.compile(r'\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,})\b')
    words = []

    for match in word_pattern.finditer(text):
        word = match.group(1)
        # Ignorar palabras en mayúsculas (títulos de capítulos)
        if not word.isupper() or len(word) <= 4:
            words.append((word, match.start(), match.end()))

    return words


def evaluate_pyspellchecker_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar PySpellChecker voter."""
    from narrative_assistant.nlp.orthography.voting_checker import PySpellCheckerVoter

    result = VoterTestResult(voter_name="pyspellchecker")

    voter = PySpellCheckerVoter()
    if not voter.is_available:
        logger.warning("PySpellChecker no disponible")
        return result

    start_time = time.time()

    for word, start, end in words:
        vote = voter.check_word(word)
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors

        if vote and vote.is_error:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    return result


def evaluate_hunspell_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar Hunspell (chunspell) voter."""
    from narrative_assistant.nlp.orthography.voting_checker import ChunspellVoter

    result = VoterTestResult(voter_name="hunspell")

    voter = ChunspellVoter()
    if not voter.is_available:
        logger.warning("Hunspell no disponible")
        return result

    start_time = time.time()

    for word, start, end in words:
        vote = voter.check_word(word)
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors

        if vote and vote.is_error:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    return result


def evaluate_symspell_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar SymSpell voter."""
    from narrative_assistant.nlp.orthography.voting_checker import SymSpellVoter

    result = VoterTestResult(voter_name="symspell")

    voter = SymSpellVoter()
    if not voter.is_available:
        logger.warning("SymSpell no disponible")
        return result

    start_time = time.time()

    for word, start, end in words:
        vote = voter.check_word(word)
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors

        if vote and vote.is_error:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    return result


def evaluate_pattern_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar Pattern voter."""
    from narrative_assistant.nlp.orthography.voting_checker import PatternVoter

    result = VoterTestResult(voter_name="patterns")

    voter = PatternVoter()
    if not voter.is_available:
        logger.warning("PatternVoter no disponible")
        return result

    start_time = time.time()

    for word, start, end in words:
        vote = voter.check_word(word)
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors

        if vote and vote.is_error:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    return result


def evaluate_languagetool_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar LanguageTool voter."""
    from narrative_assistant.nlp.orthography.voting_checker import LanguageToolVoter

    result = VoterTestResult(voter_name="languagetool")

    voter = LanguageToolVoter()
    if not voter.is_available:
        logger.warning("LanguageTool no disponible")
        return result

    start_time = time.time()

    # LanguageTool procesa texto completo
    lt_errors = voter.check_text(text)
    lt_error_positions = {(start, end): word for word, start, end, vote in lt_errors}
    lt_error_words = {word.lower() for word, _, _, _ in lt_errors}

    for word, start, end in words:
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors
        is_detected = word_lower in lt_error_words or (start, end) in lt_error_positions

        if is_detected:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    voter.close()
    return result


def evaluate_beto_voter(text: str, words: list, gold_errors: dict) -> VoterTestResult:
    """Evaluar BETO voter (transformer español)."""
    from narrative_assistant.nlp.orthography.voting_checker import BETOVoter

    result = VoterTestResult(voter_name="beto")

    voter = BETOVoter()
    if not voter.is_available:
        logger.warning("BETO no disponible")
        return result

    start_time = time.time()

    # Extraer oraciones como contexto
    sentences = re.split(r'[.!?\n]+', text)
    sentence_map = {}  # word_pos -> sentence
    pos = 0
    for sent in sentences:
        for match in re.finditer(r'\b\w+\b', sent):
            sentence_map[pos + match.start()] = sent
        pos += len(sent) + 1

    for word, start, end in words:
        # Obtener contexto (oración)
        context = sentence_map.get(start, "")
        if not context:
            # Buscar oración que contenga la posición
            for s in sentences:
                if word.lower() in s.lower():
                    context = s
                    break

        vote = voter.check_word(word, context)
        word_lower = word.lower()
        is_gold_error = word_lower in gold_errors

        if vote and vote.is_error:
            if is_gold_error:
                result.true_positives += 1
                result.tp_words.append(word)
            else:
                result.false_positives += 1
                result.fp_words.append(word)
        else:
            if is_gold_error:
                result.false_negatives += 1
                result.fn_words.append(word)
            else:
                result.true_negatives += 1

    result.time_seconds = time.time() - start_time
    return result


def run_individual_voter_tests():
    """Ejecutar tests de todos los votantes individuales."""
    print("=" * 70)
    print("EVALUACIÓN INDIVIDUAL DE VOTANTES - ORTOGRAFÍA")
    print("=" * 70)

    # Cargar datos
    print("\nCargando gold standard y texto de prueba...")
    gold_errors = load_gold_standard_errors()
    text = load_test_text()
    words = extract_words(text)

    print(f"  - {len(gold_errors)} errores en gold standard")
    print(f"  - {len(words)} palabras en el texto")
    print(f"  - Errores gold: {list(gold_errors.keys())[:10]}...")

    # Tests de cada votante
    results = []

    print("\n" + "-" * 70)
    print("1. PySpellChecker")
    print("-" * 70)
    r = evaluate_pyspellchecker_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    print("\n" + "-" * 70)
    print("2. Hunspell")
    print("-" * 70)
    r = evaluate_hunspell_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    print("\n" + "-" * 70)
    print("3. SymSpell")
    print("-" * 70)
    r = evaluate_symspell_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    print("\n" + "-" * 70)
    print("4. Patterns")
    print("-" * 70)
    r = evaluate_pattern_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    print("\n" + "-" * 70)
    print("5. LanguageTool")
    print("-" * 70)
    r = evaluate_languagetool_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    print("\n" + "-" * 70)
    print("6. BETO (Transformer)")
    print("-" * 70)
    r = evaluate_beto_voter(text, words, gold_errors)
    results.append(r)
    print(r)
    if r.fp_words:
        print(f"  FP (primeros 10): {r.fp_words[:10]}")
    if r.fn_words:
        print(f"  FN (primeros 10): {r.fn_words[:10]}")

    # Resumen comparativo
    print("\n" + "=" * 70)
    print("RESUMEN COMPARATIVO")
    print("=" * 70)
    print(f"{'Voter':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Time':>10}")
    print("-" * 60)

    for r in results:
        print(f"{r.voter_name:<20} {r.precision:>10.1%} {r.recall:>10.1%} {r.f1:>10.1%} {r.time_seconds:>9.2f}s")

    # Recomendaciones
    print("\n" + "=" * 70)
    print("ANÁLISIS DE FORTALEZAS/DEBILIDADES")
    print("=" * 70)

    # Ordenar por precisión
    by_precision = sorted([r for r in results if r.precision > 0],
                          key=lambda x: x.precision, reverse=True)
    print("\nMejores para PRECISIÓN (menos falsos positivos):")
    for r in by_precision[:3]:
        print(f"  - {r.voter_name}: {r.precision:.1%}")

    # Ordenar por recall
    by_recall = sorted([r for r in results if r.recall > 0],
                       key=lambda x: x.recall, reverse=True)
    print("\nMejores para RECALL (menos falsos negativos):")
    for r in by_recall[:3]:
        print(f"  - {r.voter_name}: {r.recall:.1%}")

    # Ordenar por F1
    by_f1 = sorted([r for r in results if r.f1 > 0],
                   key=lambda x: x.f1, reverse=True)
    print("\nMejores F1 (equilibrio):")
    for r in by_f1[:3]:
        print(f"  - {r.voter_name}: {r.f1:.1%}")

    # Más rápidos
    by_speed = sorted([r for r in results if r.time_seconds > 0],
                      key=lambda x: x.time_seconds)
    print("\nMás rápidos:")
    for r in by_speed[:3]:
        print(f"  - {r.voter_name}: {r.time_seconds:.2f}s")

    return results


if __name__ == "__main__":
    run_individual_voter_tests()
