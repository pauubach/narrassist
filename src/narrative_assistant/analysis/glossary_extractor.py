"""
Extractor automático de términos para el glosario.

Detecta términos candidatos para el glosario basándose en:
1. Frecuencia baja + mayúsculas (posibles nombres propios inventados)
2. Patrones técnicos (terminología especializada)
3. Neologismos (palabras no reconocidas por el diccionario)
4. Entidades nombradas del NER que no son comunes
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from narrative_assistant.core import Result

logger = logging.getLogger(__name__)


@dataclass
class GlossarySuggestion:
    """
    Sugerencia de término para añadir al glosario.
    """

    term: str  # Término sugerido
    reason: str  # Razón de la sugerencia
    category_hint: str  # Categoría sugerida: personaje, lugar, objeto, concepto, técnico
    confidence: float  # Confianza 0.0-1.0

    # Estadísticas
    frequency: int = 0  # Veces que aparece
    first_chapter: int | None = None  # Primer capítulo donde aparece
    contexts: list[str] = field(default_factory=list)  # Ejemplos de uso (max 3)

    # Flags inferidos
    is_likely_invented: bool = False
    is_likely_technical: bool = False
    is_likely_proper_noun: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "term": self.term,
            "reason": self.reason,
            "category_hint": self.category_hint,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "first_chapter": self.first_chapter,
            "contexts": self.contexts,
            "is_likely_invented": self.is_likely_invented,
            "is_likely_technical": self.is_likely_technical,
            "is_likely_proper_noun": self.is_likely_proper_noun,
        }


@dataclass
class GlossaryExtractionReport:
    """
    Reporte de extracción de términos para glosario.
    """

    suggestions: list[GlossarySuggestion]
    total_unique_words: int
    chapters_analyzed: int

    # Por categoría
    proper_nouns_found: int = 0
    technical_terms_found: int = 0
    potential_neologisms_found: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "suggestions": [s.to_dict() for s in self.suggestions],
            "total_unique_words": self.total_unique_words,
            "chapters_analyzed": self.chapters_analyzed,
            "proper_nouns_found": self.proper_nouns_found,
            "technical_terms_found": self.technical_terms_found,
            "potential_neologisms_found": self.potential_neologisms_found,
        }


class GlossaryExtractor:
    """
    Extrae términos candidatos para el glosario de un manuscrito.

    Estrategias de detección:
    1. Nombres propios no comunes (mayúscula + frecuencia baja)
    2. Términos técnicos (patrones específicos)
    3. Neologismos (palabras no en diccionario)
    4. Entidades del NER con frecuencia significativa
    """

    # Palabras comunes que NO deben sugerirse
    COMMON_PROPER_NOUNS = {
        # Nombres españoles muy comunes
        "maría",
        "juan",
        "pedro",
        "ana",
        "josé",
        "luis",
        "carlos",
        "antonio",
        "miguel",
        "francisco",
        "manuel",
        "carmen",
        "isabel",
        "rosa",
        "laura",
        "david",
        "pablo",
        "jorge",
        "raúl",
        "andrés",
        "elena",
        "marta",
        "lucía",
        "sofía",
        "alba",
        "sara",
        "paula",
        "daniela",
        "valeria",
        "emma",
        # Ciudades/países muy comunes
        "españa",
        "madrid",
        "barcelona",
        "méxico",
        "argentina",
        "colombia",
        "chile",
        "perú",
        "francia",
        "italia",
        "alemania",
        "londres",
        "parís",
        "roma",
        "nueva york",
        "buenos aires",
        "lima",
        "bogotá",
        # Meses, días
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
        # Otros comunes
        "dios",
        "señor",
        "señora",
        "doctor",
        "doctora",
    }

    # Patrones de términos técnicos
    TECHNICAL_PATTERNS = [
        r"\b[A-Z]{2,}s?\b",  # Acrónimos: ADN, HTTP, APIs
        r"\b\w+ismo\b",  # -ismo: comunismo, capitalismo
        r"\b\w+logía\b",  # -logía: biología, tecnología
        r"\b\w+ización\b",  # -ización: digitalización
        r"\b\w+metría\b",  # -metría: geometría
        r"\b\w+ectomía\b",  # -ectomía: apendicectomía
        r"\b\w+itis\b",  # -itis: artritis
        r"\b\w+osis\b",  # -osis: neurosis
    ]

    # Sufijos que indican términos inventados en fantasía/ciencia ficción
    FANTASY_SUFFIXES = [
        "iel",
        "ael",
        "wen",
        "dor",
        "thor",
        "mir",
        "gar",
        "dal",
        "rim",
        "eth",
        "oth",
        "ath",
        "ion",
        "eon",
        "ium",
        "ar",
        "or",
        "ur",
    ]

    def __init__(
        self,
        min_frequency: int = 2,
        max_frequency: int = 50,
        min_confidence: float = 0.5,
        existing_terms: set[str] | None = None,
    ):
        """
        Inicializa el extractor.

        Args:
            min_frequency: Frecuencia mínima para considerar un término
            max_frequency: Frecuencia máxima (términos muy frecuentes no se sugieren)
            min_confidence: Confianza mínima para incluir en sugerencias
            existing_terms: Términos ya en el glosario (para excluir)
        """
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self.min_confidence = min_confidence
        self.existing_terms = existing_terms or set()
        self._compiled_technical = [re.compile(p, re.IGNORECASE) for p in self.TECHNICAL_PATTERNS]

    def extract(
        self,
        chapters: list[dict],
        entities: list[dict] | None = None,
    ) -> Result[GlossaryExtractionReport]:
        """
        Extrae términos candidatos de los capítulos.

        Args:
            chapters: Lista de capítulos con 'number' y 'content'
            entities: Entidades extraídas del NER (opcional)

        Returns:
            Result con GlossaryExtractionReport
        """
        try:
            suggestions: dict[str, GlossarySuggestion] = {}
            word_counts: Counter[str] = Counter()
            word_chapters: dict[str, int] = {}  # Primera aparición
            word_contexts: dict[str, list[str]] = {}

            # Procesar cada capítulo
            for chapter in chapters:
                chapter_num = chapter.get("number", 0)
                content = chapter.get("content", "")

                if not content.strip():
                    continue

                # Extraer palabras con contexto
                self._process_chapter(
                    content=content,
                    chapter_num=chapter_num,
                    word_counts=word_counts,
                    word_chapters=word_chapters,
                    word_contexts=word_contexts,
                )

            # Analizar entidades del NER si están disponibles
            if entities:
                self._process_entities(
                    entities=entities,
                    word_counts=word_counts,
                    word_chapters=word_chapters,
                    suggestions=suggestions,
                )

            # Generar sugerencias de palabras detectadas
            for word, count in word_counts.items():
                # Filtrar por frecuencia
                if count < self.min_frequency or count > self.max_frequency:
                    continue

                # Saltar si ya está en el glosario
                if word.lower() in self.existing_terms:
                    continue

                # Saltar palabras comunes
                if word.lower() in self.COMMON_PROPER_NOUNS:
                    continue

                # Evaluar y crear sugerencia
                suggestion = self._evaluate_word(
                    word=word,
                    count=count,
                    first_chapter=word_chapters.get(word),
                    contexts=word_contexts.get(word, [])[:3],
                )

                if suggestion and suggestion.confidence >= self.min_confidence:
                    # No duplicar si ya existe una sugerencia con mayor confianza
                    existing = suggestions.get(word.lower())
                    if not existing or suggestion.confidence > existing.confidence:
                        suggestions[word.lower()] = suggestion

            # Ordenar por confianza
            sorted_suggestions = sorted(
                suggestions.values(),
                key=lambda s: (-s.confidence, -s.frequency),
            )

            # Contar por tipo
            proper_nouns = sum(1 for s in sorted_suggestions if s.is_likely_proper_noun)
            technical = sum(1 for s in sorted_suggestions if s.is_likely_technical)
            neologisms = sum(1 for s in sorted_suggestions if s.is_likely_invented)

            report = GlossaryExtractionReport(
                suggestions=sorted_suggestions,
                total_unique_words=len(word_counts),
                chapters_analyzed=len([c for c in chapters if c.get("content", "").strip()]),
                proper_nouns_found=proper_nouns,
                technical_terms_found=technical,
                potential_neologisms_found=neologisms,
            )

            logger.info(
                f"Extracción glosario: {len(sorted_suggestions)} sugerencias de {len(word_counts)} palabras únicas"
            )

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error en extracción de glosario: {e}", exc_info=True)
            return Result.failure(e)  # type: ignore[arg-type]

    def _process_chapter(
        self,
        content: str,
        chapter_num: int,
        word_counts: Counter[str],
        word_chapters: dict[str, int],
        word_contexts: dict[str, list[str]],
    ) -> None:
        """Procesa un capítulo extrayendo palabras candidatas."""
        # Dividir en oraciones para contexto
        sentences = re.split(r"[.!?]+", content)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Buscar palabras con mayúscula que no están al inicio de oración
            # Patrón: palabra anterior + Palabra con mayúscula
            pattern = r"(?<=[a-záéíóúñü]\s)([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)"
            matches = re.finditer(pattern, sentence)

            for match in matches:
                word = match.group(1)
                if len(word) < 3:  # Ignorar palabras muy cortas
                    continue

                word_counts[word] += 1
                if word not in word_chapters:
                    word_chapters[word] = chapter_num
                if word not in word_contexts:
                    word_contexts[word] = []
                if len(word_contexts[word]) < 5:  # Máximo 5 contextos
                    # Extraer contexto alrededor de la palabra
                    start = max(0, match.start() - 30)
                    end = min(len(sentence), match.end() + 30)
                    context = sentence[start:end].strip()
                    if context and context not in word_contexts[word]:
                        word_contexts[word].append(context)

            # Buscar también términos técnicos
            for pattern in self._compiled_technical:  # type: ignore[assignment]
                for match in pattern.finditer(sentence):  # type: ignore[attr-defined]
                    term = match.group()
                    if len(term) >= 3:
                        word_counts[term] += 1
                        if term not in word_chapters:
                            word_chapters[term] = chapter_num

    def _process_entities(
        self,
        entities: list[dict],
        word_counts: Counter[str],
        word_chapters: dict[str, int],
        suggestions: dict[str, GlossarySuggestion],
    ) -> None:
        """Procesa entidades del NER para añadir sugerencias."""
        for entity in entities:
            name = entity.get("name", "").strip()
            entity_type = entity.get("type", "").upper()
            mention_count = entity.get("mention_count", 0)

            if not name or len(name) < 3:
                continue

            # Saltar si ya está en el glosario
            if name.lower() in self.existing_terms:
                continue

            # Saltar nombres muy comunes
            if name.lower() in self.COMMON_PROPER_NOUNS:
                continue

            # Mapear tipo de entidad a categoría de glosario
            category_map = {
                "CHARACTER": "personaje",
                "LOCATION": "lugar",
                "OBJECT": "objeto",
                "CONCEPT": "concepto",
                "ORGANIZATION": "concepto",
                "EVENT": "concepto",
            }
            category = category_map.get(entity_type, "general")

            # Solo sugerir si tiene suficientes menciones
            if mention_count < self.min_frequency:
                continue

            # Calcular confianza basada en frecuencia y tipo
            confidence = min(0.9, 0.5 + (mention_count / 100))
            if entity_type in ("CHARACTER", "LOCATION"):
                confidence += 0.1  # Bonus para personajes y lugares

            suggestion = GlossarySuggestion(
                term=name,
                reason=f"Entidad {entity_type.lower()} detectada por NER",
                category_hint=category,
                confidence=confidence,
                frequency=mention_count,
                first_chapter=entity.get("first_mention_chapter"),
                is_likely_proper_noun=entity_type in ("CHARACTER", "LOCATION"),
                is_likely_invented=self._looks_invented(name),
            )

            existing = suggestions.get(name.lower())
            if not existing or suggestion.confidence > existing.confidence:
                suggestions[name.lower()] = suggestion

    def _evaluate_word(
        self,
        word: str,
        count: int,
        first_chapter: int | None,
        contexts: list[str],
    ) -> GlossarySuggestion | None:
        """
        Evalúa una palabra y genera una sugerencia si es candidata.

        Returns:
            GlossarySuggestion si es candidata, None si no
        """
        is_capitalized = word[0].isupper()
        is_all_caps = word.isupper() and len(word) > 2
        looks_invented = self._looks_invented(word)
        is_technical = self._is_technical(word)

        # Calcular confianza base
        confidence = 0.0
        reasons = []
        category = "general"

        # Nombre propio (capitalizado, no muy frecuente)
        if is_capitalized and not is_all_caps:
            confidence += 0.4
            reasons.append("Nombre con mayúscula")
            category = "personaje"  # Asumir personaje por defecto

            # Bonus si parece inventado
            if looks_invented:
                confidence += 0.2
                reasons.append("parece inventado")

        # Acrónimo
        if is_all_caps:
            confidence += 0.5
            reasons.append("Acrónimo")
            category = "técnico"

        # Término técnico
        if is_technical:
            confidence += 0.4
            reasons.append("Patrón técnico")
            category = "técnico"

        # Bonus por frecuencia intermedia (no muy común, no único)
        if 3 <= count <= 20:
            confidence += 0.1
            reasons.append(f"frecuencia media ({count})")

        # No sugerir si la confianza es muy baja
        if confidence < self.min_confidence:
            return None

        return GlossarySuggestion(
            term=word,
            reason=", ".join(reasons),
            category_hint=category,
            confidence=min(1.0, confidence),
            frequency=count,
            first_chapter=first_chapter,
            contexts=contexts,
            is_likely_invented=looks_invented,
            is_likely_technical=is_technical,
            is_likely_proper_noun=is_capitalized and not is_all_caps,
        )

    def _looks_invented(self, word: str) -> bool:
        """Determina si una palabra parece inventada (fantasía/ciencia ficción)."""
        word_lower = word.lower()

        # Verificar sufijos de fantasía
        for suffix in self.FANTASY_SUFFIXES:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                return True

        # Patrones de nombres de fantasía (consonantes inusuales seguidas)
        unusual_patterns = [
            r"[^aeiouáéíóú]{4,}",  # 4+ consonantes seguidas
            r"th[^aeiouáéíóú]",  # th seguido de consonante
            r"[^aeiouáéíóú]w",  # consonante + w (raro en español)
            r"[xzq][^u]",  # x, z, q no seguidos de u (raro)
        ]

        return any(re.search(pattern, word_lower) for pattern in unusual_patterns)

    def _is_technical(self, word: str) -> bool:
        """Determina si una palabra parece técnica."""
        return any(pattern.fullmatch(word) for pattern in self._compiled_technical)
