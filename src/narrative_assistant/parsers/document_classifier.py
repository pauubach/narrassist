# -*- coding: utf-8 -*-
"""
Clasificador de tipo de documento para ajustar análisis.

Detecta el tipo de documento (ficción, ensayo, autoayuda, técnico, etc.)
y ajusta los parámetros de análisis en consecuencia.

Tipos de documento:
- FICTION: Novelas, cuentos, relatos (buscar personajes, diálogos, trama)
- ESSAY: Ensayos, artículos de opinión (conceptos, argumentos)
- SELF_HELP: Autoayuda, desarrollo personal (conceptos abstractos, consejos)
- TECHNICAL: Manuales, documentación técnica (términos técnicos, procedimientos)
- MEMOIR: Memorias, autobiografías (mezcla de ficción y ensayo)
- COOKBOOK: Recetas, libros de cocina (ingredientes, procedimientos)
- ACADEMIC: Textos académicos, papers (citas, referencias)
- UNKNOWN: No clasificado

El tipo de documento afecta:
- Detección de entidades (CHARACTER en ficción, CONCEPT en autoayuda)
- Fusión semántica (más conservadora en ensayos)
- Alertas (diferentes reglas según contexto)
- Análisis temporal (relevante solo en ficción)
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Tipos de documento soportados."""

    FICTION = "fiction"           # Novela, cuento, relato
    ESSAY = "essay"               # Ensayo, artículo de opinión
    SELF_HELP = "self_help"       # Autoayuda, desarrollo personal
    TECHNICAL = "technical"       # Manual técnico, documentación
    MEMOIR = "memoir"             # Memorias, autobiografía
    COOKBOOK = "cookbook"         # Recetas, gastronomía
    ACADEMIC = "academic"         # Paper, texto académico
    UNKNOWN = "unknown"           # No clasificado


@dataclass
class DocumentClassification:
    """Resultado de la clasificación de documento."""

    document_type: DocumentType
    confidence: float  # 0.0 - 1.0
    indicators: list[str]  # Indicadores que llevaron a la clasificación
    recommended_settings: dict  # Configuración recomendada


# Indicadores por tipo de documento
FICTION_INDICATORS = {
    # Patrones de diálogo
    "dialog_markers": [
        r'--\s*[A-ZÁÉÍÓÚÑ¡¿]',  # Doble guión (clásico español: La Regenta, etc.)
        r'[—–]\s*[A-ZÁÉÍÓÚÑ¡¿]',  # Guión largo/medio seguido de mayúscula o ¡¿
        r'"[^"]+"\s*[,\.]?\s*(dijo|preguntó|respondió|exclamó|murmuró|susurró)',
        r'«[^»]+»',  # Comillas latinas (angulares)
    ],
    # Descripciones narrativas
    "narrative_descriptions": [
        r'\b(ojos|cabello|rostro|mirada|sonrisa)\s+(de|del|de la)\b',
        r'\b(alta?|bajo|rubio|moreno|delgado|gordo)\b.*\b(hombre|mujer|chico|chica)\b',
    ],
    # Acciones de personajes
    "character_actions": [
        r'\b(caminó|corrió|saltó|miró|observó|pensó)\b',
        r'\bse\s+(levantó|sentó|acercó|alejó|giró)\b',
    ],
    # Estructuras narrativas
    "narrative_structures": [
        r'\bcapítulo\s+\d+\b',
        r'\bprólogo\b',
        r'\bepílogo\b',
    ],
}

SELF_HELP_INDICATORS = {
    # Consejos directos al lector
    "direct_advice": [
        r'\b(debes|deberías|tienes que|necesitas|intenta|prueba)\b',
        r'\bsi\s+(quieres|deseas|buscas)\b',
        r'\bte\s+(recomiendo|sugiero|aconsejo)\b',
    ],
    # Conceptos abstractos
    "abstract_concepts": [
        r'\b(felicidad|éxito|bienestar|autoestima|confianza|motivación)\b',
        r'\b(crecimiento personal|desarrollo personal|superación)\b',
        r'\b(mentalidad|actitud|enfoque|perspectiva)\b',
    ],
    # Estructura de tips/pasos
    "tips_structure": [
        r'^\s*\d+\.\s+[A-ZÁÉÍÓÚÑ]',  # Lista numerada
        r'\b(paso\s+\d+|tip\s+#?\d+|consejo\s+#?\d+)\b',
        r'\b(primero|segundo|tercero|finalmente|por último)\b',
    ],
    # Preguntas retóricas
    "rhetorical_questions": [
        r'\¿(alguna vez|has pensado|te has preguntado|por qué|cómo puedes)\b',
        r'\¿qué\s+(pasaría|harías|pensarías)\b',
    ],
}

