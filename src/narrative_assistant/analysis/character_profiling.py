"""
Perfilado de personajes con 6 indicadores.

Construye un perfil completo de cada personaje basado en:
1. Presencia: frecuencia y distribución de menciones por capítulo
2. Acciones: verbos y acciones asociados al personaje
3. Habla: métricas del diálogo (delegado a VoiceProfileBuilder)
4. Definición: atributos explícitos asignados al personaje
5. Sentimiento: polaridad emocional asociada
6. Entornos: ubicaciones donde aparece el personaje

El perfil se usa para:
- Detectar comportamiento fuera de personaje (out-of-character)
- Medir relevancia narrativa (protagonista vs. figurante)
- Analizar evolución a lo largo de la obra
"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CharacterRole(Enum):
    """Rol narrativo estimado del personaje."""

    PROTAGONIST = "protagonist"
    DEUTERAGONIST = "deuteragonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    MENTIONED = "mentioned"


@dataclass
class PresenceIndicator:
    """Indicador 1: Presencia narrativa."""

    total_mentions: int = 0
    chapters_present: list[int] = field(default_factory=list)
    mentions_per_chapter: dict[int, int] = field(default_factory=dict)
    first_appearance_chapter: int | None = None
    last_appearance_chapter: int | None = None
    continuity: float = 0.0  # % de capítulos donde aparece

    @property
    def chapter_span(self) -> int:
        """Número de capítulos entre primera y última aparición."""
        if self.first_appearance_chapter is None or self.last_appearance_chapter is None:
            return 0
        return self.last_appearance_chapter - self.first_appearance_chapter + 1


@dataclass
class ActionIndicator:
    """Indicador 2: Acciones del personaje."""

    action_verbs: Counter = field(default_factory=Counter)
    action_count: int = 0
    # Categorías de acción
    physical_actions: int = 0  # correr, golpear, abrazar
    verbal_actions: int = 0  # decir, gritar, susurrar
    mental_actions: int = 0  # pensar, recordar, decidir
    social_actions: int = 0  # ayudar, traicionar, prometer
    # Agentividad: ratio acciones activas / pasivas
    agency_score: float = 0.5  # 0=pasivo, 1=activo


@dataclass
class SpeechIndicator:
    """Indicador 3: Perfil de habla."""

    total_interventions: int = 0
    total_words: int = 0
    avg_length: float = 0.0
    formality_score: float = 0.5  # 0=informal, 1=formal
    question_ratio: float = 0.0
    exclamation_ratio: float = 0.0
    # Delegado a VoiceProfileBuilder para detalles


@dataclass
class DefinitionIndicator:
    """Indicador 4: Atributos explícitos."""

    physical_attributes: dict[str, str] = field(default_factory=dict)
    psychological_attributes: dict[str, str] = field(default_factory=dict)
    social_attributes: dict[str, str] = field(default_factory=dict)
    attribute_count: int = 0
    # Evolución: atributos que cambian
    evolving_attributes: list[str] = field(default_factory=list)


@dataclass
class SentimentIndicator:
    """Indicador 5: Polaridad emocional."""

    positive_mentions: int = 0
    negative_mentions: int = 0
    neutral_mentions: int = 0
    avg_sentiment: float = 0.0  # -1 a +1
    # Emociones dominantes
    dominant_emotions: list[tuple[str, int]] = field(default_factory=list)
    # Evolución emocional por capítulo
    sentiment_by_chapter: dict[int, float] = field(default_factory=dict)


@dataclass
class EnvironmentIndicator:
    """Indicador 6: Entornos asociados."""

    locations: Counter = field(default_factory=Counter)
    primary_location: str | None = None
    location_changes: int = 0
    # Entornos por capítulo
    locations_by_chapter: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class CharacterProfile:
    """Perfil completo de un personaje con 6 indicadores."""

    entity_id: int
    entity_name: str
    role: CharacterRole = CharacterRole.MINOR

    presence: PresenceIndicator = field(default_factory=PresenceIndicator)
    actions: ActionIndicator = field(default_factory=ActionIndicator)
    speech: SpeechIndicator = field(default_factory=SpeechIndicator)
    definition: DefinitionIndicator = field(default_factory=DefinitionIndicator)
    sentiment: SentimentIndicator = field(default_factory=SentimentIndicator)
    environment: EnvironmentIndicator = field(default_factory=EnvironmentIndicator)

    # Puntuación global de relevancia narrativa (0-1)
    narrative_relevance: float = 0.0

    def to_dict(self) -> dict:
        """Convierte el perfil a diccionario serializable."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "role": self.role.value,
            "narrative_relevance": round(self.narrative_relevance, 3),
            "presence": {
                "total_mentions": self.presence.total_mentions,
                "chapters_present": self.presence.chapters_present,
                "first_chapter": self.presence.first_appearance_chapter,
                "last_chapter": self.presence.last_appearance_chapter,
                "continuity": round(self.presence.continuity, 3),
                "mentions_per_chapter": dict(self.presence.mentions_per_chapter),
            },
            "actions": {
                "count": self.actions.action_count,
                "top_verbs": self.actions.action_verbs.most_common(10),
                "physical": self.actions.physical_actions,
                "verbal": self.actions.verbal_actions,
                "mental": self.actions.mental_actions,
                "social": self.actions.social_actions,
                "agency": round(self.actions.agency_score, 3),
            },
            "speech": {
                "interventions": self.speech.total_interventions,
                "words": self.speech.total_words,
                "avg_length": round(self.speech.avg_length, 1),
                "formality": round(self.speech.formality_score, 3),
            },
            "definition": {
                "physical": self.definition.physical_attributes,
                "psychological": self.definition.psychological_attributes,
                "social": self.definition.social_attributes,
                "total_attributes": self.definition.attribute_count,
            },
            "sentiment": {
                "avg": round(self.sentiment.avg_sentiment, 3),
                "positive": self.sentiment.positive_mentions,
                "negative": self.sentiment.negative_mentions,
                "dominant_emotions": self.sentiment.dominant_emotions[:5],
                "by_chapter": dict(self.sentiment.sentiment_by_chapter),
            },
            "environment": {
                "primary_location": self.environment.primary_location,
                "locations": self.environment.locations.most_common(5),
                "changes": self.environment.location_changes,
                "locations_by_chapter": dict(self.environment.locations_by_chapter),
            },
        }


