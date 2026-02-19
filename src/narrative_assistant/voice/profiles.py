"""
Perfiles de voz por personaje.

Construye perfiles estilísticos basados en los diálogos de cada personaje,
incluyendo métricas como longitud de intervención, riqueza léxica (TTR),
formalidad, muletillas y patrones de puntuación.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, stdev

logger = logging.getLogger(__name__)


# Palabras de registro formal vs informal en español
FORMAL_MARKERS = {
    # Pronombres y tratamiento
    "usted",
    "ustedes",
    "senor",
    "senora",
    "don",
    "dona",
    # Verbos formales
    "desearia",
    "permitiria",
    "solicitaria",
    "agradeceria",
    # Expresiones formales
    "sin embargo",
    "no obstante",
    "por consiguiente",
    "asimismo",
    "en efecto",
    "ciertamente",
    "efectivamente",
    "indudablemente",
    # Vocabulario culto
    "menester",
    "acaecer",
    "deparar",
    "suscitar",
    "denotar",
}

INFORMAL_MARKERS = {
    # Pronombres y tratamiento
    "tu",
    "vos",
    "tio",
    "tia",
    "colega",
    "chaval",
    "chavala",
    # Muletillas
    "bueno",
    "pues",
    "vale",
    "venga",
    "vamos",
    "mira",
    "oye",
    "eh",
    "ey",
    "jo",
    "jolin",
    "joder",
    "hostia",
    # Expresiones coloquiales
    "mogollon",
    "mola",
    "flipar",
    "currar",
    "molar",
    "flipante",
    "guay",
    "genial",
    "pasada",
    "rollo",
    "chungo",
    # Contracciones y elisiones tipicas
    "pa",
    "pal",
    "mu",
}

# Muletillas comunes en español
FILLERS = {
    "bueno",
    "pues",
    "eh",
    "este",
    "o sea",
    "es decir",
    "sabes",
    "entiendes",
    "me explico",
    "verdad",
    "la verdad",
    "en plan",
    "tipo",
    "como que",
    "basicamente",
    "literalmente",
    "sinceramente",
    "francamente",
    "obviamente",
    "claramente",
    "realmente",
    "practicamente",
    "exactamente",
}


@dataclass
class VoiceMetrics:
    """Métricas cuantitativas de la voz de un personaje."""

    # Longitud de intervención
    avg_intervention_length: float = 0.0  # Palabras promedio por intervención
    std_intervention_length: float = 0.0  # Desviación estándar
    min_intervention_length: int = 0
    max_intervention_length: int = 0

    # Riqueza léxica
    type_token_ratio: float = 0.0  # TTR: tipos únicos / total tokens
    hapax_legomena_ratio: float = 0.0  # Palabras que aparecen solo una vez

    # Formalidad (0 = muy informal, 1 = muy formal)
    formality_score: float = 0.5
    formal_marker_count: int = 0
    informal_marker_count: int = 0

    # Muletillas
    filler_ratio: float = 0.0  # Proporción de palabras que son muletillas
    top_fillers: list[tuple[str, int]] = field(default_factory=list)

    # Puntuación
    exclamation_ratio: float = 0.0  # Exclamaciones por intervención
    question_ratio: float = 0.0  # Preguntas por intervención
    ellipsis_ratio: float = 0.0  # Puntos suspensivos por intervención

    # Complejidad sintáctica
    avg_sentence_length: float = 0.0  # Palabras por oración
    subordinate_clause_ratio: float = 0.0  # Proporción de oraciones subordinadas

    # Estadísticas de muestra
    total_interventions: int = 0
    total_words: int = 0


@dataclass
class VoiceProfile:
    """Perfil de voz completo de un personaje."""

    entity_id: int
    entity_name: str
    metrics: VoiceMetrics = field(default_factory=VoiceMetrics)

    # Vocabulario característico
    characteristic_words: list[tuple[str, float]] = field(default_factory=list)  # (palabra, tf-idf)

    # Patrones detectados
    speech_patterns: list[str] = field(default_factory=list)  # Patrones frecuentes

    # Nivel de confianza del perfil
    confidence: float = 0.0  # Basado en cantidad de muestras

    def to_dict(self) -> dict:
        """Convierte el perfil a diccionario."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "metrics": {
                "avg_intervention_length": self.metrics.avg_intervention_length,
                "std_intervention_length": self.metrics.std_intervention_length,
                "min_intervention_length": self.metrics.min_intervention_length,
                "max_intervention_length": self.metrics.max_intervention_length,
                "type_token_ratio": self.metrics.type_token_ratio,
                "hapax_legomena_ratio": self.metrics.hapax_legomena_ratio,
                "formality_score": self.metrics.formality_score,
                "formal_marker_count": self.metrics.formal_marker_count,
                "informal_marker_count": self.metrics.informal_marker_count,
                "filler_ratio": self.metrics.filler_ratio,
                "top_fillers": self.metrics.top_fillers,
                "exclamation_ratio": self.metrics.exclamation_ratio,
                "question_ratio": self.metrics.question_ratio,
                "ellipsis_ratio": self.metrics.ellipsis_ratio,
                "avg_sentence_length": self.metrics.avg_sentence_length,
                "subordinate_clause_ratio": self.metrics.subordinate_clause_ratio,
                "total_interventions": self.metrics.total_interventions,
                "total_words": self.metrics.total_words,
            },
            "characteristic_words": self.characteristic_words[:10],
            "speech_patterns": self.speech_patterns[:5],
            "confidence": self.confidence,
        }


