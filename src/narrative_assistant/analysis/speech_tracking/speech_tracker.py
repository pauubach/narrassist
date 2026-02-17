"""
SpeechTracker - Coordinador principal de detección de cambios de habla.
"""

import logging
from typing import Optional

from .change_detector import ChangeDetector
from .metrics import SpeechMetrics
from .speech_window import SpeechWindow, create_sliding_windows
from .types import SpeechChangeAlert

logger = logging.getLogger(__name__)


class SpeechTracker:
    """
    Coordina la detección de inconsistencias en el habla de personajes.

    Workflow:
    1. Crear ventanas deslizantes de diálogos por personaje
    2. Calcular métricas de habla por ventana
    3. Comparar ventanas adyacentes con pruebas estadísticas
    4. Generar alertas para cambios significativos
    """

    def __init__(
        self,
        window_size: int = 3,
        overlap: int = 1,
        min_words_per_window: int = 200,
        min_confidence: float = 0.6,
    ):
        """
        Inicializa el tracker.

        Args:
            window_size: Tamaño de ventana en capítulos (default: 3)
            overlap: Solapamiento entre ventanas (default: 1)
            min_words_per_window: Palabras mínimas para ventana válida (default: 200)
            min_confidence: Confianza mínima para generar alerta (default: 0.6)
        """
        self.window_size = window_size
        self.overlap = overlap
        self.min_words_per_window = min_words_per_window
        self.min_confidence = min_confidence
        self.change_detector = ChangeDetector()

    def detect_changes(
        self,
        character_id: int,
        character_name: str,
        chapters: list,
        spacy_nlp=None,
        narrative_context_analyzer=None,
        document_fingerprint: str | None = None,
    ) -> list[SpeechChangeAlert]:
        """
        Detecta cambios en el habla de un personaje.

        Args:
            character_id: ID del personaje
            character_name: Nombre del personaje
            chapters: Lista de capítulos del manuscrito
            spacy_nlp: Modelo spaCy (opcional, para métricas)
            narrative_context_analyzer: Analizador de contexto (opcional)
            document_fingerprint: SHA-256 del documento (opcional, para cache DB v0.10.14)

        Returns:
            Lista de SpeechChangeAlert
        """
        logger.info(f"Analyzing speech for character: {character_name}")

        # 1. Crear ventanas deslizantes
        windows = create_sliding_windows(
            character_id=character_id,
            character_name=character_name,
            chapters=chapters,
            window_size=self.window_size,
            overlap=self.overlap,
            min_words_per_window=self.min_words_per_window,
        )

        if len(windows) < 2:
            logger.debug(
                f"Not enough windows for {character_name} "
                f"(found {len(windows)}, need >=2)"
            )
            return []

        # 2. Calcular métricas para cada ventana (con cache DB v0.10.14)
        windows_with_metrics = []

        # DEBUG: Verificar si cache está habilitado
        if document_fingerprint:
            logger.info(
                f"[CACHE] Using DB cache for {character_name}, "
                f"fingerprint={document_fingerprint[:16]}..."
            )
        else:
            logger.warning(
                f"[CACHE] NO fingerprint for {character_name} "
                f"(got: {repr(document_fingerprint)}), "
                f"cache DISABLED -> re-analysis will be SLOW (10-12 min)"
            )

        for window in windows:
            metrics = SpeechMetrics.calculate(
                window.dialogues,
                spacy_nlp=spacy_nlp,
                use_cache=True,
                # Parámetros para DB cache (v0.10.14)
                character_id=character_id,
                window_start_chapter=window.start_chapter,
                window_end_chapter=window.end_chapter,
                document_fingerprint=document_fingerprint,
            )
            windows_with_metrics.append((window, metrics))

        # 3. Comparar ventanas adyacentes
        alerts = []
        for i in range(len(windows_with_metrics) - 1):
            window1, metrics1 = windows_with_metrics[i]
            window2, metrics2 = windows_with_metrics[i + 1]

            alert = self._compare_windows(
                character_id,
                character_name,
                window1,
                metrics1,
                window2,
                metrics2,
                narrative_context_analyzer,
                chapters,
            )

            if alert:
                alerts.append(alert)

        logger.info(
            f"Found {len(alerts)} speech change alerts for {character_name}"
        )
        return alerts

    def _compare_windows(
        self,
        character_id: int,
        character_name: str,
        window1: SpeechWindow,
        metrics1: dict[str, float],
        window2: SpeechWindow,
        metrics2: dict[str, float],
        narrative_context_analyzer,
        chapters: list,
    ) -> Optional[SpeechChangeAlert]:
        """
        Compara dos ventanas adyacentes y genera alerta si hay cambio significativo.

        Args:
            character_id: ID del personaje
            character_name: Nombre del personaje
            window1: Primera ventana
            metrics1: Métricas de window1
            window2: Segunda ventana
            metrics2: Métricas de window2
            narrative_context_analyzer: Analizador de contexto (opcional)
            chapters: Lista de capítulos (para contexto)

        Returns:
            SpeechChangeAlert si hay cambio significativo, None si no
        """
        # Detectar cambios en cada métrica
        changes = {}

        for metric_name in metrics1:
            value1 = metrics1[metric_name]
            value2 = metrics2[metric_name]

            change_result = self.change_detector.detect_metric_change(
                metric_name=metric_name,
                value1=value1,
                value2=value2,
                n1=window1.total_words,
                n2=window2.total_words,
            )

            if change_result.is_significant:
                changes[metric_name] = change_result

        # Si no hay cambios significativos, no crear alerta
        if len(changes) < 2:
            logger.debug(
                f"Not enough significant changes between "
                f"{window1.chapter_range} and {window2.chapter_range} "
                f"(found {len(changes)}, need >=2)"
            )
            return None

        # Calcular confianza agregada
        confidence = self.change_detector.calculate_change_confidence(
            changes=changes,
            window1_words=window1.total_words,
            window2_words=window2.total_words,
            window1_dialogues=window1.dialogue_count,
            window2_dialogues=window2.dialogue_count,
        )

        # Filtrar por confianza mínima
        if confidence < self.min_confidence:
            logger.debug(
                f"Confidence too low: {confidence:.2f} < {self.min_confidence}"
            )
            return None

        # Analizar contexto narrativo (si disponible)
        narrative_context = None
        if narrative_context_analyzer and chapters:
            try:
                # Analizar capítulos entre las dos ventanas
                gap_start = window1.end_chapter - 1  # 0-indexed
                gap_end = window2.start_chapter - 1

                if gap_start >= 0 and gap_end < len(chapters):
                    gap_chapters = chapters[gap_start : gap_end + 1]
                    narrative_context = narrative_context_analyzer.analyze(gap_chapters)
            except Exception as e:
                logger.warning(f"Narrative context analysis failed: {e}")

        # Determinar severidad
        severity = self.change_detector.determine_severity(
            changes=changes,
            confidence=confidence,
            narrative_context=narrative_context,
        )

        # Crear alerta
        alert = SpeechChangeAlert(
            character_id=character_id,
            character_name=character_name,
            window1_chapters=window1.chapter_range,
            window2_chapters=window2.chapter_range,
            changed_metrics=changes,
            confidence=confidence,
            severity=severity,
            narrative_context=narrative_context,
        )

        logger.info(
            f"Created speech change alert: {character_name} "
            f"({window1.chapter_range} → {window2.chapter_range}), "
            f"confidence={confidence:.2f}, severity={severity}"
        )

        return alert