# Verbos de acción categorizados
PHYSICAL_VERBS = {
    "correr", "caminar", "saltar", "golpear", "abrazar", "besar",
    "empujar", "tirar", "coger", "soltar", "subir", "bajar",
    "abrir", "cerrar", "romper", "lanzar", "luchar", "huir",
    "caer", "levantar", "sentar", "acostar", "comer", "beber",
    "dormir", "despertar", "vestir", "matar", "herir", "tocar",
}

VERBAL_VERBS = {
    "decir", "hablar", "gritar", "susurrar", "murmurar", "exclamar",
    "preguntar", "responder", "contar", "explicar", "ordenar",
    "suplicar", "rogar", "insultar", "mentir", "confesar",
    "prometer", "jurar", "amenazar", "cantar", "rezar", "leer",
}

MENTAL_VERBS = {
    "pensar", "creer", "saber", "recordar", "olvidar", "decidir",
    "querer", "desear", "temer", "esperar", "sospechar", "dudar",
    "imaginar", "soñar", "comprender", "entender", "intuir",
    "sentir", "amar", "odiar", "envidiar", "observar", "notar",
}

SOCIAL_VERBS = {
    "ayudar", "traicionar", "proteger", "abandonar", "salvar",
    "castigar", "perdonar", "engañar", "seducir", "convencer",
    "manipular", "obedecer", "mandar", "servir", "acompañar",
    "visitar", "invitar", "rechazar", "aceptar", "negociar",
}

# Verbos pasivos / de estado
PASSIVE_VERBS = {
    "ser", "estar", "parecer", "resultar", "quedar",
    "permanecer", "yacer", "sufrir", "padecer", "recibir",
}

# Patrón para detectar sujeto + verbo (simplificado)
SUBJECT_VERB_PATTERN = re.compile(
    r"(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)"
    r"\s+(?P<verb>[a-záéíóúñ]+(?:ó|aba|ió|ía|ó|ando|endo))\b",
    re.UNICODE,
)

# Palabras de sentimiento positivo/negativo (simplificadas)
POSITIVE_WORDS = {
    "feliz", "alegre", "contento", "satisfecho", "orgulloso",
    "amable", "generoso", "valiente", "esperanza", "amor",
    "sonreír", "reír", "abrazar", "celebrar", "triunfo",
    "paz", "calma", "ilusión", "cariño", "ternura",
}