class VoiceProfileBuilder:
    """Constructor de perfiles de voz a partir de diálogos."""

    def __init__(self, min_interventions: int = 5):
        """
        Inicializa el constructor de perfiles.

        Args:
            min_interventions: Mínimo de intervenciones para perfil confiable
        """
        self.min_interventions = min_interventions
        self._all_words: Counter = Counter()  # Para calcular TF-IDF
        self._entity_words: dict[int, Counter] = {}  # Palabras por entidad

    def build_profiles(
        self,
        dialogues: list[dict],
        entities: list[dict],
    ) -> list[VoiceProfile]:
        """
        Construye perfiles de voz para todos los personajes.

        Args:
            dialogues: Lista de diálogos con formato:
                {
                    "text": str,
                    "speaker_id": int,
                    "chapter": int,
                    "position": int
                }
            entities: Lista de entidades con formato:
                {"id": int, "name": str, "type": str}

        Returns:
            Lista de perfiles de voz
        """
        # Filtrar solo personajes
        character_ids = {
            e["id"] for e in entities if e.get("type") in ("PERSON", "CHARACTER", "PER")
        }

        # Agrupar diálogos por speaker
        dialogues_by_speaker: dict[int, list[str]] = {}
        for dialogue in dialogues:
            speaker_id = dialogue.get("speaker_id")
            if speaker_id and speaker_id in character_ids:
                if speaker_id not in dialogues_by_speaker:
                    dialogues_by_speaker[speaker_id] = []
                dialogues_by_speaker[speaker_id].append(dialogue["text"])

        # Primera pasada: recolectar todas las palabras
        self._collect_vocabulary(dialogues_by_speaker)

        # Construir perfil para cada personaje
        profiles = []
        entity_map = {e["id"]: e["name"] for e in entities}

        for entity_id, interventions in dialogues_by_speaker.items():
            entity_name = entity_map.get(entity_id, f"Entity_{entity_id}")
            profile = self._build_single_profile(entity_id, entity_name, interventions)
            profiles.append(profile)

        logger.info(f"Construidos {len(profiles)} perfiles de voz")
        return profiles

    def _collect_vocabulary(self, dialogues_by_speaker: dict[int, list[str]]) -> None:
        """Recolecta vocabulario de todos los diálogos."""
        self._all_words.clear()
        self._entity_words.clear()

        for entity_id, interventions in dialogues_by_speaker.items():
            self._entity_words[entity_id] = Counter()
            for text in interventions:
                words = self._tokenize(text)
                self._all_words.update(words)
                self._entity_words[entity_id].update(words)

    def _build_single_profile(
        self,
        entity_id: int,
        entity_name: str,
        interventions: list[str],
    ) -> VoiceProfile:
        """Construye perfil para un personaje."""
        metrics = VoiceMetrics()

        if not interventions:
            return VoiceProfile(
                entity_id=entity_id, entity_name=entity_name, metrics=metrics, confidence=0.0
            )

        # Calcular métricas de longitud
        lengths = [len(self._tokenize(text)) for text in interventions]
        metrics.total_interventions = len(interventions)
        metrics.total_words = sum(lengths)
        metrics.avg_intervention_length = mean(lengths) if lengths else 0
        metrics.std_intervention_length = stdev(lengths) if len(lengths) > 1 else 0
        metrics.min_intervention_length = min(lengths) if lengths else 0
        metrics.max_intervention_length = max(lengths) if lengths else 0

        # Calcular TTR y hapax
        all_words = []
        for text in interventions:
            all_words.extend(self._tokenize(text))

        if all_words:
            word_counts = Counter(all_words)
            types = len(word_counts)
            tokens = len(all_words)
            metrics.type_token_ratio = types / tokens if tokens > 0 else 0
            hapax = sum(1 for count in word_counts.values() if count == 1)
            metrics.hapax_legomena_ratio = hapax / types if types > 0 else 0

        # Calcular formalidad
        formal_count = 0
        informal_count = 0
        text_lower = " ".join(interventions).lower()

        for marker in FORMAL_MARKERS:
            formal_count += text_lower.count(marker)
        for marker in INFORMAL_MARKERS:
            informal_count += text_lower.count(marker)

        metrics.formal_marker_count = formal_count
        metrics.informal_marker_count = informal_count

        total_markers = formal_count + informal_count
        if total_markers > 0:
            metrics.formality_score = formal_count / total_markers
        else:
            metrics.formality_score = 0.5  # Neutral

        # Calcular muletillas
        filler_counts: Counter[str] = Counter()
        total_filler_count = 0
        for text in interventions:
            text_lower = text.lower()
            for filler in FILLERS:
                count = text_lower.count(filler)
                if count > 0:
                    filler_counts[filler] += count
                    total_filler_count += count

        metrics.filler_ratio = (
            total_filler_count / metrics.total_words if metrics.total_words > 0 else 0
        )
        metrics.top_fillers = filler_counts.most_common(5)

        # Calcular patrones de puntuación
        exclamations = sum(text.count("!") for text in interventions)
        questions = sum(text.count("?") for text in interventions)
        ellipsis = sum(text.count("...") for text in interventions)

        metrics.exclamation_ratio = exclamations / len(interventions)
        metrics.question_ratio = questions / len(interventions)
        metrics.ellipsis_ratio = ellipsis / len(interventions)

        # Calcular complejidad sintáctica
        sentence_lengths = []
        for text in interventions:
            sentences = re.split(r"[.!?]+", text)
            for sent in sentences:
                words = self._tokenize(sent)
                if words:
                    sentence_lengths.append(len(words))

        metrics.avg_sentence_length = mean(sentence_lengths) if sentence_lengths else 0

        # Detectar oraciones subordinadas (aproximación)
        subordinate_markers = [
            "que",
            "quien",
            "donde",
            "cuando",
            "como",
            "porque",
            "aunque",
            "si",
            "mientras",
            "antes",
            "despues",
        ]
        subordinate_count = 0
        total_sentences = 0
        for text in interventions:
            sentences = re.split(r"[.!?]+", text)
            for sent in sentences:
                if sent.strip():
                    total_sentences += 1
                    sent_lower = sent.lower()
                    if any(marker in sent_lower for marker in subordinate_markers):
                        subordinate_count += 1

        metrics.subordinate_clause_ratio = (
            subordinate_count / total_sentences if total_sentences > 0 else 0
        )

        # Calcular palabras características (TF-IDF simplificado)
        characteristic_words = self._calculate_characteristic_words(entity_id)

        # Detectar patrones de habla
        speech_patterns = self._detect_speech_patterns(interventions)

        # Calcular confianza
        confidence = min(1.0, len(interventions) / (self.min_interventions * 2))

        return VoiceProfile(
            entity_id=entity_id,
            entity_name=entity_name,
            metrics=metrics,
            characteristic_words=characteristic_words,
            speech_patterns=speech_patterns,
            confidence=confidence,
        )

    def _tokenize(self, text: str) -> list[str]:
        """Tokeniza texto en palabras."""
        # Eliminar puntuación y convertir a minúsculas
        text = re.sub(r"[^\w\s]", " ", text.lower())
        words = text.split()
        # Filtrar palabras muy cortas
        return [w for w in words if len(w) > 1]

    def _calculate_characteristic_words(
        self, entity_id: int, top_n: int = 20
    ) -> list[tuple[str, float]]:
        """
        Calcula palabras características usando TF-IDF simplificado.

        Las palabras características son aquellas que el personaje usa
        más frecuentemente que el promedio.
        """
        if entity_id not in self._entity_words:
            return []

        entity_counter = self._entity_words[entity_id]
        entity_total = sum(entity_counter.values())

        if entity_total == 0:
            return []

        all_total = sum(self._all_words.values())

        scores = []
        for word, count in entity_counter.items():
            # TF: frecuencia en el personaje
            tf = count / entity_total

            # IDF aproximado: inverso de la frecuencia global
            global_freq = self._all_words.get(word, 1) / all_total
            idf = 1 / (global_freq + 0.001)  # Evitar división por cero

            # TF-IDF
            tfidf = tf * idf

            # Solo incluir palabras con puntuación significativa
            if tfidf > 1.0 and count >= 2:
                scores.append((word, round(tfidf, 2)))

        # Ordenar por puntuación
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]

    def _detect_speech_patterns(
        self, interventions: list[str], min_occurrences: int = 2
    ) -> list[str]:
        """Detecta patrones frecuentes en el habla del personaje."""
        patterns = []

        # Patrones de inicio de frase
        starts: Counter[str] = Counter()
        for text in interventions:
            words = text.split()[:3]  # Primeras 3 palabras
            if len(words) >= 2:
                starts[" ".join(words[:2])] += 1

        for pattern, count in starts.most_common(5):
            if count >= min_occurrences:
                patterns.append(f"Inicio: '{pattern}...'")

        # Patrones de fin de frase
        ends: Counter[str] = Counter()
        for text in interventions:
            # Buscar patrones antes de puntuación final
            match = re.search(r"(\w+\s+\w+)[.!?]+\s*$", text)
            if match:
                ends[match.group(1)] += 1

        for pattern, count in ends.most_common(3):
            if count >= min_occurrences:
                patterns.append(f"Final: '...{pattern}'")

        # Expresiones repetidas
        expressions: Counter[str] = Counter()
        for text in interventions:
            # Buscar bigramas y trigramas frecuentes
            words = self._tokenize(text)
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i + 1]}"
                expressions[bigram] += 1

        for pattern, count in expressions.most_common(5):
            if count >= min_occurrences * 2:
                patterns.append(f"Expresion: '{pattern}'")

        return patterns[:5]


def build_voice_profiles_from_chapters(
    chapters: list[dict],
    entities: list[dict],
) -> list[VoiceProfile]:
    """
    Función de conveniencia para construir perfiles desde capítulos.

    Args:
        chapters: Lista de capítulos con diálogos extraídos
        entities: Lista de entidades del proyecto

    Returns:
        Lista de perfiles de voz
    """
    # Extraer diálogos de los capítulos
    dialogues = []
    for chapter in chapters:
        chapter_dialogues = chapter.get("dialogues", [])
        for d in chapter_dialogues:
            dialogues.append(
                {
                    "text": d.get("text", ""),
                    "speaker_id": d.get("speaker_id"),
                    "chapter": chapter.get("number", 0),
                    "position": d.get("position", 0),
                }
            )

    builder = VoiceProfileBuilder()
    return builder.build_profiles(dialogues, entities)
