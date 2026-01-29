"""
Narrative Health Check — Chequeo de salud narrativa.

Evalúa si un manuscrito tiene los elementos narrativos esenciales:
protagonista, conflicto, clímax, resolución, arco emocional, etc.

Ofrece una puntuación global y un desglose por dimensiones, con
semáforo (OK / AVISO / CRÍTICO) y sugerencias accionables.

Orientado a correctores editoriales: herramienta diagnóstica, no
prescriptiva. Un libro de cocina no necesita "antagonista", por eso
cada dimensión se adapta al contexto del tipo de documento.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Tipos
# =============================================================================

class HealthStatus(str, Enum):
    """Estado de salud de una dimensión narrativa."""
    OK = "ok"              # Detectado con confianza
    WARNING = "warning"    # Parcialmente detectado o mejorable
    CRITICAL = "critical"  # No detectado o con problemas graves
    NA = "n_a"             # No aplica para este tipo de documento


class HealthDimension(str, Enum):
    """Dimensiones del chequeo de salud narrativa."""
    PROTAGONIST = "protagonist"
    CONFLICT = "conflict"
    GOAL = "goal"
    STAKES = "stakes"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    EMOTIONAL_ARC = "emotional_arc"
    PACING = "pacing"
    COHERENCE = "coherence"
    STRUCTURE = "structure"
    CAST_BALANCE = "cast_balance"
    CHEKHOV = "chekhov"


# Iconos por dimensión (para el frontend)
DIMENSION_ICONS: dict[HealthDimension, str] = {
    HealthDimension.PROTAGONIST: "pi-user",
    HealthDimension.CONFLICT: "pi-exclamation-triangle",
    HealthDimension.GOAL: "pi-flag",
    HealthDimension.STAKES: "pi-bolt",
    HealthDimension.CLIMAX: "pi-chart-line",
    HealthDimension.RESOLUTION: "pi-check-circle",
    HealthDimension.EMOTIONAL_ARC: "pi-heart",
    HealthDimension.PACING: "pi-forward",
    HealthDimension.COHERENCE: "pi-link",
    HealthDimension.STRUCTURE: "pi-sitemap",
    HealthDimension.CAST_BALANCE: "pi-users",
    HealthDimension.CHEKHOV: "pi-key",
}

# Nombres en español
DIMENSION_NAMES: dict[HealthDimension, str] = {
    HealthDimension.PROTAGONIST: "Protagonista",
    HealthDimension.CONFLICT: "Conflicto central",
    HealthDimension.GOAL: "Objetivo / Meta",
    HealthDimension.STAKES: "Apuestas en juego",
    HealthDimension.CLIMAX: "Clímax",
    HealthDimension.RESOLUTION: "Resolución",
    HealthDimension.EMOTIONAL_ARC: "Arco emocional",
    HealthDimension.PACING: "Ritmo narrativo",
    HealthDimension.COHERENCE: "Coherencia",
    HealthDimension.STRUCTURE: "Estructura",
    HealthDimension.CAST_BALANCE: "Equilibrio de personajes",
    HealthDimension.CHEKHOV: "Tramas cerradas",
}


@dataclass
class DimensionScore:
    """Puntuación de una dimensión de salud narrativa."""
    dimension: HealthDimension
    name: str
    icon: str
    score: float            # 0-100
    status: HealthStatus
    explanation: str        # Explicación breve del resultado
    suggestion: str = ""    # Sugerencia de mejora (vacía si OK)
    evidence: str = ""      # Evidencia concreta del texto

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.value,
            "name": self.name,
            "icon": self.icon,
            "score": round(self.score, 1),
            "status": self.status.value,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
        }


@dataclass
class NarrativeHealthReport:
    """Informe completo de salud narrativa."""
    overall_score: float = 0.0
    overall_status: HealthStatus = HealthStatus.CRITICAL
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    critical_gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    total_chapters: int = 0

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "overall_status": self.overall_status.value,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "strengths": self.strengths,
            "critical_gaps": self.critical_gaps,
            "recommendations": self.recommendations,
            "total_chapters": self.total_chapters,
        }


# =============================================================================
# Analizador
# =============================================================================

class NarrativeHealthChecker:
    """
    Chequeo de salud narrativa.

    Evalúa 12 dimensiones narrativas usando datos ya analizados:
    - Entidades y menciones (protagonista, elenco)
    - Eventos narrativos (conflicto, clímax, resolución)
    - Arcos de personaje (arco emocional)
    - Ritmo (pacing)
    - Elementos Chekhov (tramas abiertas)
    - Estructura de capítulos
    """

    # Umbrales
    OK_THRESHOLD = 65.0
    WARNING_THRESHOLD = 35.0

    def check(
        self,
        chapters_data: list[dict],
        total_chapters: int,
        entities_data: Optional[list[dict]] = None,
        character_arcs: Optional[list[dict]] = None,
        chekhov_elements: Optional[list[dict]] = None,
        abandoned_threads: Optional[list[dict]] = None,
        pacing_data: Optional[dict] = None,
    ) -> NarrativeHealthReport:
        """
        Ejecutar chequeo de salud narrativa.

        Args:
            chapters_data: Datos por capítulo (misma estructura que narrative_templates)
            total_chapters: Número total de capítulos
            entities_data: Lista de entidades con tipo, menciones, etc.
            character_arcs: Arcos de personaje detectados
            chekhov_elements: Elementos setup/payoff tipo Chekhov
            abandoned_threads: Hilos narrativos abandonados
            pacing_data: Datos de ritmo

        Returns:
            NarrativeHealthReport
        """
        report = NarrativeHealthReport(total_chapters=total_chapters)
        entities = entities_data or []
        arcs = character_arcs or []
        chekhov = chekhov_elements or []
        threads = abandoned_threads or []

        if total_chapters < 2:
            report.overall_score = 0
            report.overall_status = HealthStatus.CRITICAL
            report.critical_gaps.append(
                "El manuscrito tiene menos de 2 capítulos. "
                "No es posible evaluar la salud narrativa."
            )
            return report

        # Evaluar cada dimensión
        report.dimensions = [
            self._check_protagonist(entities, chapters_data, total_chapters),
            self._check_conflict(chapters_data, total_chapters),
            self._check_goal(chapters_data, entities, total_chapters),
            self._check_stakes(chapters_data, total_chapters),
            self._check_climax(chapters_data, total_chapters),
            self._check_resolution(chapters_data, total_chapters),
            self._check_emotional_arc(arcs, total_chapters),
            self._check_pacing(chapters_data, total_chapters, pacing_data),
            self._check_coherence(chapters_data, total_chapters),
            self._check_structure(chapters_data, total_chapters),
            self._check_cast_balance(entities, chapters_data, total_chapters),
            self._check_chekhov(chekhov, threads),
        ]

        # Calcular score global (media ponderada excluyendo N/A)
        scored = [d for d in report.dimensions if d.status != HealthStatus.NA]
        if scored:
            report.overall_score = sum(d.score for d in scored) / len(scored)
        else:
            report.overall_score = 0

        # Status global
        if report.overall_score >= self.OK_THRESHOLD:
            report.overall_status = HealthStatus.OK
        elif report.overall_score >= self.WARNING_THRESHOLD:
            report.overall_status = HealthStatus.WARNING
        else:
            report.overall_status = HealthStatus.CRITICAL

        # Fortalezas y gaps
        for dim in report.dimensions:
            if dim.status == HealthStatus.OK:
                report.strengths.append(f"{dim.name}: {dim.explanation}")
            elif dim.status == HealthStatus.CRITICAL:
                report.critical_gaps.append(f"{dim.name}: {dim.explanation}")

        # Recomendaciones priorizadas
        report.recommendations = self._generate_recommendations(report)

        return report

    # =========================================================================
    # Dimensión: Protagonista
    # =========================================================================

    def _check_protagonist(
        self, entities: list[dict], chapters: list[dict], total: int
    ) -> DimensionScore:
        """¿Hay un protagonista claro con presencia sostenida?"""
        characters = [e for e in entities if e.get("entity_type") == "character"]

        if not characters:
            return DimensionScore(
                dimension=HealthDimension.PROTAGONIST,
                name=DIMENSION_NAMES[HealthDimension.PROTAGONIST],
                icon=DIMENSION_ICONS[HealthDimension.PROTAGONIST],
                score=10,
                status=HealthStatus.CRITICAL,
                explanation="No se detectaron personajes en el manuscrito.",
                suggestion="Verifique que los personajes estén correctamente identificados en el análisis de entidades.",
            )

        # Buscar personaje con más menciones
        characters_sorted = sorted(characters, key=lambda c: c.get("mention_count", 0), reverse=True)
        protagonist = characters_sorted[0]
        mentions = protagonist.get("mention_count", 0)
        name = protagonist.get("name", "Desconocido")

        # ¿Aparece en la mayoría de capítulos?
        chapters_present = protagonist.get("chapters_present", 0)
        presence_ratio = chapters_present / total if total > 0 else 0

        if mentions >= 10 and presence_ratio >= 0.6:
            score = min(100, 60 + presence_ratio * 40)
            return DimensionScore(
                dimension=HealthDimension.PROTAGONIST,
                name=DIMENSION_NAMES[HealthDimension.PROTAGONIST],
                icon=DIMENSION_ICONS[HealthDimension.PROTAGONIST],
                score=score,
                status=HealthStatus.OK,
                explanation=f"«{name}» es el protagonista claro con {mentions} menciones en {chapters_present} capítulos.",
                evidence=f"Presencia en {presence_ratio:.0%} de los capítulos.",
            )
        elif mentions >= 5:
            score = 40 + min(30, presence_ratio * 50)
            return DimensionScore(
                dimension=HealthDimension.PROTAGONIST,
                name=DIMENSION_NAMES[HealthDimension.PROTAGONIST],
                icon=DIMENSION_ICONS[HealthDimension.PROTAGONIST],
                score=score,
                status=HealthStatus.WARNING,
                explanation=f"«{name}» parece ser el protagonista ({mentions} menciones) pero su presencia es irregular.",
                suggestion="El protagonista debería tener presencia sostenida a lo largo del manuscrito.",
                evidence=f"Presente en {chapters_present} de {total} capítulos ({presence_ratio:.0%}).",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.PROTAGONIST,
                name=DIMENSION_NAMES[HealthDimension.PROTAGONIST],
                icon=DIMENSION_ICONS[HealthDimension.PROTAGONIST],
                score=25,
                status=HealthStatus.WARNING,
                explanation=f"«{name}» tiene pocas menciones ({mentions}). No queda claro quién es el protagonista.",
                suggestion="Considere si el protagonista está suficientemente establecido.",
            )

    # =========================================================================
    # Dimensión: Conflicto central
    # =========================================================================

    def _check_conflict(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿Hay un conflicto central detectable?"""
        conflict_chapters = 0
        total_conflicts = 0
        first_conflict = None

        for ch in chapters:
            c_count = ch.get("conflict_interactions", 0)
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            conflict_events = [e for e in events if e.get("event_type") == "conflict"]
            ch_conflicts = c_count + len(conflict_events)

            if ch_conflicts > 0:
                conflict_chapters += 1
                total_conflicts += ch_conflicts
                if first_conflict is None:
                    first_conflict = ch["chapter_number"]

        conflict_ratio = conflict_chapters / total if total > 0 else 0

        if conflict_ratio >= 0.3 and total_conflicts >= 3:
            score = min(100, 50 + conflict_ratio * 50 + total_conflicts * 2)
            return DimensionScore(
                dimension=HealthDimension.CONFLICT,
                name=DIMENSION_NAMES[HealthDimension.CONFLICT],
                icon=DIMENSION_ICONS[HealthDimension.CONFLICT],
                score=score,
                status=HealthStatus.OK,
                explanation=f"Conflicto detectado en {conflict_chapters} capítulos ({conflict_ratio:.0%} del manuscrito).",
                evidence=f"Primer conflicto en capítulo {first_conflict}. Total: {total_conflicts} interacciones conflictivas.",
            )
        elif total_conflicts >= 1:
            score = 30 + min(30, total_conflicts * 5)
            return DimensionScore(
                dimension=HealthDimension.CONFLICT,
                name=DIMENSION_NAMES[HealthDimension.CONFLICT],
                icon=DIMENSION_ICONS[HealthDimension.CONFLICT],
                score=score,
                status=HealthStatus.WARNING,
                explanation=f"Se detecta conflicto pero es esporádico ({conflict_chapters} capítulos, {total_conflicts} interacciones).",
                suggestion="El conflicto debería estar presente de forma más sostenida a lo largo de la trama.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.CONFLICT,
                name=DIMENSION_NAMES[HealthDimension.CONFLICT],
                icon=DIMENSION_ICONS[HealthDimension.CONFLICT],
                score=10,
                status=HealthStatus.CRITICAL,
                explanation="No se detectó conflicto significativo en el manuscrito.",
                suggestion="Todo relato necesita algún tipo de tensión o conflicto (incluso en no ficción).",
            )

    # =========================================================================
    # Dimensión: Objetivo / Meta
    # =========================================================================

    def _check_goal(
        self, chapters: list[dict], entities: list[dict], total: int
    ) -> DimensionScore:
        """¿El protagonista tiene un objetivo claro? Heurística: decisiones y acciones."""
        goal_events = {"decision", "departure", "discovery"}
        found = 0
        evidence_ch = None

        for ch in chapters[:max(3, total // 3)]:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in goal_events:
                    found += 1
                    if evidence_ch is None:
                        evidence_ch = ch["chapter_number"]

        if found >= 2:
            return DimensionScore(
                dimension=HealthDimension.GOAL,
                name=DIMENSION_NAMES[HealthDimension.GOAL],
                icon=DIMENSION_ICONS[HealthDimension.GOAL],
                score=70,
                status=HealthStatus.OK,
                explanation=f"Se detectan decisiones y acciones tempranas ({found} eventos en el primer tercio).",
                evidence=f"Primera decisión/descubrimiento en capítulo {evidence_ch}.",
            )
        elif found == 1:
            return DimensionScore(
                dimension=HealthDimension.GOAL,
                name=DIMENSION_NAMES[HealthDimension.GOAL],
                icon=DIMENSION_ICONS[HealthDimension.GOAL],
                score=45,
                status=HealthStatus.WARNING,
                explanation="Hay indicios de objetivo pero no es evidente. Requiere análisis LLM para confirmar.",
                suggestion="El objetivo del protagonista debería quedar claro en el primer tercio del manuscrito.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.GOAL,
                name=DIMENSION_NAMES[HealthDimension.GOAL],
                icon=DIMENSION_ICONS[HealthDimension.GOAL],
                score=25,
                status=HealthStatus.WARNING,
                explanation="No se detectaron decisiones o acciones claras en el primer tercio.",
                suggestion="Considere si el lector puede identificar qué quiere el protagonista.",
            )

    # =========================================================================
    # Dimensión: Apuestas en juego
    # =========================================================================

    def _check_stakes(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿Hay algo en juego? Heurística: intensidad tonal + conflictos."""
        high_intensity = 0
        for ch in chapters:
            intensity = ch.get("tone_intensity", 0)
            if intensity >= 0.6:
                high_intensity += 1

        ratio = high_intensity / total if total > 0 else 0
        if ratio >= 0.25:
            score = min(90, 50 + ratio * 80)
            return DimensionScore(
                dimension=HealthDimension.STAKES,
                name=DIMENSION_NAMES[HealthDimension.STAKES],
                icon=DIMENSION_ICONS[HealthDimension.STAKES],
                score=score,
                status=HealthStatus.OK,
                explanation=f"Intensidad tonal alta en {high_intensity} capítulos ({ratio:.0%}), indica apuestas claras.",
            )
        elif high_intensity >= 1:
            return DimensionScore(
                dimension=HealthDimension.STAKES,
                name=DIMENSION_NAMES[HealthDimension.STAKES],
                icon=DIMENSION_ICONS[HealthDimension.STAKES],
                score=40,
                status=HealthStatus.WARNING,
                explanation=f"Intensidad tonal alta solo en {high_intensity} capítulo(s).",
                suggestion="Las apuestas deberían escalar progresivamente a lo largo del manuscrito.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.STAKES,
                name=DIMENSION_NAMES[HealthDimension.STAKES],
                icon=DIMENSION_ICONS[HealthDimension.STAKES],
                score=20,
                status=HealthStatus.CRITICAL,
                explanation="No se detecta intensidad tonal significativa.",
                suggestion="Sin apuestas claras el lector pierde interés. ¿Qué se pierde si el protagonista fracasa?",
            )

    # =========================================================================
    # Dimensión: Clímax
    # =========================================================================

    def _check_climax(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿Hay un punto de máxima tensión en el último tercio?"""
        last_third = [c for c in chapters if c["chapter_number"] >= total * 0.65]
        climax_events = {"climax_moment", "conflict", "sacrifice", "death", "transformation"}

        best_intensity = 0.0
        best_ch = None
        has_climax_event = False

        for ch in last_third:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in climax_events:
                    has_climax_event = True

            intensity = ch.get("tone_intensity", 0)
            conflicts = ch.get("conflict_interactions", 0)
            combined = intensity + conflicts * 0.1
            if combined > best_intensity:
                best_intensity = combined
                best_ch = ch["chapter_number"]

        if has_climax_event and best_intensity >= 0.5:
            return DimensionScore(
                dimension=HealthDimension.CLIMAX,
                name=DIMENSION_NAMES[HealthDimension.CLIMAX],
                icon=DIMENSION_ICONS[HealthDimension.CLIMAX],
                score=85,
                status=HealthStatus.OK,
                explanation=f"Clímax detectado en el último tercio (capítulo {best_ch}).",
                evidence=f"Eventos de clímax + intensidad tonal de {best_intensity:.2f}.",
            )
        elif best_intensity >= 0.4:
            return DimensionScore(
                dimension=HealthDimension.CLIMAX,
                name=DIMENSION_NAMES[HealthDimension.CLIMAX],
                icon=DIMENSION_ICONS[HealthDimension.CLIMAX],
                score=55,
                status=HealthStatus.WARNING,
                explanation=f"Posible clímax en capítulo {best_ch} pero con intensidad moderada.",
                suggestion="El clímax debería ser el momento de máxima tensión. Considere si es suficientemente potente.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.CLIMAX,
                name=DIMENSION_NAMES[HealthDimension.CLIMAX],
                icon=DIMENSION_ICONS[HealthDimension.CLIMAX],
                score=15,
                status=HealthStatus.CRITICAL,
                explanation="No se detectó un clímax claro en el último tercio del manuscrito.",
                suggestion="Todo manuscrito narrativo necesita un punto de máxima tensión antes del desenlace.",
            )

    # =========================================================================
    # Dimensión: Resolución
    # =========================================================================

    def _check_resolution(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿Los conflictos se resuelven al final?"""
        last_chapters = [c for c in chapters if c["chapter_number"] >= total * 0.85]
        resolution_events = {"resolution", "return"}

        has_resolution = False
        for ch in last_chapters:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in resolution_events:
                    has_resolution = True

        if has_resolution:
            return DimensionScore(
                dimension=HealthDimension.RESOLUTION,
                name=DIMENSION_NAMES[HealthDimension.RESOLUTION],
                icon=DIMENSION_ICONS[HealthDimension.RESOLUTION],
                score=80,
                status=HealthStatus.OK,
                explanation="Se detectó resolución en los últimos capítulos.",
            )

        # Si hay capítulos finales con tono más calmado
        if last_chapters:
            last = last_chapters[-1]
            tone = last.get("dominant_tone", "")
            if tone in ("positive", "neutral", "hopeful", "calm"):
                return DimensionScore(
                    dimension=HealthDimension.RESOLUTION,
                    name=DIMENSION_NAMES[HealthDimension.RESOLUTION],
                    icon=DIMENSION_ICONS[HealthDimension.RESOLUTION],
                    score=50,
                    status=HealthStatus.WARNING,
                    explanation=f"El último capítulo tiene tono '{tone}' (posible resolución implícita).",
                    suggestion="Verifique que los hilos narrativos principales queden cerrados.",
                )

        return DimensionScore(
            dimension=HealthDimension.RESOLUTION,
            name=DIMENSION_NAMES[HealthDimension.RESOLUTION],
            icon=DIMENSION_ICONS[HealthDimension.RESOLUTION],
            score=20,
            status=HealthStatus.CRITICAL,
            explanation="No se detectó resolución clara en los últimos capítulos.",
            suggestion="El manuscrito debería cerrar los conflictos principales. Un final abierto es válido, pero debe ser intencional.",
        )

    # =========================================================================
    # Dimensión: Arco emocional
    # =========================================================================

    def _check_emotional_arc(
        self, arcs: list[dict], total: int
    ) -> DimensionScore:
        """¿El protagonista muestra un arco de transformación?"""
        if not arcs:
            return DimensionScore(
                dimension=HealthDimension.EMOTIONAL_ARC,
                name=DIMENSION_NAMES[HealthDimension.EMOTIONAL_ARC],
                icon=DIMENSION_ICONS[HealthDimension.EMOTIONAL_ARC],
                score=30,
                status=HealthStatus.WARNING,
                explanation="No se detectaron arcos de personaje.",
                suggestion="Los personajes principales deberían mostrar algún cambio o crecimiento.",
            )

        # Buscar el arco más completo
        best_arc = max(arcs, key=lambda a: a.get("completeness", 0))
        completeness = best_arc.get("completeness", 0)
        arc_type = best_arc.get("arc_type", "static")
        name = best_arc.get("character_name", "Desconocido")

        if completeness >= 0.6 and arc_type != "static":
            score = min(95, 50 + completeness * 50)
            return DimensionScore(
                dimension=HealthDimension.EMOTIONAL_ARC,
                name=DIMENSION_NAMES[HealthDimension.EMOTIONAL_ARC],
                icon=DIMENSION_ICONS[HealthDimension.EMOTIONAL_ARC],
                score=score,
                status=HealthStatus.OK,
                explanation=f"«{name}» tiene un arco de tipo '{arc_type}' con completitud del {completeness:.0%}.",
                evidence=f"Trayectoria: {best_arc.get('trajectory', 'estable')}.",
            )
        elif completeness >= 0.3:
            return DimensionScore(
                dimension=HealthDimension.EMOTIONAL_ARC,
                name=DIMENSION_NAMES[HealthDimension.EMOTIONAL_ARC],
                icon=DIMENSION_ICONS[HealthDimension.EMOTIONAL_ARC],
                score=45,
                status=HealthStatus.WARNING,
                explanation=f"Arco parcial para «{name}» (completitud {completeness:.0%}, tipo '{arc_type}').",
                suggestion="El arco del protagonista podría estar más definido. ¿Cómo cambia a lo largo de la historia?",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.EMOTIONAL_ARC,
                name=DIMENSION_NAMES[HealthDimension.EMOTIONAL_ARC],
                icon=DIMENSION_ICONS[HealthDimension.EMOTIONAL_ARC],
                score=25,
                status=HealthStatus.CRITICAL,
                explanation=f"El arco de «{name}» es muy incompleto ({completeness:.0%}) o estático.",
                suggestion="Un protagonista estático resta impacto emocional. Considere qué aprende o cómo cambia.",
            )

    # =========================================================================
    # Dimensión: Ritmo narrativo
    # =========================================================================

    def _check_pacing(
        self, chapters: list[dict], total: int, pacing_data: Optional[dict]
    ) -> DimensionScore:
        """¿El ritmo es apropiado? Sin zonas muertas largas."""
        word_counts = [c.get("word_count", 0) for c in chapters]

        if not word_counts or all(w == 0 for w in word_counts):
            return DimensionScore(
                dimension=HealthDimension.PACING,
                name=DIMENSION_NAMES[HealthDimension.PACING],
                icon=DIMENSION_ICONS[HealthDimension.PACING],
                score=30,
                status=HealthStatus.WARNING,
                explanation="No hay datos de longitud de capítulos para evaluar el ritmo.",
            )

        avg = sum(word_counts) / len(word_counts) if word_counts else 0
        if avg == 0:
            avg = 1

        # Detectar variación extrema
        max_ratio = max(word_counts) / avg if avg > 0 else 1
        min_ratio = min(w for w in word_counts if w > 0) / avg if avg > 0 and any(w > 0 for w in word_counts) else 1

        # Detectar capítulos vacíos o casi vacíos
        dead_chapters = sum(1 for w in word_counts if w < avg * 0.2)

        if max_ratio < 2.5 and dead_chapters == 0:
            return DimensionScore(
                dimension=HealthDimension.PACING,
                name=DIMENSION_NAMES[HealthDimension.PACING],
                icon=DIMENSION_ICONS[HealthDimension.PACING],
                score=80,
                status=HealthStatus.OK,
                explanation=f"Ritmo consistente: capítulos entre {min(word_counts)} y {max(word_counts)} palabras.",
            )
        elif max_ratio < 4.0 and dead_chapters <= 1:
            return DimensionScore(
                dimension=HealthDimension.PACING,
                name=DIMENSION_NAMES[HealthDimension.PACING],
                icon=DIMENSION_ICONS[HealthDimension.PACING],
                score=55,
                status=HealthStatus.WARNING,
                explanation=f"Variación de ritmo notable: capítulo más largo es {max_ratio:.1f}x el promedio.",
                suggestion="Equilibre la extensión de los capítulos para mantener un ritmo más uniforme.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.PACING,
                name=DIMENSION_NAMES[HealthDimension.PACING],
                icon=DIMENSION_ICONS[HealthDimension.PACING],
                score=25,
                status=HealthStatus.CRITICAL,
                explanation=f"Ritmo muy irregular: {dead_chapters} capítulo(s) casi vacío(s), ratio max/min de {max_ratio:.1f}x.",
                suggestion="Hay zonas muertas o capítulos desproporcionados que pueden romper el ritmo de lectura.",
            )

    # =========================================================================
    # Dimensión: Coherencia
    # =========================================================================

    def _check_coherence(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿Los eventos siguen una lógica? Heurística: cambios de tono bruscos."""
        if total < 3:
            return DimensionScore(
                dimension=HealthDimension.COHERENCE,
                name=DIMENSION_NAMES[HealthDimension.COHERENCE],
                icon=DIMENSION_ICONS[HealthDimension.COHERENCE],
                score=50,
                status=HealthStatus.WARNING,
                explanation="Muy pocos capítulos para evaluar coherencia narrativa.",
            )

        tones = [c.get("dominant_tone", "neutral") for c in chapters]
        sudden_shifts = 0
        positive_tones = {"positive", "hopeful", "triumphant", "calm"}
        negative_tones = {"negative", "tense", "fearful", "melancholic"}

        for i in range(1, len(tones)):
            prev, curr = tones[i - 1], tones[i]
            if (prev in positive_tones and curr in negative_tones) or \
               (prev in negative_tones and curr in positive_tones):
                sudden_shifts += 1

        shift_ratio = sudden_shifts / (total - 1) if total > 1 else 0

        if shift_ratio <= 0.2:
            return DimensionScore(
                dimension=HealthDimension.COHERENCE,
                name=DIMENSION_NAMES[HealthDimension.COHERENCE],
                icon=DIMENSION_ICONS[HealthDimension.COHERENCE],
                score=80,
                status=HealthStatus.OK,
                explanation=f"Progresión tonal fluida ({sudden_shifts} cambios bruscos de {total - 1} transiciones).",
            )
        elif shift_ratio <= 0.4:
            return DimensionScore(
                dimension=HealthDimension.COHERENCE,
                name=DIMENSION_NAMES[HealthDimension.COHERENCE],
                icon=DIMENSION_ICONS[HealthDimension.COHERENCE],
                score=50,
                status=HealthStatus.WARNING,
                explanation=f"Se detectan {sudden_shifts} cambios bruscos de tono ({shift_ratio:.0%} de transiciones).",
                suggestion="Los cambios emocionales abruptos pueden desorientar al lector si no están justificados narrativamente.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.COHERENCE,
                name=DIMENSION_NAMES[HealthDimension.COHERENCE],
                icon=DIMENSION_ICONS[HealthDimension.COHERENCE],
                score=25,
                status=HealthStatus.CRITICAL,
                explanation=f"Coherencia tonal baja: {sudden_shifts} cambios bruscos en {total - 1} transiciones.",
                suggestion="Revise la progresión emocional entre capítulos. Los giros abruptos necesitan preparación.",
            )

    # =========================================================================
    # Dimensión: Estructura
    # =========================================================================

    def _check_structure(self, chapters: list[dict], total: int) -> DimensionScore:
        """¿El manuscrito tiene inicio, desarrollo y final distinguibles?"""
        if total < 3:
            return DimensionScore(
                dimension=HealthDimension.STRUCTURE,
                name=DIMENSION_NAMES[HealthDimension.STRUCTURE],
                icon=DIMENSION_ICONS[HealthDimension.STRUCTURE],
                score=30,
                status=HealthStatus.WARNING,
                explanation="Menos de 3 capítulos: estructura mínima.",
            )

        # Verificar que hay contenido en las tres partes
        third = max(1, total // 3)
        beginning = chapters[:third]
        middle = chapters[third:2 * third]
        ending = chapters[2 * third:]

        parts_with_content = 0
        for part in [beginning, middle, ending]:
            word_sum = sum(c.get("word_count", 0) for c in part)
            if word_sum > 0:
                parts_with_content += 1

        if parts_with_content == 3:
            # Verificar proporción razonable (no todo al inicio o al final)
            begin_words = sum(c.get("word_count", 0) for c in beginning)
            middle_words = sum(c.get("word_count", 0) for c in middle)
            end_words = sum(c.get("word_count", 0) for c in ending)
            total_words = begin_words + middle_words + end_words

            if total_words > 0:
                ratios = [begin_words / total_words, middle_words / total_words, end_words / total_words]
                min_ratio = min(ratios)

                if min_ratio >= 0.15:
                    return DimensionScore(
                        dimension=HealthDimension.STRUCTURE,
                        name=DIMENSION_NAMES[HealthDimension.STRUCTURE],
                        icon=DIMENSION_ICONS[HealthDimension.STRUCTURE],
                        score=85,
                        status=HealthStatus.OK,
                        explanation=f"Estructura equilibrada: inicio ({ratios[0]:.0%}), desarrollo ({ratios[1]:.0%}), final ({ratios[2]:.0%}).",
                    )
                else:
                    return DimensionScore(
                        dimension=HealthDimension.STRUCTURE,
                        name=DIMENSION_NAMES[HealthDimension.STRUCTURE],
                        icon=DIMENSION_ICONS[HealthDimension.STRUCTURE],
                        score=55,
                        status=HealthStatus.WARNING,
                        explanation=f"Estructura desbalanceada: alguna parte tiene solo {min_ratio:.0%} del contenido.",
                        suggestion="Las tres partes del manuscrito deberían estar proporcionalmente equilibradas.",
                    )

        return DimensionScore(
            dimension=HealthDimension.STRUCTURE,
            name=DIMENSION_NAMES[HealthDimension.STRUCTURE],
            icon=DIMENSION_ICONS[HealthDimension.STRUCTURE],
            score=35 + parts_with_content * 10,
            status=HealthStatus.WARNING if parts_with_content >= 2 else HealthStatus.CRITICAL,
            explanation=f"Solo {parts_with_content} de 3 partes estructurales tienen contenido.",
            suggestion="El manuscrito necesita inicio, desarrollo y final con contenido sustancial.",
        )

    # =========================================================================
    # Dimensión: Equilibrio de personajes
    # =========================================================================

    def _check_cast_balance(
        self, entities: list[dict], chapters: list[dict], total: int
    ) -> DimensionScore:
        """¿El elenco está equilibrado? Sin personajes fantasma ni exceso."""
        characters = [e for e in entities if e.get("entity_type") == "character"]

        if not characters:
            return DimensionScore(
                dimension=HealthDimension.CAST_BALANCE,
                name=DIMENSION_NAMES[HealthDimension.CAST_BALANCE],
                icon=DIMENSION_ICONS[HealthDimension.CAST_BALANCE],
                score=30,
                status=HealthStatus.WARNING,
                explanation="No se detectaron personajes.",
            )

        mentions = [c.get("mention_count", 0) for c in characters]
        total_mentions = sum(mentions) or 1
        max_mentions = max(mentions)

        # Personajes con menos de 5% de las menciones totales → "fantasma"
        ghost_count = sum(1 for m in mentions if m / total_mentions < 0.02)
        ghost_ratio = ghost_count / len(characters) if characters else 0

        # Concentración del protagonista
        protag_ratio = max_mentions / total_mentions

        if ghost_ratio <= 0.2 and 0.15 <= protag_ratio <= 0.60:
            return DimensionScore(
                dimension=HealthDimension.CAST_BALANCE,
                name=DIMENSION_NAMES[HealthDimension.CAST_BALANCE],
                icon=DIMENSION_ICONS[HealthDimension.CAST_BALANCE],
                score=80,
                status=HealthStatus.OK,
                explanation=f"Elenco equilibrado: {len(characters)} personajes, protagonista con {protag_ratio:.0%} de menciones.",
            )
        elif ghost_ratio > 0.3:
            return DimensionScore(
                dimension=HealthDimension.CAST_BALANCE,
                name=DIMENSION_NAMES[HealthDimension.CAST_BALANCE],
                icon=DIMENSION_ICONS[HealthDimension.CAST_BALANCE],
                score=40,
                status=HealthStatus.WARNING,
                explanation=f"{ghost_count} de {len(characters)} personajes tienen menciones mínimas.",
                suggestion="Los personajes mencionados pocas veces pueden confundir al lector. Considere eliminarlos o desarrollarlos.",
            )
        elif protag_ratio > 0.70:
            return DimensionScore(
                dimension=HealthDimension.CAST_BALANCE,
                name=DIMENSION_NAMES[HealthDimension.CAST_BALANCE],
                icon=DIMENSION_ICONS[HealthDimension.CAST_BALANCE],
                score=55,
                status=HealthStatus.WARNING,
                explanation=f"El protagonista concentra el {protag_ratio:.0%} de las menciones.",
                suggestion="Los personajes secundarios podrían necesitar más desarrollo para enriquecer la trama.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.CAST_BALANCE,
                name=DIMENSION_NAMES[HealthDimension.CAST_BALANCE],
                icon=DIMENSION_ICONS[HealthDimension.CAST_BALANCE],
                score=60,
                status=HealthStatus.OK,
                explanation=f"Elenco de {len(characters)} personajes con distribución razonable.",
            )

    # =========================================================================
    # Dimensión: Tramas cerradas (Chekhov)
    # =========================================================================

    def _check_chekhov(
        self, chekhov: list[dict], threads: list[dict]
    ) -> DimensionScore:
        """¿Los hilos narrativos se cierran? ¿Hay setup sin payoff?"""
        total_elements = len(chekhov)
        fired = sum(1 for e in chekhov if e.get("is_fired", False))
        abandoned = len(threads)

        if total_elements == 0 and abandoned == 0:
            return DimensionScore(
                dimension=HealthDimension.CHEKHOV,
                name=DIMENSION_NAMES[HealthDimension.CHEKHOV],
                icon=DIMENSION_ICONS[HealthDimension.CHEKHOV],
                score=50,
                status=HealthStatus.WARNING,
                explanation="No se detectaron elementos setup/payoff ni hilos abandonados.",
                suggestion="El análisis de tramas requiere entidades y capítulos analizados.",
            )

        fired_ratio = fired / total_elements if total_elements > 0 else 1.0

        if fired_ratio >= 0.7 and abandoned <= 1:
            score = min(95, 60 + fired_ratio * 30)
            return DimensionScore(
                dimension=HealthDimension.CHEKHOV,
                name=DIMENSION_NAMES[HealthDimension.CHEKHOV],
                icon=DIMENSION_ICONS[HealthDimension.CHEKHOV],
                score=score,
                status=HealthStatus.OK,
                explanation=f"{fired} de {total_elements} elementos Chekhov cerrados. {abandoned} hilo(s) abandonado(s).",
            )
        elif fired_ratio >= 0.4:
            return DimensionScore(
                dimension=HealthDimension.CHEKHOV,
                name=DIMENSION_NAMES[HealthDimension.CHEKHOV],
                icon=DIMENSION_ICONS[HealthDimension.CHEKHOV],
                score=45,
                status=HealthStatus.WARNING,
                explanation=f"Solo {fired} de {total_elements} elementos cerrados. {abandoned} hilo(s) abandonado(s).",
                suggestion="Los elementos narrativos introducidos deberían resolverse o pagarse antes del final.",
            )
        else:
            return DimensionScore(
                dimension=HealthDimension.CHEKHOV,
                name=DIMENSION_NAMES[HealthDimension.CHEKHOV],
                icon=DIMENSION_ICONS[HealthDimension.CHEKHOV],
                score=20,
                status=HealthStatus.CRITICAL,
                explanation=f"Muchas tramas sin cerrar: {total_elements - fired} de {total_elements} elementos sin payoff, {abandoned} hilo(s) abandonado(s).",
                suggestion="Revise los elementos narrativos pendientes de resolución. El lector espera que los hilos se cierren.",
            )

    # =========================================================================
    # Recomendaciones
    # =========================================================================

    def _generate_recommendations(self, report: NarrativeHealthReport) -> list[str]:
        """Generar recomendaciones priorizadas."""
        recs = []

        # Primero: dimensiones críticas
        critical = [d for d in report.dimensions if d.status == HealthStatus.CRITICAL]
        for dim in critical:
            if dim.suggestion:
                recs.append(f"[CRÍTICO] {dim.name}: {dim.suggestion}")

        # Segundo: advertencias con sugerencia
        warnings = [d for d in report.dimensions if d.status == HealthStatus.WARNING and dim.suggestion]
        for dim in warnings:
            if dim.suggestion:
                recs.append(f"[AVISO] {dim.name}: {dim.suggestion}")

        # Recomendación general
        if report.overall_score >= 70:
            recs.append(
                "El manuscrito tiene buena salud narrativa. "
                "Las sugerencias anteriores son mejoras opcionales."
            )
        elif report.overall_score >= 45:
            recs.append(
                "El manuscrito tiene una base narrativa pero necesita trabajo en las áreas marcadas."
            )
        elif report.overall_score > 0:
            recs.append(
                "El manuscrito necesita atención en varios aspectos narrativos fundamentales. "
                "Considere abordar primero los elementos críticos."
            )

        return recs
