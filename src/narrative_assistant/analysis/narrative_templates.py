"""
Plantillas Narrativas — Diagnóstico de estructura narrativa.

Herramienta diagnóstica que evalúa si un manuscrito sigue patrones
conocidos de estructura narrativa. No es prescriptiva: un corrector
usa esto para identificar qué estructura parece estar usando el autor
y detectar huecos o inconsistencias.

Plantillas soportadas:
- Estructura en Tres Actos (Aristóteles → Syd Field)
- El Viaje del Héroe (Campbell → Vogler)
- Save the Cat (Blake Snyder)
- Kishotenketsu (estructura japonesa en 4 actos)
- Estructura en 5 Actos (Freytag)

Cada plantilla define "beats" (puntos clave) que se buscan en el
manuscrito usando datos ya analizados: capítulos, eventos, ritmo,
arcos de personaje y tono emocional.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Tipos
# =============================================================================

class TemplateType(str, Enum):
    """Tipos de plantilla narrativa."""
    THREE_ACT = "three_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    KISHOTENKETSU = "kishotenketsu"
    FIVE_ACT = "five_act"


class BeatStatus(str, Enum):
    """Estado de detección de un beat."""
    DETECTED = "detected"       # Encontrado con confianza alta
    POSSIBLE = "possible"       # Indicios parciales
    MISSING = "missing"         # No encontrado
    NOT_APPLICABLE = "n_a"      # No aplica (ej: pocos capítulos)


@dataclass
class TemplateBeat:
    """
    Un 'beat' o punto clave esperado en una plantilla.

    Ejemplo: "Llamada a la aventura" en el Viaje del Héroe.
    """
    beat_id: str                # ID único (ej: "call_to_adventure")
    name: str                   # Nombre en español
    description: str            # Descripción breve
    expected_position: float    # Posición esperada normalizada 0-1 en el manuscrito
    tolerance: float = 0.15     # Tolerancia de posición (±15% por defecto)

    # Resultado de la detección
    status: BeatStatus = BeatStatus.MISSING
    detected_chapter: Optional[int] = None
    detected_position: float = 0.0
    confidence: float = 0.0
    evidence: str = ""          # Texto/razón de la detección

    def to_dict(self) -> dict:
        return {
            "beat_id": self.beat_id,
            "name": self.name,
            "description": self.description,
            "expected_position": round(self.expected_position, 2),
            "status": self.status.value,
            "detected_chapter": self.detected_chapter,
            "detected_position": round(self.detected_position, 2),
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
        }


@dataclass
class TemplateMatch:
    """Resultado de comparar el manuscrito con una plantilla."""
    template_type: TemplateType
    template_name: str
    template_description: str
    fit_score: float            # 0-100: qué tan bien encaja
    beats: list[TemplateBeat] = field(default_factory=list)
    detected_count: int = 0
    possible_count: int = 0
    missing_count: int = 0
    total_beats: int = 0
    gaps: list[str] = field(default_factory=list)       # Huecos detectados
    strengths: list[str] = field(default_factory=list)   # Puntos fuertes
    suggestions: list[str] = field(default_factory=list)  # Sugerencias

    def to_dict(self) -> dict:
        return {
            "template_type": self.template_type.value,
            "template_name": self.template_name,
            "template_description": self.template_description,
            "fit_score": round(self.fit_score, 1),
            "beats": [b.to_dict() for b in self.beats],
            "detected_count": self.detected_count,
            "possible_count": self.possible_count,
            "missing_count": self.missing_count,
            "total_beats": self.total_beats,
            "gaps": self.gaps,
            "strengths": self.strengths,
            "suggestions": self.suggestions,
        }


@dataclass
class NarrativeTemplateReport:
    """Informe completo de análisis de plantillas narrativas."""
    best_match: Optional[TemplateMatch] = None
    matches: list[TemplateMatch] = field(default_factory=list)
    total_chapters: int = 0
    manuscript_summary: str = ""  # Resumen de la estructura detectada

    def to_dict(self) -> dict:
        sorted_matches = sorted(self.matches, key=lambda m: m.fit_score, reverse=True)
        return {
            "best_match": sorted_matches[0].to_dict() if sorted_matches else None,
            "matches": [m.to_dict() for m in sorted_matches],
            "total_chapters": self.total_chapters,
            "manuscript_summary": self.manuscript_summary,
        }


# =============================================================================
# Definiciones de plantillas
# =============================================================================

def _three_act_beats() -> list[TemplateBeat]:
    """Estructura en Tres Actos (Syd Field)."""
    return [
        TemplateBeat("setup", "Presentación", "Mundo ordinario, personajes y conflicto inicial", 0.05, 0.10),
        TemplateBeat("inciting_incident", "Incidente detonante", "Evento que pone la historia en marcha", 0.10, 0.08),
        TemplateBeat("first_plot_point", "Primer punto de giro", "El protagonista entra en el conflicto (fin Acto I)", 0.25, 0.08),
        TemplateBeat("rising_action", "Acción creciente", "Complicaciones, alianzas, conflictos secundarios", 0.40, 0.15),
        TemplateBeat("midpoint", "Punto medio", "Revelación o giro que cambia la perspectiva", 0.50, 0.08),
        TemplateBeat("second_plot_point", "Segundo punto de giro", "Crisis máxima, todo parece perdido (fin Acto II)", 0.75, 0.08),
        TemplateBeat("climax", "Clímax", "Enfrentamiento final, punto de máxima tensión", 0.88, 0.10),
        TemplateBeat("resolution", "Resolución", "Nuevo equilibrio, consecuencias del clímax", 0.95, 0.08),
    ]


def _hero_journey_beats() -> list[TemplateBeat]:
    """El Viaje del Héroe (Campbell/Vogler, 12 etapas)."""
    return [
        TemplateBeat("ordinary_world", "Mundo ordinario", "Vida cotidiana del héroe antes de la aventura", 0.04, 0.06),
        TemplateBeat("call_to_adventure", "Llamada a la aventura", "El héroe recibe un desafío o llamada", 0.10, 0.06),
        TemplateBeat("refusal", "Rechazo de la llamada", "Dudas, miedo, resistencia inicial", 0.14, 0.06),
        TemplateBeat("mentor", "Encuentro con el mentor", "Un guía o aliado prepara al héroe", 0.18, 0.06),
        TemplateBeat("crossing_threshold", "Cruce del umbral", "El héroe deja su mundo conocido", 0.25, 0.08),
        TemplateBeat("tests_allies", "Pruebas, aliados, enemigos", "Retos y nuevas relaciones en el mundo especial", 0.40, 0.12),
        TemplateBeat("approach_cave", "Acercamiento a la cueva", "Preparación para el desafío central", 0.50, 0.08),
        TemplateBeat("ordeal", "Prueba suprema", "El mayor desafío, muerte simbólica", 0.60, 0.08),
        TemplateBeat("reward", "Recompensa", "El héroe obtiene lo que buscaba", 0.68, 0.06),
        TemplateBeat("road_back", "Camino de regreso", "Vuelta al mundo ordinario con consecuencias", 0.78, 0.08),
        TemplateBeat("resurrection", "Resurrección", "Prueba final, transformación definitiva", 0.88, 0.08),
        TemplateBeat("return_elixir", "Regreso con el elixir", "El héroe vuelve transformado", 0.95, 0.06),
    ]


def _save_the_cat_beats() -> list[TemplateBeat]:
    """Save the Cat (Blake Snyder, 15 beats)."""
    return [
        TemplateBeat("opening_image", "Imagen de apertura", "Primera impresión del tono y mundo", 0.02, 0.04),
        TemplateBeat("theme_stated", "Tema enunciado", "Alguien dice la lección de la historia", 0.05, 0.05),
        TemplateBeat("setup_stc", "Set-up", "Presentación del protagonista y su mundo", 0.08, 0.06),
        TemplateBeat("catalyst", "Catalizador", "Evento que lo cambia todo", 0.10, 0.04),
        TemplateBeat("debate", "Debate", "¿Debería aceptar el desafío?", 0.15, 0.06),
        TemplateBeat("break_into_two", "Entrada al Acto II", "Decisión de actuar, nuevo mundo", 0.25, 0.06),
        TemplateBeat("b_story", "Trama B", "Historia de amor o amistad paralela", 0.30, 0.08),
        TemplateBeat("fun_and_games", "Diversión y juegos", "La promesa de la premisa", 0.38, 0.10),
        TemplateBeat("midpoint_stc", "Punto medio", "Victoria falsa o derrota falsa", 0.50, 0.06),
        TemplateBeat("bad_guys_close_in", "Los malos se acercan", "Presión externa e interna aumenta", 0.62, 0.08),
        TemplateBeat("all_is_lost", "Todo está perdido", "El peor momento, muerte del mentor", 0.75, 0.06),
        TemplateBeat("dark_night_soul", "Noche oscura del alma", "Reflexión, desesperanza", 0.80, 0.06),
        TemplateBeat("break_into_three", "Entrada al Acto III", "El héroe encuentra la solución", 0.85, 0.05),
        TemplateBeat("finale", "Finale", "Ejecución del plan, enfrentamiento final", 0.90, 0.06),
        TemplateBeat("final_image", "Imagen final", "Contraste con la imagen de apertura", 0.98, 0.04),
    ]


def _kishotenketsu_beats() -> list[TemplateBeat]:
    """Kishotenketsu (estructura narrativa japonesa, 4 actos)."""
    return [
        TemplateBeat("ki_intro", "Ki (起) — Introducción", "Presentación de personajes y escenario", 0.12, 0.08),
        TemplateBeat("sho_development", "Shō (承) — Desarrollo", "Profundización sin conflicto, vida cotidiana", 0.37, 0.08),
        TemplateBeat("ten_twist", "Ten (転) — Giro", "Cambio inesperado, nueva perspectiva", 0.65, 0.08),
        TemplateBeat("ketsu_conclusion", "Ketsu (結) — Conclusión", "Reconciliación de elementos, nuevo equilibrio", 0.90, 0.08),
    ]


def _five_act_beats() -> list[TemplateBeat]:
    """Estructura en 5 Actos (Pirámide de Freytag)."""
    return [
        TemplateBeat("exposition", "Exposición", "Presentación del mundo y los personajes", 0.08, 0.08),
        TemplateBeat("rising_action_5", "Acción ascendente", "Complicaciones y tensión creciente", 0.30, 0.12),
        TemplateBeat("climax_5", "Clímax", "Punto de máxima tensión narrativa", 0.50, 0.10),
        TemplateBeat("falling_action", "Acción descendente", "Consecuencias del clímax", 0.72, 0.10),
        TemplateBeat("denouement", "Desenlace", "Resolución final de todos los hilos", 0.92, 0.08),
    ]


TEMPLATE_DEFINITIONS: dict[TemplateType, dict] = {
    TemplateType.THREE_ACT: {
        "name": "Tres Actos",
        "description": "Estructura clásica: planteamiento, nudo y desenlace (Aristóteles → Syd Field).",
        "beats_fn": _three_act_beats,
    },
    TemplateType.HERO_JOURNEY: {
        "name": "Viaje del Héroe",
        "description": "Monomito de Campbell: el protagonista sale de su mundo, enfrenta pruebas y regresa transformado.",
        "beats_fn": _hero_journey_beats,
    },
    TemplateType.SAVE_THE_CAT: {
        "name": "Save the Cat",
        "description": "Estructura de Blake Snyder en 15 beats, popular en guion y ficción comercial.",
        "beats_fn": _save_the_cat_beats,
    },
    TemplateType.KISHOTENKETSU: {
        "name": "Kishotenketsu",
        "description": "Estructura japonesa en 4 actos: introducción, desarrollo, giro y conclusión. Sin conflicto central obligatorio.",
        "beats_fn": _kishotenketsu_beats,
    },
    TemplateType.FIVE_ACT: {
        "name": "Cinco Actos (Freytag)",
        "description": "Pirámide de Freytag: exposición, acción ascendente, clímax, acción descendente, desenlace.",
        "beats_fn": _five_act_beats,
    },
}


# =============================================================================
# Analizador
# =============================================================================

class NarrativeTemplateAnalyzer:
    """
    Analiza un manuscrito contra plantillas narrativas conocidas.

    Usa datos ya analizados (capítulos, eventos, tono, ritmo) para
    detectar qué beats están presentes y en qué posición.
    """

    # Pesos para el score de fit
    WEIGHT_DETECTED = 1.0
    WEIGHT_POSSIBLE = 0.4
    WEIGHT_POSITION_BONUS = 0.2  # Bonus si el beat está en la posición correcta

    def analyze(
        self,
        chapters_data: list[dict],
        total_chapters: int,
        pacing_data: Optional[dict] = None,
    ) -> NarrativeTemplateReport:
        """
        Analizar manuscrito contra todas las plantillas.

        Args:
            chapters_data: Lista de dicts con datos por capítulo:
                - chapter_number: int
                - word_count: int
                - key_events: list[dict] con event_type, description, characters
                - dominant_tone: str
                - tone_intensity: float
                - new_characters: list[str]
                - conflict_interactions: int
                - total_interactions: int
                - locations_mentioned: list[str]
                - location_changes: int
            total_chapters: Número total de capítulos
            pacing_data: Datos de ritmo (opcional, dict con tension_curve, avg_sentence_length, etc.)

        Returns:
            NarrativeTemplateReport
        """
        report = NarrativeTemplateReport(total_chapters=total_chapters)

        if total_chapters < 3:
            report.manuscript_summary = (
                "El manuscrito tiene menos de 3 capítulos. "
                "El análisis de estructura requiere un mínimo de capítulos."
            )
            return report

        # Analizar contra cada plantilla
        for template_type, definition in TEMPLATE_DEFINITIONS.items():
            beats = definition["beats_fn"]()
            match = self._analyze_template(
                template_type=template_type,
                template_name=definition["name"],
                template_description=definition["description"],
                beats=beats,
                chapters_data=chapters_data,
                total_chapters=total_chapters,
                pacing_data=pacing_data,
            )
            report.matches.append(match)

        # Determinar mejor match
        if report.matches:
            report.best_match = max(report.matches, key=lambda m: m.fit_score)

        # Resumen
        report.manuscript_summary = self._generate_summary(report)

        return report

    def _analyze_template(
        self,
        template_type: TemplateType,
        template_name: str,
        template_description: str,
        beats: list[TemplateBeat],
        chapters_data: list[dict],
        total_chapters: int,
        pacing_data: Optional[dict],
    ) -> TemplateMatch:
        """Analizar un manuscrito contra una plantilla específica."""

        # Detectar cada beat
        for beat in beats:
            self._detect_beat(beat, chapters_data, total_chapters, pacing_data)

        # Calcular métricas
        detected = sum(1 for b in beats if b.status == BeatStatus.DETECTED)
        possible = sum(1 for b in beats if b.status == BeatStatus.POSSIBLE)
        missing = sum(1 for b in beats if b.status == BeatStatus.MISSING)
        total = len(beats)

        # Score de fit (0-100)
        if total == 0:
            fit_score = 0.0
        else:
            base_score = (
                (detected * self.WEIGHT_DETECTED + possible * self.WEIGHT_POSSIBLE) / total
            ) * 100

            # Bonus por posiciones correctas
            position_bonus = 0.0
            for beat in beats:
                if beat.status == BeatStatus.DETECTED:
                    pos_diff = abs(beat.detected_position - beat.expected_position)
                    if pos_diff <= beat.tolerance:
                        position_bonus += self.WEIGHT_POSITION_BONUS / total * 100

            fit_score = min(100, base_score + position_bonus)

            # Penalización por baja granularidad: plantillas con pocos beats
            # tienden a inflar la puntuación porque cada beat pesa más
            min_beats_full = 7
            if total < min_beats_full:
                granularity_factor = 0.7 + 0.3 * (total / min_beats_full)
                fit_score *= granularity_factor

        # Generar gaps, fortalezas y sugerencias
        gaps = []
        strengths = []
        suggestions = []

        for beat in beats:
            if beat.status == BeatStatus.MISSING:
                gaps.append(f'"{beat.name}" no detectado — {beat.description}')
            elif beat.status == BeatStatus.DETECTED:
                pos_diff = abs(beat.detected_position - beat.expected_position)
                if pos_diff <= beat.tolerance:
                    strengths.append(
                        f'"{beat.name}" en capítulo {beat.detected_chapter} '
                        f'(posición correcta)'
                    )
                else:
                    direction = "antes" if beat.detected_position < beat.expected_position else "después"
                    suggestions.append(
                        f'"{beat.name}" detectado en capítulo {beat.detected_chapter}, '
                        f'pero se espera {direction} (posición {beat.expected_position:.0%} del texto)'
                    )

        if missing > total * 0.5:
            suggestions.append(
                f"El manuscrito no encaja bien con la plantilla {template_name} — "
                f"faltan {missing} de {total} beats esperados."
            )

        return TemplateMatch(
            template_type=template_type,
            template_name=template_name,
            template_description=template_description,
            fit_score=fit_score,
            beats=beats,
            detected_count=detected,
            possible_count=possible,
            missing_count=missing,
            total_beats=total,
            gaps=gaps,
            strengths=strengths,
            suggestions=suggestions,
        )

    def _detect_beat(
        self,
        beat: TemplateBeat,
        chapters_data: list[dict],
        total_chapters: int,
        pacing_data: Optional[dict],
    ) -> None:
        """
        Detectar si un beat está presente en el manuscrito.

        Modifica el beat in-place con status, confidence, etc.
        Usa heurísticas basadas en los datos ya analizados.
        """
        bid = beat.beat_id

        # === SETUP / PRESENTACIÓN ===
        if bid in ("setup", "ordinary_world", "opening_image", "setup_stc",
                    "ki_intro", "exposition"):
            self._detect_setup(beat, chapters_data, total_chapters)

        # === INCIDENTE DETONANTE / CATALIZADOR ===
        elif bid in ("inciting_incident", "call_to_adventure", "catalyst"):
            self._detect_inciting_incident(beat, chapters_data, total_chapters)

        # === RECHAZO / DEBATE ===
        elif bid in ("refusal", "debate"):
            self._detect_refusal(beat, chapters_data, total_chapters)

        # === MENTOR ===
        elif bid == "mentor":
            self._detect_mentor(beat, chapters_data, total_chapters)

        # === CRUCE DEL UMBRAL / ENTRADA ACTO II ===
        elif bid in ("crossing_threshold", "first_plot_point", "break_into_two"):
            self._detect_threshold(beat, chapters_data, total_chapters)

        # === DESARROLLO / PRUEBAS ===
        elif bid in ("rising_action", "tests_allies", "fun_and_games",
                      "sho_development", "rising_action_5", "b_story"):
            self._detect_development(beat, chapters_data, total_chapters)

        # === PUNTO MEDIO ===
        elif bid in ("midpoint", "approach_cave", "midpoint_stc"):
            self._detect_midpoint(beat, chapters_data, total_chapters, pacing_data)

        # === PRUEBA SUPREMA / CRISIS ===
        elif bid in ("ordeal", "bad_guys_close_in"):
            self._detect_ordeal(beat, chapters_data, total_chapters)

        # === TODO ESTÁ PERDIDO ===
        elif bid in ("all_is_lost", "dark_night_soul",
                      "second_plot_point"):
            self._detect_all_is_lost(beat, chapters_data, total_chapters)

        # === RECOMPENSA ===
        elif bid == "reward":
            self._detect_reward(beat, chapters_data, total_chapters)

        # === CAMINO DE REGRESO / ENTRADA ACTO III ===
        elif bid in ("road_back", "break_into_three"):
            self._detect_road_back(beat, chapters_data, total_chapters)

        # === GIRO (Kishotenketsu Ten) ===
        elif bid == "ten_twist":
            self._detect_twist(beat, chapters_data, total_chapters)

        # === CLÍMAX ===
        elif bid in ("climax", "resurrection", "finale", "climax_5"):
            self._detect_climax(beat, chapters_data, total_chapters, pacing_data)

        # === RESOLUCIÓN / DESENLACE ===
        elif bid in ("resolution", "return_elixir", "final_image",
                      "denouement", "ketsu_conclusion"):
            self._detect_resolution(beat, chapters_data, total_chapters)

        # === TEMA ENUNCIADO ===
        elif bid == "theme_stated":
            self._detect_theme(beat, chapters_data, total_chapters)

        # === ACCIÓN DESCENDENTE ===
        elif bid == "falling_action":
            self._detect_falling_action(beat, chapters_data, total_chapters, pacing_data)

    # =========================================================================
    # Detectores de beats
    # =========================================================================

    def _detect_setup(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar presentación: primeros capítulos con nuevos personajes."""
        early = [c for c in chapters if c["chapter_number"] <= max(2, total // 5)]
        if not early:
            return

        new_chars = sum(len(c.get("new_characters", [])) for c in early)

        if new_chars >= 2:
            best = max(early, key=lambda c: len(c.get("new_characters", [])))
            beat.status = BeatStatus.DETECTED
            beat.detected_chapter = best["chapter_number"]
            beat.detected_position = best["chapter_number"] / total
            beat.confidence = min(0.9, 0.5 + new_chars * 0.1)
            beat.evidence = f"{new_chars} personajes introducidos en los primeros capítulos"
        elif new_chars >= 1:
            best = max(early, key=lambda c: len(c.get("new_characters", [])))
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = best["chapter_number"]
            beat.detected_position = best["chapter_number"] / total
            beat.confidence = 0.35
            beat.evidence = f"{new_chars} personaje introducido en los primeros capítulos"
        else:
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = 1
            beat.detected_position = 1 / total
            beat.confidence = 0.2
            beat.evidence = "Primer capítulo presente pero sin nuevos personajes detectados"

    def _detect_inciting_incident(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar incidente detonante: primer conflicto o evento disruptivo."""
        early_mid = [c for c in chapters if c["chapter_number"] <= max(3, total // 4)]
        conflict_events = {"conflict", "departure", "discovery", "plot_twist"}

        for ch in early_mid:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                etype = ev.get("event_type", "")
                if etype in conflict_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.75
                    beat.evidence = f"Evento '{etype}' en capítulo {ch['chapter_number']}"
                    return

        # Buscar aumento de conflicto
        for ch in early_mid:
            if ch.get("conflict_interactions", 0) > 0:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.4
                beat.evidence = f"Interacciones de conflicto en capítulo {ch['chapter_number']}"
                return

    def _detect_refusal(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar rechazo: cambio emocional negativo tras el incidente."""
        zone = [c for c in chapters
                if total * 0.08 <= c["chapter_number"] <= total * 0.25]

        # Buscar emotional_shift negativo (señal fuerte)
        for ch in zone:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") == "emotional_shift":
                    tone = ch.get("dominant_tone", "")
                    if tone in ("negative", "tense", "melancholic", "fearful"):
                        beat.status = BeatStatus.DETECTED
                        beat.detected_chapter = ch["chapter_number"]
                        beat.detected_position = ch["chapter_number"] / total
                        beat.confidence = 0.65
                        beat.evidence = (
                            f"Cambio emocional con tono '{tone}' "
                            f"en capítulo {ch['chapter_number']}"
                        )
                        return

        # Buscar tono negativo combinado con conflicto (señal media)
        for ch in zone:
            tone = ch.get("dominant_tone", "")
            has_conflict = ch.get("conflict_interactions", 0) > 0
            if tone in ("negative", "tense", "melancholic", "fearful") and has_conflict:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.45
                beat.evidence = (
                    f"Tono '{tone}' con conflicto "
                    f"en capítulo {ch['chapter_number']}"
                )
                return

        # Solo tono negativo (señal débil)
        for ch in zone:
            tone = ch.get("dominant_tone", "")
            if tone in ("negative", "tense", "melancholic", "fearful"):
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.3
                beat.evidence = f"Tono '{tone}' en capítulo {ch['chapter_number']}"
                return

    def _detect_mentor(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar mentor: nuevo personaje con interacciones positivas o alianzas."""
        zone = [c for c in chapters
                if total * 0.10 <= c["chapter_number"] <= total * 0.30]

        # Buscar alianza o nuevo personaje con muchas interacciones positivas (señal fuerte)
        for ch in zone:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            has_alliance = any(ev.get("event_type") == "alliance" for ev in events)
            pos_int = ch.get("positive_interactions", 0)
            has_new = bool(ch.get("new_characters"))

            if has_alliance and has_new:
                beat.status = BeatStatus.DETECTED
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.7
                beat.evidence = (
                    f"Alianza con nuevo personaje en cap. {ch['chapter_number']}"
                )
                return

            if has_new and pos_int >= 2:
                beat.status = BeatStatus.DETECTED
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.6
                beat.evidence = (
                    f"Nuevo personaje con {pos_int} interacciones positivas "
                    f"en cap. {ch['chapter_number']}"
                )
                return

        # Nuevo personaje con alguna interacción positiva (señal débil)
        for ch in zone:
            if ch.get("new_characters") and ch.get("positive_interactions", 0) > 0:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.35
                beat.evidence = (
                    f"Nuevo personaje con interacción positiva "
                    f"en cap. {ch['chapter_number']}"
                )
                return

    def _detect_threshold(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar cruce del umbral: cambio de ubicación o aumento brusco de conflicto ~25%."""
        target = max(1, round(total * 0.25))
        zone = [c for c in chapters
                if abs(c["chapter_number"] - target) <= max(2, total // 6)]
        transition_events = {"departure", "location_change", "decision", "crossing_threshold"}

        for ch in sorted(zone, key=lambda c: abs(c["chapter_number"] - target)):
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in transition_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.7
                    beat.evidence = f"Evento '{ev['event_type']}' en cap. {ch['chapter_number']}"
                    return

            if ch.get("location_changes", 0) >= 2:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.4
                beat.evidence = f"Múltiples cambios de ubicación en cap. {ch['chapter_number']}"
                return

    def _detect_development(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar desarrollo: zona central con interacciones y eventos variados."""
        zone = [c for c in chapters
                if total * 0.25 <= c["chapter_number"] <= total * 0.55]
        if not zone:
            return

        total_events = sum(
            len(c.get("key_events", [])) + len(c.get("llm_events", []))
            for c in zone
        )
        total_interactions = sum(c.get("total_interactions", 0) for c in zone)

        if total_events >= 3 or total_interactions >= 5:
            mid_ch = zone[len(zone) // 2]
            beat.status = BeatStatus.DETECTED
            beat.detected_chapter = mid_ch["chapter_number"]
            beat.detected_position = mid_ch["chapter_number"] / total
            beat.confidence = min(0.85, 0.4 + total_events * 0.08 + total_interactions * 0.03)
            beat.evidence = f"{total_events} eventos y {total_interactions} interacciones en la zona central"
        elif total_events >= 1 or total_interactions >= 2:
            mid_ch = zone[len(zone) // 2]
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = mid_ch["chapter_number"]
            beat.detected_position = mid_ch["chapter_number"] / total
            beat.confidence = 0.3
            beat.evidence = f"{total_events} eventos y {total_interactions} interacciones en la zona central (insuficiente para confirmar)"
        elif zone:
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = zone[0]["chapter_number"]
            beat.detected_position = zone[0]["chapter_number"] / total
            beat.confidence = 0.2
            beat.evidence = "Capítulos centrales presentes pero con pocos eventos detectados"

    def _detect_midpoint(self, beat: TemplateBeat, chapters: list[dict], total: int,
                         pacing: Optional[dict]) -> None:
        """Detectar punto medio: revelación, giro o cambio de tono ~50%."""
        target = max(1, round(total * 0.50))
        zone = [c for c in chapters
                if abs(c["chapter_number"] - target) <= max(2, total // 6)]
        midpoint_events = {"revelation", "discovery", "plot_twist", "emotional_shift", "betrayal"}

        for ch in sorted(zone, key=lambda c: abs(c["chapter_number"] - target)):
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in midpoint_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.75
                    beat.evidence = f"Evento '{ev['event_type']}' cerca del punto medio"
                    return

        # Buscar cambio de tono
        if len(zone) >= 2:
            tones = [c.get("dominant_tone", "neutral") for c in zone]
            if len(set(tones)) > 1:
                ch = zone[len(zone) // 2]
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.35
                beat.evidence = "Cambio de tono detectado en la zona central"

    def _detect_ordeal(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar prueba suprema: pico de conflicto en la segunda mitad."""
        zone = [c for c in chapters
                if total * 0.50 <= c["chapter_number"] <= total * 0.75]
        crisis_events = {"conflict", "death", "betrayal", "sacrifice", "climax_moment"}

        best_conflict = None
        max_conflict = 0
        for ch in zone:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in crisis_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.7
                    beat.evidence = f"Evento de crisis '{ev['event_type']}' en cap. {ch['chapter_number']}"
                    return

            c_count = ch.get("conflict_interactions", 0)
            if c_count > max_conflict:
                max_conflict = c_count
                best_conflict = ch

        if best_conflict and max_conflict >= 2:
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = best_conflict["chapter_number"]
            beat.detected_position = best_conflict["chapter_number"] / total
            beat.confidence = 0.4
            beat.evidence = f"{max_conflict} interacciones de conflicto en cap. {best_conflict['chapter_number']}"

    def _detect_all_is_lost(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar 'todo está perdido': tono negativo intenso ~75%."""
        target = max(1, round(total * 0.75))
        zone = [c for c in chapters
                if abs(c["chapter_number"] - target) <= max(2, total // 5)]
        dark_events = {"death", "betrayal", "sacrifice"}

        for ch in sorted(zone, key=lambda c: abs(c["chapter_number"] - target)):
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in dark_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.65
                    beat.evidence = f"Evento '{ev['event_type']}' en cap. {ch['chapter_number']}"
                    return

            tone = ch.get("dominant_tone", "")
            intensity = ch.get("tone_intensity", 0)
            if tone in ("negative", "tense", "fearful") and intensity >= 0.6:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.35
                beat.evidence = f"Tono '{tone}' intenso ({intensity:.0%}) en cap. {ch['chapter_number']}"
                return

    def _detect_reward(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar recompensa: tono positivo tras la prueba suprema."""
        zone = [c for c in chapters
                if total * 0.60 <= c["chapter_number"] <= total * 0.75]
        for ch in zone:
            tone = ch.get("dominant_tone", "")
            if tone in ("positive", "hopeful", "triumphant"):
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.35
                beat.evidence = f"Tono positivo '{tone}' en cap. {ch['chapter_number']}"
                return

    def _detect_road_back(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar camino de regreso: ubicación o dinámica que cambia ~80%."""
        zone = [c for c in chapters
                if total * 0.75 <= c["chapter_number"] <= total * 0.88]
        for ch in zone:
            if ch.get("location_changes", 0) >= 1:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.3
                beat.evidence = f"Cambio de ubicación en cap. {ch['chapter_number']}"
                return

    def _detect_twist(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """
        Detectar giro (Ten 転) de Kishotenketsu.

        El Ten NO es un clímax basado en conflicto. Es un cambio inesperado de
        perspectiva, tono o información. Funciona sin conflicto.
        Zona esperada: 53-77% del manuscrito.
        """
        zone = [c for c in chapters
                if total * 0.53 <= c["chapter_number"] <= total * 0.77]

        twist_indicators = {"revelation", "twist", "surprise", "discovery", "transformation"}

        # Buscar eventos de giro/revelación
        for ch in zone:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in twist_indicators:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.7
                    beat.evidence = f"Evento '{ev['event_type']}' sugiere giro narrativo"
                    return

        # Buscar cambio tonal significativo entre capítulos adyacentes
        for i, ch in enumerate(zone):
            if i == 0:
                continue
            prev_tone = zone[i - 1].get("dominant_tone", "")
            curr_tone = ch.get("dominant_tone", "")
            if prev_tone and curr_tone and prev_tone != curr_tone:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = ch["chapter_number"]
                beat.detected_position = ch["chapter_number"] / total
                beat.confidence = 0.35
                beat.evidence = f"Cambio de tono ({prev_tone} → {curr_tone}) en cap. {ch['chapter_number']}"
                return

    def _detect_climax(self, beat: TemplateBeat, chapters: list[dict], total: int,
                       pacing: Optional[dict]) -> None:
        """Detectar clímax: pico máximo de tensión/conflicto."""
        zone = [c for c in chapters
                if total * 0.75 <= c["chapter_number"] <= total * 0.95]
        climax_events = {"climax_moment", "conflict", "sacrifice", "death", "transformation"}

        # Buscar eventos de clímax
        for ch in zone:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in climax_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.75
                    beat.evidence = f"Evento '{ev['event_type']}' en zona de clímax"
                    return

        # Buscar capítulo con más conflicto en la zona
        if zone:
            best = max(zone, key=lambda c: c.get("conflict_interactions", 0))
            if best.get("conflict_interactions", 0) >= 1:
                beat.status = BeatStatus.POSSIBLE
                beat.detected_chapter = best["chapter_number"]
                beat.detected_position = best["chapter_number"] / total
                beat.confidence = 0.4
                beat.evidence = f"Mayor conflicto de la zona final en cap. {best['chapter_number']}"

    def _detect_resolution(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar resolución: últimos capítulos con tono menos tenso."""
        late = [c for c in chapters if c["chapter_number"] >= total * 0.85]
        resolution_events = {"resolution", "return"}

        for ch in late:
            events = ch.get("key_events", []) + ch.get("llm_events", [])
            for ev in events:
                if ev.get("event_type") in resolution_events:
                    beat.status = BeatStatus.DETECTED
                    beat.detected_chapter = ch["chapter_number"]
                    beat.detected_position = ch["chapter_number"] / total
                    beat.confidence = 0.7
                    beat.evidence = f"Evento de resolución en cap. {ch['chapter_number']}"
                    return

        if late:
            last = late[-1]
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = last["chapter_number"]
            beat.detected_position = last["chapter_number"] / total
            beat.confidence = 0.3
            beat.evidence = "Capítulo final presente (resolución implícita)"

    def _detect_theme(self, beat: TemplateBeat, chapters: list[dict], total: int) -> None:
        """Detectar tema enunciado (Save the Cat): difícil sin LLM, heurística básica."""
        # Sin LLM solo podemos detectar esto parcialmente
        early = [c for c in chapters if c["chapter_number"] <= max(2, total // 5)]
        if early:
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = early[0]["chapter_number"]
            beat.detected_position = early[0]["chapter_number"] / total
            beat.confidence = 0.2
            beat.evidence = "Posible enunciado temático en los primeros capítulos (requiere análisis LLM)"

    def _detect_falling_action(self, beat: TemplateBeat, chapters: list[dict], total: int,
                               pacing: Optional[dict]) -> None:
        """Detectar acción descendente: reducción de conflicto post-clímax."""
        zone = [c for c in chapters
                if total * 0.65 <= c["chapter_number"] <= total * 0.85]
        if not zone:
            return

        # Buscar reducción de conflicto comparando con zona de clímax
        late_conflict = [c.get("conflict_interactions", 0) for c in zone]
        if late_conflict and max(late_conflict) > 0:
            mid = zone[len(zone) // 2]
            beat.status = BeatStatus.POSSIBLE
            beat.detected_chapter = mid["chapter_number"]
            beat.detected_position = mid["chapter_number"] / total
            beat.confidence = 0.35
            beat.evidence = "Zona de transición post-conflicto detectada"

    # =========================================================================
    # Resumen
    # =========================================================================

    def _generate_summary(self, report: NarrativeTemplateReport) -> str:
        """Generar resumen del análisis de plantillas."""
        if not report.matches:
            return "No se pudieron analizar plantillas narrativas."

        best = report.best_match
        if not best:
            return "No se encontró coincidencia con ninguna plantilla."

        if best.fit_score >= 60:
            return (
                f"El manuscrito encaja mejor con «{best.template_name}» "
                f"(coincidencia del {best.fit_score:.0f}%): "
                f"{best.detected_count} de {best.total_beats} beats detectados."
            )
        elif best.fit_score >= 35:
            return (
                f"Se detectan elementos parciales de «{best.template_name}» "
                f"({best.fit_score:.0f}% de coincidencia). "
                f"El autor podría estar usando una estructura híbrida."
            )
        else:
            return (
                "No se detecta una estructura narrativa convencional clara. "
                "El manuscrito podría usar una estructura libre o experimental."
            )
