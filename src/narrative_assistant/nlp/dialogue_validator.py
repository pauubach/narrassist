"""
Validador de contexto de diálogos.

Detecta diálogos huérfanos y problemas de contexto:
1. Diálogos sin atribución clara (no se sabe quién habla)
2. Secuencias de diálogos sin establecer escena
3. Diálogos al inicio de capítulo sin contexto
4. Diálogos consecutivos sin indicar cambio de hablante
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .dialogue import detect_dialogues, DialogueSpan, DialogueResult

logger = logging.getLogger(__name__)


class DialogueIssueType(str, Enum):
    """Tipos de problemas en diálogos."""

    ORPHAN_NO_ATTRIBUTION = "orphan_no_attribution"  # Sin saber quién habla
    ORPHAN_NO_CONTEXT = "orphan_no_context"  # Sin contexto de escena
    CONSECUTIVE_NO_CHANGE = "consecutive_no_change"  # Varios seguidos sin indicar cambio
    CHAPTER_START_DIALOGUE = "chapter_start_dialogue"  # Inicia capítulo con diálogo


class DialogueIssueSeverity(str, Enum):
    """Severidad del problema de diálogo."""

    HIGH = "high"  # Confusión clara de quién habla
    MEDIUM = "medium"  # Podría causar confusión
    LOW = "low"  # Menor importancia


@dataclass
class DialogueLocation:
    """Ubicación de un diálogo problemático."""

    chapter: int
    paragraph: int
    start_char: int
    end_char: int
    text: str

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text[:150] + "..." if len(self.text) > 150 else self.text,
        }


@dataclass
class DialogueIssue:
    """
    Un problema detectado en un diálogo.
    """

    issue_type: DialogueIssueType
    severity: DialogueIssueSeverity
    location: DialogueLocation
    description: str
    suggestion: str
    consecutive_count: int = 1  # Para secuencias de diálogos sin atribución

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "location": self.location.to_dict(),
            "description": self.description,
            "suggestion": self.suggestion,
            "consecutive_count": self.consecutive_count,
        }


@dataclass
class DialogueValidationReport:
    """Reporte de validación de diálogos."""

    issues: list[DialogueIssue] = field(default_factory=list)
    total_dialogues: int = 0
    dialogues_with_attribution: int = 0
    dialogues_without_attribution: int = 0
    chapters_analyzed: int = 0

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @property
    def attribution_ratio(self) -> float:
        if self.total_dialogues == 0:
            return 1.0
        return self.dialogues_with_attribution / self.total_dialogues

    def to_dict(self) -> dict:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "total_issues": self.total_issues,
            "total_dialogues": self.total_dialogues,
            "dialogues_with_attribution": self.dialogues_with_attribution,
            "dialogues_without_attribution": self.dialogues_without_attribution,
            "attribution_ratio": self.attribution_ratio,
            "chapters_analyzed": self.chapters_analyzed,
            "by_type": self._count_by_type(),
            "by_severity": self._count_by_severity(),
        }

    def _count_by_type(self) -> dict:
        counts = {t.value: 0 for t in DialogueIssueType}
        for issue in self.issues:
            counts[issue.issue_type.value] += 1
        return counts

    def _count_by_severity(self) -> dict:
        counts = {s.value: 0 for s in DialogueIssueSeverity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class DialogueContextValidator:
    """
    Valida que los diálogos tengan contexto adecuado.

    Detecta:
    - Diálogos sin atribución (quién habla)
    - Secuencias largas sin establecer escena
    - Diálogos al inicio de capítulo sin contexto
    """

    def __init__(
        self,
        max_unattributed_consecutive: int = 3,
        min_context_chars: int = 50,
    ):
        """
        Inicializa el validador.

        Args:
            max_unattributed_consecutive: Máximo de diálogos consecutivos
                sin atribución antes de reportar problema.
            min_context_chars: Mínimo de caracteres de contexto esperado
                antes del primer diálogo.
        """
        self.max_unattributed_consecutive = max_unattributed_consecutive
        self.min_context_chars = min_context_chars

    def validate_chapter(
        self,
        chapter_text: str,
        chapter_number: int,
        chapter_start_char: int = 0,
    ) -> list[DialogueIssue]:
        """
        Valida los diálogos de un capítulo.

        Args:
            chapter_text: Contenido del capítulo
            chapter_number: Número del capítulo
            chapter_start_char: Posición de inicio del capítulo en el documento

        Returns:
            Lista de problemas detectados
        """
        if not chapter_text or not chapter_text.strip():
            return []

        issues = []

        # Detectar diálogos
        result = detect_dialogues(chapter_text)
        if result.is_failure or not result.value:
            return []

        dialogue_result: DialogueResult = result.value
        dialogues = dialogue_result.dialogues

        if not dialogues:
            return []

        # Verificar contexto al inicio del capítulo
        first_dialogue = dialogues[0]
        context_issue = self._check_chapter_start_context(
            first_dialogue, chapter_text, chapter_number, chapter_start_char
        )
        if context_issue:
            issues.append(context_issue)

        # Verificar secuencias sin atribución
        sequence_issues = self._check_unattributed_sequences(
            dialogues, chapter_text, chapter_number, chapter_start_char
        )
        issues.extend(sequence_issues)

        return issues

    def validate_all(
        self,
        chapters: list[dict],
    ) -> DialogueValidationReport:
        """
        Valida todos los capítulos.

        Args:
            chapters: Lista de capítulos con {number, content, start_char}

        Returns:
            DialogueValidationReport con todos los problemas
        """
        report = DialogueValidationReport(chapters_analyzed=len(chapters))
        all_issues = []

        for chapter in chapters:
            chapter_num = chapter.get("number", 0)
            content = chapter.get("content", "")
            start_char = chapter.get("start_char", 0)

            if not content.strip():
                continue

            # Obtener estadísticas de diálogos
            result = detect_dialogues(content)
            if result.is_success and result.value:
                dr = result.value
                report.total_dialogues += len(dr.dialogues)
                report.dialogues_with_attribution += sum(
                    1 for d in dr.dialogues if d.attribution_text
                )
                report.dialogues_without_attribution += sum(
                    1 for d in dr.dialogues if not d.attribution_text
                )

            # Validar capítulo
            issues = self.validate_chapter(content, chapter_num, start_char)
            all_issues.extend(issues)

        report.issues = all_issues
        return report

    def _check_chapter_start_context(
        self,
        first_dialogue: DialogueSpan,
        chapter_text: str,
        chapter_number: int,
        chapter_start_char: int,
    ) -> Optional[DialogueIssue]:
        """
        Verifica si hay suficiente contexto antes del primer diálogo.
        """
        # Texto antes del primer diálogo
        text_before = chapter_text[:first_dialogue.start_char].strip()

        # Si el capítulo empieza con diálogo o hay muy poco contexto
        if len(text_before) < self.min_context_chars:
            # Solo reportar si no tiene atribución
            if not first_dialogue.attribution_text:
                return DialogueIssue(
                    issue_type=DialogueIssueType.CHAPTER_START_DIALOGUE,
                    severity=DialogueIssueSeverity.MEDIUM,
                    location=DialogueLocation(
                        chapter=chapter_number,
                        paragraph=1,
                        start_char=chapter_start_char + first_dialogue.start_char,
                        end_char=chapter_start_char + first_dialogue.end_char,
                        text=first_dialogue.text,
                    ),
                    description=(
                        f"El capítulo {chapter_number} comienza con un diálogo "
                        f"sin establecer contexto de escena."
                    ),
                    suggestion=(
                        "Considera añadir una breve descripción de la escena "
                        "antes del diálogo, o indicar quién habla."
                    ),
                )

        return None

    def _check_unattributed_sequences(
        self,
        dialogues: list[DialogueSpan],
        chapter_text: str,
        chapter_number: int,
        chapter_start_char: int,
    ) -> list[DialogueIssue]:
        """
        Detecta secuencias de diálogos sin atribución.
        """
        issues = []
        consecutive_unattributed = 0
        sequence_start_idx = 0

        for i, dialogue in enumerate(dialogues):
            has_attribution = bool(dialogue.attribution_text)

            # También verificar si hay texto narrativo entre diálogos que indique hablante
            if i > 0 and not has_attribution:
                prev_end = dialogues[i - 1].end_char
                text_between = chapter_text[prev_end:dialogue.start_char].strip()
                has_attribution = self._text_indicates_speaker(text_between)

            if not has_attribution:
                if consecutive_unattributed == 0:
                    sequence_start_idx = i
                consecutive_unattributed += 1
            else:
                # Si había una secuencia larga, reportar
                if consecutive_unattributed >= self.max_unattributed_consecutive:
                    issue = self._create_sequence_issue(
                        dialogues,
                        sequence_start_idx,
                        i - 1,
                        consecutive_unattributed,
                        chapter_number,
                        chapter_start_char,
                    )
                    issues.append(issue)
                consecutive_unattributed = 0

        # Verificar secuencia al final
        if consecutive_unattributed >= self.max_unattributed_consecutive:
            issue = self._create_sequence_issue(
                dialogues,
                sequence_start_idx,
                len(dialogues) - 1,
                consecutive_unattributed,
                chapter_number,
                chapter_start_char,
            )
            issues.append(issue)

        # También reportar diálogos individuales sin atribución después del primero
        for i, dialogue in enumerate(dialogues[1:], start=1):
            if not dialogue.attribution_text:
                # Verificar si hay contexto entre diálogos
                prev_end = dialogues[i - 1].end_char
                text_between = chapter_text[prev_end:dialogue.start_char].strip()

                if not self._text_indicates_speaker(text_between):
                    # Solo si no está ya en una secuencia reportada
                    already_reported = any(
                        issue.location.start_char == chapter_start_char + dialogue.start_char
                        for issue in issues
                    )
                    if not already_reported and len(text_between) < 10:
                        issues.append(
                            DialogueIssue(
                                issue_type=DialogueIssueType.CONSECUTIVE_NO_CHANGE,
                                severity=DialogueIssueSeverity.LOW,
                                location=DialogueLocation(
                                    chapter=chapter_number,
                                    paragraph=self._get_paragraph(chapter_text, dialogue.start_char),
                                    start_char=chapter_start_char + dialogue.start_char,
                                    end_char=chapter_start_char + dialogue.end_char,
                                    text=dialogue.text,
                                ),
                                description=(
                                    "Diálogo sin indicación de quién habla, "
                                    "inmediatamente después de otro diálogo."
                                ),
                                suggestion=(
                                    "Considera añadir una atribución (dijo X) "
                                    "o una acotación narrativa."
                                ),
                            )
                        )

        return issues

    def _text_indicates_speaker(self, text: str) -> bool:
        """
        Verifica si el texto entre diálogos indica quién habla.
        """
        if not text:
            return False

        # Patrones que indican cambio de hablante
        speaker_patterns = [
            r"\b(dij[oa]|pregunt[oó]|respond[ií]|exclam[oó]|grit[oó]|susurr[oó])\b",
            r"\b(murmur[oó]|contest[oó]|replic[oó]|a[ñn]adi[oó]|continu[oó])\b",
            r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+(dij|pregunt|respond|exclam|grit)",
            r"(él|ella|ellos|ellas)\s+(dij|pregunt|respond)",
        ]

        text_lower = text.lower()
        for pattern in speaker_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _create_sequence_issue(
        self,
        dialogues: list[DialogueSpan],
        start_idx: int,
        end_idx: int,
        count: int,
        chapter_number: int,
        chapter_start_char: int,
    ) -> DialogueIssue:
        """
        Crea un issue para una secuencia de diálogos sin atribución.
        """
        first = dialogues[start_idx]
        last = dialogues[end_idx]

        severity = DialogueIssueSeverity.HIGH if count >= 5 else DialogueIssueSeverity.MEDIUM

        return DialogueIssue(
            issue_type=DialogueIssueType.ORPHAN_NO_ATTRIBUTION,
            severity=severity,
            location=DialogueLocation(
                chapter=chapter_number,
                paragraph=self._get_paragraph(
                    "",  # No tenemos el texto aquí
                    first.start_char,
                ),
                start_char=chapter_start_char + first.start_char,
                end_char=chapter_start_char + last.end_char,
                text=first.text,
            ),
            description=(
                f"Secuencia de {count} diálogos consecutivos sin indicar "
                f"quién habla en cada caso."
            ),
            suggestion=(
                f"En una secuencia de {count} diálogos, considera añadir "
                f"atribuciones periódicas (cada 2-3 intervenciones) "
                f"para que el lector no pierda el hilo de quién habla."
            ),
            consecutive_count=count,
        )

    def _get_paragraph(self, text: str, char_pos: int) -> int:
        """Obtiene el número de párrafo aproximado."""
        if not text:
            return 1
        text_before = text[:char_pos]
        return text_before.count("\n\n") + 1


# Singleton thread-safe
_validator_lock = threading.Lock()
_validator_instance: Optional[DialogueContextValidator] = None


def get_dialogue_validator() -> DialogueContextValidator:
    """Obtiene instancia singleton del validador."""
    global _validator_instance
    if _validator_instance is None:
        with _validator_lock:
            if _validator_instance is None:
                _validator_instance = DialogueContextValidator()
    return _validator_instance


def reset_dialogue_validator() -> None:
    """Resetea el singleton (para tests)."""
    global _validator_instance
    with _validator_lock:
        _validator_instance = None