ESSAY_INDICATORS = {
    # Argumentación
    "argumentation": [
        r'\b(por tanto|por lo tanto|en consecuencia|así pues)\b',
        r'\b(sin embargo|no obstante|aunque|a pesar de)\b',
        r'\b(en primer lugar|en segundo lugar|finalmente)\b',
    ],
    # Referencias a autores/fuentes
    "references": [
        r'\bsegún\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',
        r'\([A-Za-z]+,\s*\d{4}\)',  # (Autor, año)
        r'\bcomo\s+(señala|indica|afirma|sostiene)\s+[A-ZÁÉÍÓÚÑ]',
    ],
    # Reflexiones abstractas
    "abstract_reflection": [
        r'\b(la sociedad|la humanidad|el ser humano|la historia)\b',
        r'\b(cabe\s+(señalar|destacar|mencionar)|es\s+importante\s+notar)\b',
    ],
}

TECHNICAL_INDICATORS = {
    # Términos técnicos y procedimientos
    "technical_terms": [
        r'\b(configurar|instalar|ejecutar|implementar|compilar)\b',
        r'\b(parámetro|variable|función|método|clase|objeto)\b',
        r'\b(base de datos|servidor|cliente|red|protocolo)\b',
    ],
    # Instrucciones paso a paso
    "instructions": [
        r'^\s*\d+\.\s+(Abrir?|Click|Seleccionar?|Introduzca?)\b',
        r'\bejecutar?\s+el\s+(comando|script|programa)\b',
        r'\bver\s+(figura|tabla|diagrama)\s+\d+\b',
    ],
    # Código o comandos
    "code_markers": [
        r'`[^`]+`',  # Código inline
        r'^\s*\$\s+\w+',  # Comandos shell
        r'\b(function|def|class|import|return)\b',
    ],
}

COOKBOOK_INDICATORS = {
    # Ingredientes
    "ingredients": [
        r'\d+\s*(g|kg|ml|l|cucharada|taza|unidad)\s+de\s+',
        r'\b(harina|azúcar|sal|aceite|huevo|leche|mantequilla)\b',
    ],
    # Instrucciones de cocina
    "cooking_instructions": [
        r'\b(mezclar|batir|hornear|freír|hervir|cocer|añadir)\b',
        r'\ba\s+(\d+|fuego\s+(lento|medio|alto))\s*°?C?\b',
        r'\bdurante\s+\d+\s*(minutos?|horas?)\b',
    ],
}

MEMOIR_INDICATORS = {
    # Primera persona pasado
    "first_person_past": [
        r'\b(yo|mi|mis|me)\b.*\b(recuerdo|recordaba|era|tenía|vivía)\b',
        r'\bcuando\s+(yo\s+)?(era|tenía)\s+\d+\s*años\b',
    ],
    # Referencias autobiográficas
    "autobiographical": [
        r'\bmi\s+(madre|padre|familia|infancia|juventud)\b',
        r'\ben\s+aquella\s+época\b',
        r'\b(años\s+después|tiempo\s+después|con\s+el\s+tiempo)\b',
    ],
}


