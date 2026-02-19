"""
Detector de Arquetipos de Personaje.

Clasifica personajes en arquetipos narrativos basándose en:
- Arco narrativo (growth, fall, redemption, static, circular)
- Relaciones (mentor, rival, aliado, jerárquico, romántico)
- Interacciones (tono, intensidad, frecuencia)
- Importancia (protagonista, secundario, menor)
- Presencia (distribución en capítulos, trayectoria)
- Atributos (físicos, psicológicos, rol)

Arquetipos soportados (12 de Mark & Pearson + 4 funciones narrativas de Campbell/Vogler):
- Arquetipos de personalidad (Mark & Pearson, 2001): Héroe, Inocente,
  Explorador, Sabio, Amante, Gobernante, Cuidador, Creador, Bufón, Rebelde,
  Sombra, Cambiante
- Funciones narrativas (Campbell, 1949; Vogler, 2007): Mentor, Heraldo,
  Guardián del Umbral, Embaucador (Trickster)

Nota: Jung propuso los conceptos de arquetipo y sombra como estructuras
del inconsciente colectivo, pero NO definió los 12 arquetipos de personalidad.
La taxonomía de 12 fue desarrollada por Mark & Pearson en "The Hero and
the Outlaw" (2001) adaptando ideas jungianas al análisis de marca/narrativa.

Referencias:
- Mark, M. & Pearson, C.S. "The Hero and the Outlaw" (2001) — 12 arquetipos
- Campbell, Joseph. "The Hero with a Thousand Faces" (1949) — monomito
- Vogler, Christopher. "The Writer's Journey" (2007) — funciones narrativas
- Jung, C.G. "The Archetypes and the Collective Unconscious" (1959) — marco teórico
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Tipos
# =============================================================================


class ArchetypeId(str, Enum):
    """Arquetipos de personaje."""

    HERO = "hero"
    SHADOW = "shadow"
    MENTOR = "mentor"
    HERALD = "herald"
    THRESHOLD_GUARDIAN = "threshold_guardian"
    SHAPESHIFTER = "shapeshifter"
    TRICKSTER = "trickster"
    INNOCENT = "innocent"
    EXPLORER = "explorer"
    SAGE = "sage"
    LOVER = "lover"
    RULER = "ruler"
    CAREGIVER = "caregiver"
    CREATOR = "creator"
    JESTER = "jester"
    REBEL = "rebel"


# Nombres y descripciones en español
ARCHETYPE_INFO: dict[ArchetypeId, dict] = {
    ArchetypeId.HERO: {
        "name": "Héroe",
        "description": "Protagonista que emprende un viaje, enfrenta pruebas y se transforma.",
        "icon": "pi-star",
        "color": "#3b82f6",
    },
    ArchetypeId.SHADOW: {
        "name": "Sombra",
        "description": "Antagonista o fuerza opuesta que desafía al héroe. Representa lo reprimido.",
        "icon": "pi-moon",
        "color": "#1e1b4b",
    },
    ArchetypeId.MENTOR: {
        "name": "Mentor",
        "description": "Guía sabio que prepara y aconseja al protagonista.",
        "icon": "pi-book",
        "color": "#8b5cf6",
    },
    ArchetypeId.HERALD: {
        "name": "Heraldo",
        "description": "Anuncia el cambio, trae la llamada a la aventura.",
        "icon": "pi-megaphone",
        "color": "#f59e0b",
    },
    ArchetypeId.THRESHOLD_GUARDIAN: {
        "name": "Guardián del Umbral",
        "description": "Obstáculo que el héroe debe superar para avanzar.",
        "icon": "pi-shield",
        "color": "#78716c",
    },
    ArchetypeId.SHAPESHIFTER: {
        "name": "Cambiante",
        "description": "Personaje impredecible cuya lealtad o naturaleza cambia.",
        "icon": "pi-sync",
        "color": "#06b6d4",
    },
    ArchetypeId.TRICKSTER: {
        "name": "Embaucador",
        "description": "Disruptor cómico o astuto que desafía el orden establecido.",
        "icon": "pi-sparkles",
        "color": "#f97316",
    },
    ArchetypeId.INNOCENT: {
        "name": "Inocente",
        "description": "Personaje puro, optimista, que busca la felicidad y confía en los demás.",
        "icon": "pi-sun",
        "color": "#fbbf24",
    },
    ArchetypeId.EXPLORER: {
        "name": "Explorador",
        "description": "Buscador incansable de libertad, nuevas experiencias y autodescubrimiento.",
        "icon": "pi-compass",
        "color": "#10b981",
    },
    ArchetypeId.SAGE: {
        "name": "Sabio",
        "description": "Busca la verdad y el conocimiento. Analiza, comprende y aconseja.",
        "icon": "pi-eye",
        "color": "#6366f1",
    },
    ArchetypeId.LOVER: {
        "name": "Amante",
        "description": "Movido por la pasión, la intimidad y la conexión emocional.",
        "icon": "pi-heart",
        "color": "#ec4899",
    },
    ArchetypeId.RULER: {
        "name": "Gobernante",
        "description": "Líder que busca control, orden y estabilidad. Autoridad natural.",
        "icon": "pi-crown",
        "color": "#a855f7",
    },
    ArchetypeId.CAREGIVER: {
        "name": "Cuidador",
        "description": "Protege y cuida a otros. Generoso y compasivo, a veces mártir.",
        "icon": "pi-hands",
        "color": "#14b8a6",
    },
    ArchetypeId.CREATOR: {
        "name": "Creador",
        "description": "Visionario que transforma ideas en realidad. Innovador e imaginativo.",
        "icon": "pi-palette",
        "color": "#f43f5e",
    },
    ArchetypeId.JESTER: {
        "name": "Bufón",
        "description": "Vive el momento, usa el humor para revelar verdades.",
        "icon": "pi-face-smile",
        "color": "#eab308",
    },
    ArchetypeId.REBEL: {
        "name": "Rebelde",
        "description": "Desafía las reglas y el statu quo. Busca revolución o cambio radical.",
        "icon": "pi-flag",
        "color": "#dc2626",
    },
}


@dataclass
class ArchetypeScore:
    """Puntuación de un arquetipo para un personaje."""

    archetype: ArchetypeId
    name: str
    description: str
    icon: str
    color: str
    score: float  # 0-100
    confidence: float  # 0-1
    signals: list[str] = field(default_factory=list)  # Señales que apoyan este arquetipo

    def to_dict(self) -> dict:
        return {
            "archetype": self.archetype.value,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "signals": self.signals,
        }


@dataclass
class CharacterArchetypeProfile:
    """Perfil arquetípico de un personaje."""

    character_id: int
    character_name: str
    importance: str  # protagonist, secondary, minor
    primary_archetype: ArchetypeScore | None = None
    secondary_archetype: ArchetypeScore | None = None
    all_scores: list[ArchetypeScore] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        top_scores = sorted(self.all_scores, key=lambda s: s.score, reverse=True)[:5]
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "importance": self.importance,
            "primary_archetype": self.primary_archetype.to_dict()
            if self.primary_archetype
            else None,
            "secondary_archetype": self.secondary_archetype.to_dict()
            if self.secondary_archetype
            else None,
            "top_archetypes": [s.to_dict() for s in top_scores],
            "summary": self.summary,
        }


@dataclass
class ArchetypeReport:
    """Informe completo de arquetipos del manuscrito."""

    characters: list[CharacterArchetypeProfile] = field(default_factory=list)
    archetype_distribution: dict[str, int] = field(default_factory=dict)
    ensemble_notes: list[str] = field(default_factory=list)
    protagonist_suggestion: str | None = None  # Nombre del protagonista sugerido

    def to_dict(self) -> dict:
        return {
            "characters": [c.to_dict() for c in self.characters],
            "archetype_distribution": self.archetype_distribution,
            "ensemble_notes": self.ensemble_notes,
            "protagonist_suggestion": self.protagonist_suggestion,
        }


# =============================================================================
# Señales para detección
# =============================================================================

# Mapeo de arc_type a arquetipos probables
ARC_TYPE_SIGNALS: dict[str, dict[ArchetypeId, float]] = {
    "growth": {
        ArchetypeId.HERO: 30,
        ArchetypeId.EXPLORER: 15,
        ArchetypeId.INNOCENT: 10,
    },
    "fall": {
        ArchetypeId.SHADOW: 25,
        ArchetypeId.REBEL: 15,
        ArchetypeId.RULER: 10,
    },
    "redemption": {
        ArchetypeId.HERO: 20,
        ArchetypeId.SHAPESHIFTER: 15,
        ArchetypeId.REBEL: 10,
    },
    "static": {
        ArchetypeId.SAGE: 15,
        ArchetypeId.MENTOR: 15,
        ArchetypeId.THRESHOLD_GUARDIAN: 10,
    },
    "circular": {
        ArchetypeId.TRICKSTER: 15,
        ArchetypeId.JESTER: 10,
        ArchetypeId.SHAPESHIFTER: 10,
    },
}

# Mapeo de relation_type a arquetipos
RELATION_SIGNALS: dict[str, dict[ArchetypeId, float]] = {
    "HIERARCHICAL": {ArchetypeId.RULER: 20, ArchetypeId.MENTOR: 10},
    "RIVALRY": {ArchetypeId.SHADOW: 20, ArchetypeId.REBEL: 15, ArchetypeId.THRESHOLD_GUARDIAN: 10},
    "ROMANTIC": {ArchetypeId.LOVER: 25, ArchetypeId.INNOCENT: 5},
    "FRIENDSHIP": {ArchetypeId.CAREGIVER: 10, ArchetypeId.JESTER: 5},
    "FAMILY": {ArchetypeId.CAREGIVER: 10, ArchetypeId.INNOCENT: 5},
    "PROFESSIONAL": {ArchetypeId.SAGE: 10, ArchetypeId.RULER: 10},
}

# Mapeo de subtipo de relación
SUBTYPE_SIGNALS: dict[str, dict[ArchetypeId, float]] = {
    "mentor": {ArchetypeId.MENTOR: 35, ArchetypeId.SAGE: 15},
    "jefe": {ArchetypeId.RULER: 20},
    "enemigo": {ArchetypeId.SHADOW: 25, ArchetypeId.THRESHOLD_GUARDIAN: 10},
    "rival": {ArchetypeId.SHADOW: 15, ArchetypeId.REBEL: 10},
    "protector": {ArchetypeId.CAREGIVER: 25, ArchetypeId.THRESHOLD_GUARDIAN: 10},
    "discípulo": {ArchetypeId.INNOCENT: 15, ArchetypeId.HERO: 10},
    "aliado": {ArchetypeId.CAREGIVER: 10},
    "subordinado": {ArchetypeId.THRESHOLD_GUARDIAN: 10},
}


# =============================================================================
# Analizador
# =============================================================================


class CharacterArchetypeAnalyzer:
    """
    Analiza personajes y les asigna arquetipos de Mark & Pearson / Campbell.

    Usa datos ya analizados: arcos, relaciones, interacciones,
    importancia y presencia en el manuscrito.
    """

    def analyze(
        self,
        entities: list[dict],
        character_arcs: list[dict],
        relationships: list[dict],
        interactions: list[dict],
        total_chapters: int,
        profiles: list[dict] | None = None,
    ) -> ArchetypeReport:
        """
        Analizar arquetipos de todos los personajes.

        Args:
            entities: Lista de entidades (dicts con name, importance, mention_count, etc.)
            character_arcs: Arcos de personaje (dicts con arc_type, trajectory, etc.)
            relationships: Relaciones (dicts con entity1_id, entity2_id, relation_type, subtype, etc.)
            interactions: Interacciones (dicts con entity1_id, entity2_id, tone, intensity, etc.)
            total_chapters: Número total de capítulos
            profiles: Perfiles de CharacterProfiler (dicts con narrative_relevance, role, etc.)

        Returns:
            ArchetypeReport
        """
        report = ArchetypeReport()
        characters = [e for e in entities if e.get("entity_type") == "character"]

        if not characters:
            return report

        # Indexar arcos por character_id
        arcs_by_id = {}
        for arc in character_arcs:
            cid = arc.get("character_id")
            if cid is not None:
                arcs_by_id[cid] = arc

        # Indexar relaciones por entity_id
        rels_by_id: dict[int, list[dict]] = {}
        for rel in relationships:
            for eid in [rel.get("entity1_id"), rel.get("entity2_id")]:
                if eid is not None:
                    rels_by_id.setdefault(eid, []).append(rel)

        # Indexar interacciones por entity_id
        ints_by_id: dict[int, list[dict]] = {}
        for inter in interactions:
            for eid in [inter.get("entity1_id"), inter.get("entity2_id")]:
                if eid is not None:
                    ints_by_id.setdefault(eid, []).append(inter)

        # Indexar perfiles por character name (el profiler usa names)
        profiles_by_name: dict[str, dict] = {}
        if profiles:
            for prof in profiles:
                pname = prof.get("character_name", "")
                if pname:
                    profiles_by_name[pname] = prof

        # Analizar cada personaje
        for char in characters:
            cid = char.get("id") or char.get("entity_id")
            char_name = char.get("name") or char.get("canonical_name", "")
            profile = self._analyze_character(
                char=char,
                arc=arcs_by_id.get(cid),
                relations=rels_by_id.get(cid, []),
                interactions=ints_by_id.get(cid, []),
                total_chapters=total_chapters,
                char_profile=profiles_by_name.get(char_name),
            )
            report.characters.append(profile)

        # Distribución de arquetipos
        for profile in report.characters:
            if profile.primary_archetype:
                key = profile.primary_archetype.name
                report.archetype_distribution[key] = report.archetype_distribution.get(key, 0) + 1

        # Notas del elenco
        report.ensemble_notes = self._analyze_ensemble(report.characters)

        # Identificar protagonista sugerido
        hero_chars = [
            c for c in report.characters
            if c.primary_archetype and c.primary_archetype.archetype == ArchetypeId.HERO
        ]
        if hero_chars:
            # Si hay un solo héroe, es el protagonista
            best = max(hero_chars, key=lambda c: c.primary_archetype.score)
            report.protagonist_suggestion = best.character_name
        elif report.characters:
            # Sin héroe claro: sugerir el de mayor importancia
            protagonist_chars = [
                c for c in report.characters if c.importance in ("principal", "protagonist")
            ]
            if protagonist_chars:
                report.protagonist_suggestion = protagonist_chars[0].character_name

        return report

    def _analyze_character(
        self,
        char: dict,
        arc: dict | None,
        relations: list[dict],
        interactions: list[dict],
        total_chapters: int,
        char_profile: dict | None = None,
    ) -> CharacterArchetypeProfile:
        """Analizar arquetipos de un personaje individual."""
        cid = char.get("id") or char.get("entity_id", 0)
        name = char.get("name") or char.get("canonical_name", "Desconocido")
        importance = char.get("importance", "secondary")

        # Si tenemos profiling, usar el role asignado para overridear importance
        if char_profile:
            role = char_profile.get("role", "")
            if role == "protagonist":
                importance = "principal"
            elif role == "deuteragonist":
                importance = "high"

        # Inicializar scores
        scores: dict[ArchetypeId, float] = dict.fromkeys(ArchetypeId, 0.0)
        signals: dict[ArchetypeId, list[str]] = {a: [] for a in ArchetypeId}

        # --- Señal 1: Importancia ---
        self._score_importance(importance, scores, signals)

        # --- Señal 2: Arco narrativo ---
        if arc:
            self._score_arc(arc, scores, signals)

        # --- Señal 3: Relaciones ---
        self._score_relations(relations, cid, scores, signals)

        # --- Señal 4: Interacciones ---
        self._score_interactions(interactions, cid, scores, signals)

        # --- Señal 5: Presencia ---
        self._score_presence(char, total_chapters, scores, signals)

        # --- Señal 6: Centralidad narrativa (profiling) ---
        if char_profile:
            self._score_narrative_centrality(char_profile, scores, signals)

        # Preservar raw_scores para calcular confianza basada en evidencia real
        raw_scores = dict(scores)

        # Normalizar scores a 0-100
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            for archetype in scores:
                scores[archetype] = (scores[archetype] / max_score) * 100

        # Crear lista de ArchetypeScore
        all_scores = []
        for archetype_id, score in scores.items():
            info = ARCHETYPE_INFO[archetype_id]
            # Confianza basada en evidencia bruta (raw_score), no normalizada
            raw = raw_scores.get(archetype_id, 0)
            if raw >= 40:
                confidence = min(1.0, 0.7 + (raw - 40) / 100)
            elif raw >= 20:
                confidence = 0.4 + (raw - 20) / 50
            elif raw > 0:
                confidence = 0.1 + raw / 40
            else:
                confidence = 0.0
            all_scores.append(
                ArchetypeScore(
                    archetype=archetype_id,
                    name=info["name"],
                    description=info["description"],
                    icon=info["icon"],
                    color=info["color"],
                    score=score,
                    confidence=confidence,
                    signals=signals[archetype_id],
                )
            )

        all_scores.sort(key=lambda s: s.score, reverse=True)

        primary = all_scores[0] if all_scores and all_scores[0].score > 0 else None
        secondary = all_scores[1] if len(all_scores) > 1 and all_scores[1].score > 10 else None

        summary = self._generate_character_summary(name, primary, secondary)

        return CharacterArchetypeProfile(
            character_id=cid,
            character_name=name,
            importance=importance,
            primary_archetype=primary,
            secondary_archetype=secondary,
            all_scores=all_scores,
            summary=summary,
        )

    # =========================================================================
    # Scorers
    # =========================================================================

    def _score_importance(
        self,
        importance: str,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Puntuar según importancia del personaje.

        Maneja tanto valores legacy (protagonist/secondary/minor) como
        los actuales de EntityImportance (principal/high/medium/low/minimal).
        """
        # Normalizar: mapear EntityImportance values al tier arquetípico
        importance_lower = importance.lower() if importance else ""
        if importance_lower in ("protagonist", "principal"):
            # Protagonista / importancia principal
            scores[ArchetypeId.HERO] += 10
            scores[ArchetypeId.EXPLORER] += 5
            scores[ArchetypeId.REBEL] += 5
            scores[ArchetypeId.LOVER] += 5
            scores[ArchetypeId.RULER] += 5
            signals[ArchetypeId.HERO].append("Protagonista del manuscrito")
        elif importance_lower in ("secondary", "high", "primary"):
            # Co-protagonista / importancia alta
            scores[ArchetypeId.MENTOR] += 8
            scores[ArchetypeId.SHADOW] += 8
            scores[ArchetypeId.CAREGIVER] += 5
            scores[ArchetypeId.THRESHOLD_GUARDIAN] += 5
        elif importance_lower in ("medium",):
            # Importancia media — aún puede tener funciones narrativas
            scores[ArchetypeId.MENTOR] += 5
            scores[ArchetypeId.SHADOW] += 5
            scores[ArchetypeId.CAREGIVER] += 3
            scores[ArchetypeId.THRESHOLD_GUARDIAN] += 3
        elif importance_lower in ("minor", "low"):
            scores[ArchetypeId.HERALD] += 8
            scores[ArchetypeId.TRICKSTER] += 5
            scores[ArchetypeId.JESTER] += 5
        elif importance_lower in ("minimal", "mentioned"):
            scores[ArchetypeId.HERALD] += 5
            scores[ArchetypeId.THRESHOLD_GUARDIAN] += 3

    def _score_arc(
        self,
        arc: dict,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Puntuar según el arco narrativo del personaje."""
        arc_type = arc.get("arc_type", "static")
        trajectory = arc.get("trajectory", "stable")
        completeness = arc.get("completeness", 0)

        # Señales por tipo de arco
        arc_signals = {
            "growth": {ArchetypeId.HERO: 25, ArchetypeId.EXPLORER: 12, ArchetypeId.INNOCENT: 8},
            "fall": {ArchetypeId.SHADOW: 20, ArchetypeId.REBEL: 12, ArchetypeId.RULER: 8},
            "redemption": {
                ArchetypeId.HERO: 18,
                ArchetypeId.SHAPESHIFTER: 12,
                ArchetypeId.REBEL: 8,
            },
            "static": {
                ArchetypeId.SAGE: 12,
                ArchetypeId.MENTOR: 12,
                ArchetypeId.THRESHOLD_GUARDIAN: 8,
            },
            "circular": {
                ArchetypeId.TRICKSTER: 12,
                ArchetypeId.JESTER: 8,
                ArchetypeId.SHAPESHIFTER: 8,
            },
        }

        if arc_type in arc_signals:
            for archetype, bonus in arc_signals[arc_type].items():
                scores[archetype] += bonus
                if bonus >= 12:
                    signals[archetype].append(f"Arco de tipo '{arc_type}'")

        # Trayectoria
        if trajectory == "rising":
            scores[ArchetypeId.HERO] += 10
            scores[ArchetypeId.EXPLORER] += 5
        elif trajectory == "declining":
            scores[ArchetypeId.SHADOW] += 10
            scores[ArchetypeId.REBEL] += 5
        elif trajectory == "stable":
            scores[ArchetypeId.SAGE] += 5
            scores[ArchetypeId.MENTOR] += 5

        # Completitud alta → arcos más definidos
        if completeness >= 0.7:
            scores[ArchetypeId.HERO] += 8
            signals[ArchetypeId.HERO].append(f"Arco completo ({completeness:.0%})")

    def _score_relations(
        self,
        relations: list[dict],
        char_id: int,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Puntuar según relaciones del personaje."""
        for rel in relations:
            rel_type = rel.get("relation_type", "")
            subtype = (rel.get("subtype") or "").lower()

            # Señales por tipo de relación
            rel_signals = {
                "HIERARCHICAL": {ArchetypeId.RULER: 15, ArchetypeId.MENTOR: 8},
                "RIVALRY": {
                    ArchetypeId.SHADOW: 15,
                    ArchetypeId.REBEL: 10,
                    ArchetypeId.THRESHOLD_GUARDIAN: 8,
                },
                "ROMANTIC": {ArchetypeId.LOVER: 20, ArchetypeId.INNOCENT: 5},
                "FRIENDSHIP": {ArchetypeId.CAREGIVER: 8, ArchetypeId.JESTER: 5},
                "FAMILY": {ArchetypeId.CAREGIVER: 8, ArchetypeId.INNOCENT: 5},
                "PROFESSIONAL": {ArchetypeId.SAGE: 8, ArchetypeId.RULER: 8},
            }

            if rel_type in rel_signals:
                for archetype, bonus in rel_signals[rel_type].items():
                    scores[archetype] += bonus
                    if bonus >= 15:
                        signals[archetype].append(f"Relación de tipo '{rel_type}'")

            # Subtipos específicos
            if "mentor" in subtype:
                scores[ArchetypeId.MENTOR] += 25
                signals[ArchetypeId.MENTOR].append("Subtipo de relación: mentor")
            elif "enemigo" in subtype or "rival" in subtype:
                scores[ArchetypeId.SHADOW] += 15
                signals[ArchetypeId.SHADOW].append(f"Subtipo de relación: {subtype}")
            elif "protector" in subtype:
                scores[ArchetypeId.CAREGIVER] += 18
                signals[ArchetypeId.CAREGIVER].append("Subtipo de relación: protector")
            elif "jefe" in subtype or "líder" in subtype:
                scores[ArchetypeId.RULER] += 15
                signals[ArchetypeId.RULER].append(f"Subtipo de relación: {subtype}")

    def _score_interactions(
        self,
        interactions: list[dict],
        char_id: int,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Puntuar según interacciones del personaje."""
        if not interactions:
            return

        positive = 0
        negative = 0
        neutral = 0
        dialogue_count = 0
        high_intensity = 0

        for inter in interactions:
            tone = inter.get("tone", "NEUTRAL")
            intensity = inter.get("intensity", 0.5)
            i_type = inter.get("interaction_type", "")

            if tone == "POSITIVE":
                positive += 1
            elif tone == "NEGATIVE":
                negative += 1
            else:
                neutral += 1

            if i_type == "DIALOGUE":
                dialogue_count += 1

            if intensity >= 0.7:
                high_intensity += 1

        total = len(interactions)

        # Tono predominantemente positivo
        if total > 0 and positive / total >= 0.6:
            scores[ArchetypeId.CAREGIVER] += 10
            scores[ArchetypeId.INNOCENT] += 8
            signals[ArchetypeId.CAREGIVER].append(f"{positive}/{total} interacciones positivas")

        # Tono predominantemente negativo
        if total > 0 and negative / total >= 0.5:
            scores[ArchetypeId.SHADOW] += 12
            scores[ArchetypeId.REBEL] += 8
            signals[ArchetypeId.SHADOW].append(f"{negative}/{total} interacciones negativas")

        # Mucho diálogo
        if dialogue_count >= 5:
            scores[ArchetypeId.SAGE] += 8
            scores[ArchetypeId.JESTER] += 5
            scores[ArchetypeId.MENTOR] += 5
            signals[ArchetypeId.SAGE].append(f"{dialogue_count} diálogos")

        # Alta intensidad
        if high_intensity >= 3:
            scores[ArchetypeId.HERO] += 8
            scores[ArchetypeId.REBEL] += 5
            signals[ArchetypeId.HERO].append(f"{high_intensity} interacciones de alta intensidad")

    def _score_presence(
        self,
        char: dict,
        total_chapters: int,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Puntuar según patrones de presencia del personaje."""
        mentions = char.get("mention_count", 0)
        chapters_present = char.get("chapters_present", 0)

        if total_chapters == 0:
            return

        presence_ratio = chapters_present / total_chapters if total_chapters > 0 else 0

        # Alta presencia → protagonista / héroe
        if presence_ratio >= 0.7:
            scores[ArchetypeId.HERO] += 10
            scores[ArchetypeId.EXPLORER] += 5
        elif presence_ratio >= 0.4:
            scores[ArchetypeId.MENTOR] += 5
            scores[ArchetypeId.SHADOW] += 5
        elif presence_ratio <= 0.15 and mentions >= 3:
            # Aparición breve pero significativa
            scores[ArchetypeId.HERALD] += 15
            scores[ArchetypeId.THRESHOLD_GUARDIAN] += 10
            signals[ArchetypeId.HERALD].append(
                f"Aparición breve pero significativa ({chapters_present} capítulos, {mentions} menciones)"
            )

        # Muchas menciones relativas → personaje central
        if mentions >= 50:
            scores[ArchetypeId.HERO] += 8

    def _score_narrative_centrality(
        self,
        char_profile: dict,
        scores: dict[ArchetypeId, float],
        signals: dict[ArchetypeId, list[str]],
    ) -> None:
        """Señal 6: Centralidad narrativa basada en CharacterProfiler.

        Usa narrative_relevance (0-1), role y agency_score del sistema de
        profiling de 6 indicadores para diferenciar arquetipos.
        """
        relevance = char_profile.get("narrative_relevance", 0)
        role = char_profile.get("role", "")
        agency = char_profile.get("agency_score", 0)

        # Protagonista (>= 0.7 relevance) → fuerte señal heroica
        if role == "protagonist" or relevance >= 0.7:
            scores[ArchetypeId.HERO] += 20
            scores[ArchetypeId.EXPLORER] += 8
            signals[ArchetypeId.HERO].append(
                f"Centralidad narrativa alta ({relevance:.0%})"
            )
        # Deuteragonista (>= 0.45) → funciones de soporte importantes
        elif role == "deuteragonist" or relevance >= 0.45:
            scores[ArchetypeId.MENTOR] += 10
            scores[ArchetypeId.SHADOW] += 10
            scores[ArchetypeId.CAREGIVER] += 5
            signals[ArchetypeId.MENTOR].append(
                f"Centralidad narrativa media ({relevance:.0%})"
            )
        # Supporting (>= 0.2) → funciones puntuales
        elif role == "supporting" or relevance >= 0.2:
            scores[ArchetypeId.HERALD] += 8
            scores[ArchetypeId.THRESHOLD_GUARDIAN] += 8
        # Minor/mentioned → presencia testimonial
        elif relevance < 0.2:
            scores[ArchetypeId.HERALD] += 5

        # Agency score: personajes activos vs pasivos
        if agency >= 0.7:
            scores[ArchetypeId.HERO] += 8
            scores[ArchetypeId.REBEL] += 5
            scores[ArchetypeId.RULER] += 5
            signals[ArchetypeId.HERO].append(
                f"Alta agentividad ({agency:.0%})"
            )
        elif agency <= 0.3 and relevance >= 0.3:
            scores[ArchetypeId.INNOCENT] += 8
            scores[ArchetypeId.CAREGIVER] += 5

    # =========================================================================
    # Generación de resumen y notas de elenco
    # =========================================================================

    def _generate_character_summary(
        self,
        name: str,
        primary: ArchetypeScore | None,
        secondary: ArchetypeScore | None,
    ) -> str:
        """Generar resumen del perfil arquetípico de un personaje."""
        if not primary or primary.score < 5:
            return f"No se detectaron señales arquetípicas claras para «{name}»."

        parts = [f"«{name}» encaja con el arquetipo de **{primary.name}**"]
        if primary.confidence >= 0.5:
            parts[0] += f" (confianza {primary.confidence:.0%})"

        if secondary and secondary.score > 20:
            parts.append(f" con rasgos de **{secondary.name}**")

        if primary.signals:
            parts.append(f". Señales: {'; '.join(primary.signals[:3])}")

        return "".join(parts) + "."

    def _analyze_ensemble(self, characters: list[CharacterArchetypeProfile]) -> list[str]:
        """Analizar el elenco como conjunto. Detectar ausencias y equilibrios."""
        notes = []

        # Contar arquetipos primarios
        primary_types = set()
        for ch in characters:
            if ch.primary_archetype:
                primary_types.add(ch.primary_archetype.archetype)

        # ¿Hay héroe?
        has_hero = ArchetypeId.HERO in primary_types
        has_shadow = ArchetypeId.SHADOW in primary_types
        has_mentor = ArchetypeId.MENTOR in primary_types

        if not has_hero and len(characters) >= 3:
            notes.append(
                "No se detectó un Héroe claro en el elenco. "
                "Esto puede indicar un protagonismo coral o un liderazgo narrativo difuso."
            )

        if has_hero and not has_shadow and len(characters) >= 3:
            notes.append(
                "No se detectó una Sombra/Antagonista clara. "
                "El conflicto puede canalizarse de forma interna o ambiental."
            )

        if has_hero and not has_mentor and len(characters) >= 4:
            notes.append(
                "No se detectó un Mentor entre los personajes analizados. "
                "No todas las estructuras narrativas requieren esta función."
            )

        # Detectar arquetipos duplicados (el caso que motivó esta mejora)
        archetype_chars: dict[ArchetypeId, list[str]] = {}
        for ch in characters:
            if ch.primary_archetype:
                aid = ch.primary_archetype.archetype
                archetype_chars.setdefault(aid, []).append(ch.character_name)
        for aid, names in archetype_chars.items():
            if len(names) >= 2:
                info = ARCHETYPE_INFO[aid]
                names_str = " y ".join(f"«{n}»" for n in names[:3])
                notes.append(
                    f"{names_str} comparten el arquetipo de **{info['name']}**. "
                    "Los personajes pueden cumplir la misma función narrativa "
                    "o tener rasgos diferenciadores no captados por el texto analizado."
                )

        # Diversidad de arquetipos
        if len(characters) >= 5 and len(primary_types) <= 2:
            notes.append(
                f"Los {len(characters)} personajes comparten solo "
                f"{len(primary_types)} arquetipos distintos. "
                "Puede ser una elección temática intencionada o una "
                "oportunidad de diferenciación."
            )

        # Flat arc recognition (K.M. Weiland)
        static_chars = []
        for ch in characters:
            for score in ch.all_scores:
                if any("static" in s for s in score.signals):
                    static_chars.append(ch.character_name)
                    break
        if static_chars:
            names = ", ".join(f"«{n}»" for n in static_chars[:3])
            notes.append(
                f"Se detectaron arcos estáticos en {names}. "
                "Un arco estático no implica ausencia de desarrollo: "
                "puede tratarse de un 'flat arc' donde el personaje "
                "transforma su entorno sin cambiar él mismo."
            )

        if not notes:
            notes.append(
                f"El elenco de {len(characters)} personajes muestra "
                f"{len(primary_types)} arquetipos distintos."
            )

        return notes