NEGATIVE_WORDS = {
    "triste", "furioso", "enfadado", "asustado", "desesperado",
    "cruel", "cobarde", "egoísta", "miedo", "odio",
    "llorar", "gritar", "golpear", "sufrir", "dolor",
    "muerte", "venganza", "traición", "culpa", "angustia",
}


class CharacterProfiler:
    """
    Construye perfiles de 6 indicadores para cada personaje.

    Se alimenta de datos ya extraídos por el pipeline (menciones,
    atributos, diálogos, eventos de ubicación, sentimiento).
    """

    # Pesos para calcular relevancia narrativa
    RELEVANCE_WEIGHTS = {
        "presence": 0.30,
        "actions": 0.20,
        "speech": 0.20,
        "definition": 0.10,
        "sentiment": 0.10,
        "environment": 0.10,
    }

    # Umbrales para clasificar rol
    ROLE_THRESHOLDS = {
        CharacterRole.PROTAGONIST: 0.7,
        CharacterRole.DEUTERAGONIST: 0.45,
        CharacterRole.SUPPORTING: 0.2,
        CharacterRole.MINOR: 0.05,
        # Por debajo: MENTIONED
    }

    def __init__(self, total_chapters: int = 1):
        self.total_chapters = max(total_chapters, 1)
        self._profiles: dict[int, CharacterProfile] = {}

    def build_profiles(
        self,
        mentions: list[dict],
        attributes: list[dict] | None = None,
        dialogues: list[dict] | None = None,
        location_events: list[dict] | None = None,
        chapter_texts: dict[int, str] | None = None,
    ) -> list[CharacterProfile]:
        """
        Construye perfiles para todos los personajes.

        Args:
            mentions: Lista de menciones con entity_id, entity_name, chapter
            attributes: Lista de atributos extraídos
            dialogues: Lista de diálogos con speaker_id, text, chapter
            location_events: Lista de eventos de ubicación
            chapter_texts: Textos de capítulos (para acción/sentimiento)

        Returns:
            Lista de perfiles de personaje ordenados por relevancia.
        """
        self._profiles.clear()

        # 1. Presencia
        self._build_presence(mentions)

        # 2. Acciones (requiere textos de capítulos)
        if chapter_texts:
            self._build_actions(chapter_texts)

        # 3. Habla
        if dialogues:
            self._build_speech(dialogues)

        # 4. Definición (atributos)
        if attributes:
            self._build_definition(attributes)

        # 5. Sentimiento
        if chapter_texts:
            self._build_sentiment(chapter_texts)

        # 6. Entornos
        if location_events:
            self._build_environment(location_events)

        # Calcular relevancia y rol
        self._calculate_relevance()
        self._assign_roles()

        # Ordenar por relevancia
        profiles = sorted(
            self._profiles.values(),
            key=lambda p: p.narrative_relevance,
            reverse=True,
        )

        logger.info(
            f"Perfilados {len(profiles)} personajes. "
            f"Protagonista(s): {[p.entity_name for p in profiles if p.role == CharacterRole.PROTAGONIST]}"
        )

        return profiles

    def _get_or_create_profile(self, entity_id: int, entity_name: str) -> CharacterProfile:
        """Obtiene o crea perfil para un personaje."""
        if entity_id not in self._profiles:
            self._profiles[entity_id] = CharacterProfile(
                entity_id=entity_id,
                entity_name=entity_name,
            )
        return self._profiles[entity_id]

    def _build_presence(self, mentions: list[dict]) -> None:
        """Construye indicador de presencia a partir de menciones."""
        for mention in mentions:
            entity_id = mention.get("entity_id")
            entity_name = mention.get("entity_name", "")
            chapter = mention.get("chapter", 0)

            if entity_id is None:
                continue

            profile = self._get_or_create_profile(entity_id, entity_name)
            profile.presence.total_mentions += 1
            profile.presence.mentions_per_chapter[chapter] = (
                profile.presence.mentions_per_chapter.get(chapter, 0) + 1
            )

        # Calcular estadísticas derivadas
        for profile in self._profiles.values():
            p = profile.presence
            chapters = sorted(p.mentions_per_chapter.keys())
            p.chapters_present = chapters
            if chapters:
                p.first_appearance_chapter = chapters[0]
                p.last_appearance_chapter = chapters[-1]
                p.continuity = len(chapters) / self.total_chapters

    def _build_actions(self, chapter_texts: dict[int, str]) -> None:
        """Extrae acciones asociadas a cada personaje de los textos."""
        entity_names = {
            p.entity_name.lower(): p.entity_id
            for p in self._profiles.values()
        }

        for _chapter_num, text in chapter_texts.items():
            # Buscar patrones nombre + verbo
            for match in SUBJECT_VERB_PATTERN.finditer(text):
                name = match.group("name").lower()
                verb_form = match.group("verb").lower()

                # Verificar si el nombre corresponde a un personaje
                entity_id = entity_names.get(name)
                if entity_id is None:
                    continue

                profile = self._profiles[entity_id]
                profile.actions.action_count += 1
                profile.actions.action_verbs[verb_form] += 1

                # Categorizar acción por tipo de verbo
                for verb_set, attr in [
                    (PHYSICAL_VERBS, "physical_actions"),
                    (VERBAL_VERBS, "verbal_actions"),
                    (MENTAL_VERBS, "mental_actions"),
                    (SOCIAL_VERBS, "social_actions"),
                ]:
                    if any(verb_form.startswith(v[:4]) for v in verb_set):
                        setattr(profile.actions, attr, getattr(profile.actions, attr) + 1)
                        break

        # Calcular agentividad
        for profile in self._profiles.values():
            a = profile.actions
            if a.action_count > 0:
                passive = sum(
                    1 for v in a.action_verbs
                    if any(v.startswith(pv[:3]) for pv in PASSIVE_VERBS)
                )
                active = a.action_count - passive
                a.agency_score = active / a.action_count

    def _build_speech(self, dialogues: list[dict]) -> None:
        """Construye indicador de habla a partir de diálogos."""
        dialogues_by_speaker: dict[int, list[str]] = defaultdict(list)

        for dialogue in dialogues:
            speaker_id = dialogue.get("speaker_id")
            text = dialogue.get("text", "")
            if speaker_id is not None and speaker_id in self._profiles and text:
                dialogues_by_speaker[speaker_id].append(text)

        for entity_id, texts in dialogues_by_speaker.items():
            profile = self._profiles[entity_id]
            s = profile.speech

            s.total_interventions = len(texts)
            word_counts = [len(t.split()) for t in texts]
            s.total_words = sum(word_counts)
            s.avg_length = s.total_words / len(texts) if texts else 0

            # Formalidad simplificada
            from ..voice.profiles import (
                FORMAL_MARKERS as _FORMAL,
            )
            from ..voice.profiles import (
                INFORMAL_MARKERS as _INFORMAL,
            )

            all_text = " ".join(texts).lower()
            words = all_text.split()
            formal_count = sum(1 for w in words if w in _FORMAL)
            informal_count = sum(1 for w in words if w in _INFORMAL)
            total = formal_count + informal_count
            if total > 0:
                s.formality_score = formal_count / total

            # Puntuación
            total_texts = len(texts)
            s.question_ratio = sum(1 for t in texts if "?" in t) / total_texts
            s.exclamation_ratio = sum(1 for t in texts if "!" in t) / total_texts

    def _build_definition(self, attributes: list[dict]) -> None:
        """Construye indicador de definición a partir de atributos extraídos."""
        for attr in attributes:
            entity_name = attr.get("entity_name", "")
            category = attr.get("category", "").lower()
            key = attr.get("key", "")
            value = attr.get("value", "")

            if not entity_name or not value:
                continue

            # Buscar perfil por nombre
            profile = None
            for p in self._profiles.values():
                if p.entity_name.lower() == entity_name.lower():
                    profile = p
                    break

            if profile is None:
                continue

            d = profile.definition
            d.attribute_count += 1

            if category in ("physical", "fisico", "físico"):
                d.physical_attributes[key] = value
            elif category in ("psychological", "psicologico", "psicológico"):
                d.psychological_attributes[key] = value
            elif category in ("social",):
                d.social_attributes[key] = value

    def _build_sentiment(self, chapter_texts: dict[int, str]) -> None:
        """Extrae sentimiento asociado a cada personaje."""
        entity_names = {
            p.entity_name.lower(): p.entity_id
            for p in self._profiles.values()
        }

        # Acumuladores por capítulo: {entity_id: {chapter: {pos, neg, total}}}
        chapter_counts: dict[int, dict[int, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"pos": 0, "neg": 0, "total": 0})
        )

        for _chapter_num, text in chapter_texts.items():
            sentences = re.split(r"[.!?]+", text)

            for sentence in sentences:
                sentence_lower = sentence.lower()

                # Verificar si algún personaje aparece en la oración
                for name, entity_id in entity_names.items():
                    if name not in sentence_lower:
                        continue

                    profile = self._profiles[entity_id]
                    words = set(sentence_lower.split())

                    pos = len(words & POSITIVE_WORDS)
                    neg = len(words & NEGATIVE_WORDS)

                    counts = chapter_counts[entity_id][chapter_num]
                    counts["total"] += 1

                    if pos > neg:
                        profile.sentiment.positive_mentions += 1
                        counts["pos"] += 1
                    elif neg > pos:
                        profile.sentiment.negative_mentions += 1
                        counts["neg"] += 1
                    else:
                        profile.sentiment.neutral_mentions += 1

        # Calcular promedios globales y por capítulo
        for profile in self._profiles.values():
            s = profile.sentiment
            total = s.positive_mentions + s.negative_mentions + s.neutral_mentions
            if total > 0:
                s.avg_sentiment = (s.positive_mentions - s.negative_mentions) / total

            # Sentimiento por capítulo
            for ch, c in chapter_counts.get(profile.entity_id, {}).items():
                if c["total"] > 0:
                    s.sentiment_by_chapter[ch] = round(
                        (c["pos"] - c["neg"]) / c["total"], 3
                    )

    def _build_environment(self, location_events: list[dict]) -> None:
        """Construye indicador de entornos a partir de eventos de ubicación."""
        for event in location_events:
            entity_id = event.get("entity_id")
            location = event.get("location_name", "")
            chapter = event.get("chapter", 0)
            change_type = event.get("change_type", "")

            if entity_id is None or entity_id not in self._profiles:
                continue

            profile = self._profiles[entity_id]
            e = profile.environment

            e.locations[location] += 1
            if chapter not in e.locations_by_chapter:
                e.locations_by_chapter[chapter] = []
            if location not in e.locations_by_chapter[chapter]:
                e.locations_by_chapter[chapter].append(location)

            if change_type in ("transition", "arrival"):
                e.location_changes += 1

        # Ubicación principal
        for profile in self._profiles.values():
            e = profile.environment
            if e.locations:
                e.primary_location = e.locations.most_common(1)[0][0]

    def _calculate_relevance(self) -> None:
        """Calcula puntuación de relevancia narrativa (0-1)."""
        if not self._profiles:
            return

        # Normalizar cada indicador al rango 0-1
        max_mentions = max((p.presence.total_mentions for p in self._profiles.values()), default=1)
        max_actions = max((p.actions.action_count for p in self._profiles.values()), default=1)
        max_speech = max((p.speech.total_interventions for p in self._profiles.values()), default=1)
        max_attrs = max((p.definition.attribute_count for p in self._profiles.values()), default=1)
        max_sentiment = max(
            (
                p.sentiment.positive_mentions + p.sentiment.negative_mentions
                for p in self._profiles.values()
            ),
            default=1,
        )
        max_locations = max((len(p.environment.locations) for p in self._profiles.values()), default=1)

        for profile in self._profiles.values():
            scores = {
                "presence": profile.presence.total_mentions / max(max_mentions, 1),
                "actions": profile.actions.action_count / max(max_actions, 1),
                "speech": profile.speech.total_interventions / max(max_speech, 1),
                "definition": profile.definition.attribute_count / max(max_attrs, 1),
                "sentiment": (
                    (profile.sentiment.positive_mentions + profile.sentiment.negative_mentions)
                    / max(max_sentiment, 1)
                ),
                "environment": len(profile.environment.locations) / max(max_locations, 1),
            }

            profile.narrative_relevance = sum(
                scores[k] * self.RELEVANCE_WEIGHTS[k]
                for k in self.RELEVANCE_WEIGHTS
            )

    def _assign_roles(self) -> None:
        """Asigna roles narrativos basándose en la relevancia."""
        for profile in self._profiles.values():
            rel = profile.narrative_relevance
            assigned = False
            for role, threshold in self.ROLE_THRESHOLDS.items():
                if rel >= threshold:
                    profile.role = role
                    assigned = True
                    break
            if not assigned:
                profile.role = CharacterRole.MENTIONED