class DocumentClassifier:
    """
    Clasificador de documentos basado en análisis heurístico.

    Analiza patrones textuales para determinar el tipo de documento
    y recomendar configuraciones de análisis apropiadas.
    """

    # Pesos para cada categoría de indicador
    INDICATOR_WEIGHTS = {
        "dialog_markers": 2.0,
        "narrative_descriptions": 1.5,
        "character_actions": 1.5,
        "narrative_structures": 1.0,
        "direct_advice": 2.0,
        "abstract_concepts": 1.5,
        "tips_structure": 1.5,
        "rhetorical_questions": 1.0,
        "argumentation": 1.5,
        "references": 2.0,
        "abstract_reflection": 1.0,
        "technical_terms": 2.0,
        "instructions": 1.5,
        "code_markers": 2.5,
        "ingredients": 3.0,
        "cooking_instructions": 2.5,
        "first_person_past": 1.5,
        "autobiographical": 1.5,
    }

    def classify(
        self,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DocumentClassification:
        """
        Clasifica un documento basándose en su contenido.

        Args:
            text: Texto del documento (primeros ~10000 caracteres son suficientes)
            title: Título del documento (opcional, ayuda en clasificación)
            metadata: Metadatos adicionales (opcional)

        Returns:
            DocumentClassification con tipo, confianza e indicadores
        """
        # Usar solo una muestra del texto para eficiencia
        sample = text[:10000] if len(text) > 10000 else text
        sample_lower = sample.lower()

        # Calcular puntuación para cada tipo
        scores = {
            DocumentType.FICTION: self._score_fiction(sample, sample_lower),
            DocumentType.SELF_HELP: self._score_self_help(sample, sample_lower),
            DocumentType.ESSAY: self._score_essay(sample, sample_lower),
            DocumentType.TECHNICAL: self._score_technical(sample, sample_lower),
            DocumentType.COOKBOOK: self._score_cookbook(sample, sample_lower),
            DocumentType.MEMOIR: self._score_memoir(sample, sample_lower),
        }

        # Añadir pistas del título si existe
        if title:
            self._adjust_scores_from_title(title.lower(), scores)

        # Encontrar tipo con mayor puntuación
        best_type = max(scores, key=lambda t: scores[t][0])
        best_score, indicators = scores[best_type]

        # Calcular confianza relativa
        total_score = sum(s[0] for s in scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0

        # Si la confianza es muy baja, marcar como UNKNOWN
        if confidence < 0.25 or best_score < 3.0:
            return DocumentClassification(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                indicators=[],
                recommended_settings=self._get_default_settings(),
            )

        return DocumentClassification(
            document_type=best_type,
            confidence=min(confidence, 1.0),
            indicators=indicators[:5],  # Top 5 indicadores
            recommended_settings=self._get_settings_for_type(best_type),
        )

    def _count_matches(
        self,
        text: str,
        patterns: dict[str, list[str]],
    ) -> tuple[float, list[str]]:
        """Cuenta coincidencias de patrones y retorna puntuación e indicadores."""
        total_score = 0.0
        indicators = []

        for category, pattern_list in patterns.items():
            category_matches = 0
            for pattern in pattern_list:
                try:
                    matches = len(re.findall(pattern, text, re.IGNORECASE | re.MULTILINE))
                    category_matches += matches
                except re.error:
                    continue

            if category_matches > 0:
                weight = self.INDICATOR_WEIGHTS.get(category, 1.0)
                # Log scale para evitar que un solo patrón domine
                score = weight * (1 + min(category_matches, 20) * 0.3)
                total_score += score
                indicators.append(f"{category}: {category_matches} matches")

        return total_score, indicators

    def _score_fiction(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de ficción."""
        return self._count_matches(text, FICTION_INDICATORS)

    def _score_self_help(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de autoayuda."""
        return self._count_matches(text, SELF_HELP_INDICATORS)

    def _score_essay(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de ensayo."""
        return self._count_matches(text, ESSAY_INDICATORS)

    def _score_technical(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores técnicos."""
        return self._count_matches(text, TECHNICAL_INDICATORS)

    def _score_cookbook(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de recetas."""
        return self._count_matches(text, COOKBOOK_INDICATORS)

    def _score_memoir(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de memorias."""
        return self._count_matches(text, MEMOIR_INDICATORS)

    def _adjust_scores_from_title(
        self,
        title_lower: str,
        scores: dict[DocumentType, tuple[float, list[str]]],
    ) -> None:
        """Ajusta puntuaciones basándose en el título."""
        title_hints = {
            DocumentType.FICTION: ["novela", "cuento", "relato", "historia de", "aventuras"],
            DocumentType.SELF_HELP: ["cómo", "secretos de", "guía para", "manual de vida",
                                     "felicidad", "éxito", "superación", "autoayuda"],
            DocumentType.ESSAY: ["ensayo", "reflexiones", "pensamiento", "filosofía"],
            DocumentType.TECHNICAL: ["manual", "guía técnica", "tutorial", "documentación"],
            DocumentType.COOKBOOK: ["recetas", "cocina", "gastronomía", "chef"],
            DocumentType.MEMOIR: ["memorias", "autobiografía", "mi vida", "recuerdos"],
        }

        for doc_type, hints in title_hints.items():
            for hint in hints:
                if hint in title_lower:
                    current_score, indicators = scores[doc_type]
                    scores[doc_type] = (current_score + 5.0, indicators + [f"title_hint: {hint}"])
                    break

    def _get_settings_for_type(self, doc_type: DocumentType) -> dict:
        """Retorna configuración recomendada para un tipo de documento."""
        settings = {
            DocumentType.FICTION: {
                "entity_detection": {
                    "focus": "characters",  # Priorizar detección de personajes
                    "detect_implicit": True,  # "El anciano" -> personaje
                    "min_mentions_for_entity": 2,
                },
                "semantic_fusion": {
                    "threshold": 0.82,
                    "allow_cross_type": False,  # No fusionar CHARACTER con CONCEPT
                },
                "analysis": {
                    "temporal_analysis": True,
                    "relationship_detection": True,
                    "behavior_consistency": True,
                    "dialog_analysis": True,
                },
                "alerts": {
                    "check_character_consistency": True,
                    "check_timeline": True,
                    "check_relationship_consistency": True,
                },
            },
            DocumentType.SELF_HELP: {
                "entity_detection": {
                    "focus": "concepts",  # Priorizar conceptos abstractos
                    "detect_implicit": False,
                    "min_mentions_for_entity": 3,  # Más conservador
                },
                "semantic_fusion": {
                    "threshold": 0.88,  # Más estricto para evitar fusiones incorrectas
                    "allow_cross_type": False,
                },
                "analysis": {
                    "temporal_analysis": False,  # No relevante
                    "relationship_detection": False,
                    "behavior_consistency": False,
                    "concept_tracking": True,  # Nuevo: rastrear conceptos
                },
                "alerts": {
                    "check_character_consistency": False,
                    "check_timeline": False,
                    "check_concept_consistency": True,
                },
            },
            DocumentType.ESSAY: {
                "entity_detection": {
                    "focus": "arguments",
                    "detect_implicit": False,
                    "min_mentions_for_entity": 2,
                },
                "semantic_fusion": {
                    "threshold": 0.85,
                    "allow_cross_type": False,
                },
                "analysis": {
                    "temporal_analysis": False,
                    "relationship_detection": False,
                    "argument_tracking": True,
                },
                "alerts": {
                    "check_character_consistency": False,
                    "check_citation_consistency": True,
                },
            },
            DocumentType.MEMOIR: {
                "entity_detection": {
                    "focus": "characters",  # Personas reales mencionadas
                    "detect_implicit": True,
                    "min_mentions_for_entity": 2,
                },
                "semantic_fusion": {
                    "threshold": 0.82,
                    "allow_cross_type": False,
                },
                "analysis": {
                    "temporal_analysis": True,  # Cronología de vida
                    "relationship_detection": True,
                    "behavior_consistency": False,  # Personas reales, no personajes
                },
                "alerts": {
                    "check_character_consistency": True,
                    "check_timeline": True,
                },
            },
            DocumentType.TECHNICAL: {
                "entity_detection": {
                    "focus": "technical_terms",
                    "detect_implicit": False,
                    "min_mentions_for_entity": 1,
                },
                "semantic_fusion": {
                    "threshold": 0.90,  # Muy estricto
                    "allow_cross_type": False,
                },
                "analysis": {
                    "temporal_analysis": False,
                    "terminology_consistency": True,
                },
                "alerts": {
                    "check_terminology_consistency": True,
                },
            },
            DocumentType.COOKBOOK: {
                "entity_detection": {
                    "focus": "ingredients",
                    "detect_implicit": False,
                    "min_mentions_for_entity": 1,
                },
                "semantic_fusion": {
                    "threshold": 0.90,
                    "allow_cross_type": False,
                },
                "analysis": {
                    "temporal_analysis": False,
                    "ingredient_tracking": True,
                },
                "alerts": {
                    "check_measurement_consistency": True,
                },
            },
        }

        return settings.get(doc_type, self._get_default_settings())

    def _get_default_settings(self) -> dict:
        """Retorna configuración por defecto (documento no clasificado)."""
        return {
            "entity_detection": {
                "focus": "balanced",
                "detect_implicit": True,
                "min_mentions_for_entity": 2,
            },
            "semantic_fusion": {
                "threshold": 0.85,
                "allow_cross_type": False,
            },
            "analysis": {
                "temporal_analysis": True,
                "relationship_detection": True,
            },
            "alerts": {
                "check_character_consistency": True,
            },
        }


# Singleton
_classifier: Optional[DocumentClassifier] = None


def get_document_classifier() -> DocumentClassifier:
    """Obtiene instancia singleton del clasificador."""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier()
    return _classifier


def classify_document(
    text: str,
    title: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> DocumentClassification:
    """
    Atajo para clasificar un documento.

    Args:
        text: Texto del documento
        title: Título opcional
        metadata: Metadatos opcionales

    Returns:
        DocumentClassification con tipo y configuración recomendada
    """
    return get_document_classifier().classify(text, title, metadata)
