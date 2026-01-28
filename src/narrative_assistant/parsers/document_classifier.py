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
    """Tipos de documento soportados (sincronizado con FeatureProfile)."""

    # Tipos principales
    FICTION = "fiction"           # Novela, cuento, relato
    ESSAY = "essay"               # Ensayo, artículo de opinión
    SELF_HELP = "self_help"       # Autoayuda, desarrollo personal
    TECHNICAL = "technical"       # Manual técnico, documentación
    MEMOIR = "memoir"             # Memorias, autobiografía

    # Nuevos tipos (añadidos para sincronizar con FeatureProfile)
    BIOGRAPHY = "biography"       # Biografías de terceros
    CELEBRITY = "celebrity"       # Libros de famosos/influencers
    DIVULGATION = "divulgation"   # Divulgación científica/histórica
    PRACTICAL = "practical"       # Cocina, jardinería, DIY, guías
    CHILDREN = "children"         # Infantil/juvenil
    DRAMA = "drama"               # Teatro, guiones cine/TV
    GRAPHIC = "graphic"           # Novela gráfica, cómic, manga

    # Tipos legacy (mapear a nuevos)
    COOKBOOK = "cookbook"         # -> PRACTICAL
    ACADEMIC = "academic"         # -> ESSAY

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
    # Metacognición del autor (exclusivo de memoir)
    "author_metacognition": [
        r'\b(ahora\s+(sé|entiendo)|mirando\s+atrás)\b',
        r'\b(no\s+recuerdo\s+(bien|exactamente)|creo\s+que\s+era)\b',
        r'\b(según\s+me\s+(contaron|dijeron))\b',
    ],
}

# ============================================================================
# NUEVOS TIPOS - Sincronizados con FeatureProfile
# ============================================================================

BIOGRAPHY_INDICATORS = {
    # Nacimiento y origen en tercera persona
    "birth_origin": [
        r'\b(nació|nacía)\s+(en|el)\b',
        r'\bvino\s+al\s+mundo\b',
        r'\b(era|fue)\s+(hijo|hija)\s+de\b',
    ],
    # Fuentes y testimonios (muy discriminativo)
    "sources_testimony": [
        r'\bsegún\s+(testimonios?|fuentes|relatos)\b',
        r'\b(testigos|contemporáneos)\s+(afirman|relatan)\b',
        r'\bsegún\s+(su\s+)?(biógrafo|historiador)\b',
    ],
    # Muerte y legado
    "death_legacy": [
        r'\b(falleció|murió)\s+(en|el|a\s+los)\b',
        r'\bsus\s+últimos\s+(días|años|momentos)\b',
        r'\b(dejó|legó)\s+(un|una|su)\s+(legado|huella|obra)\b',
    ],
}

CELEBRITY_INDICATORS = {
    # Vocabulario de redes sociales
    "social_media_audience": [
        r'\bmis?\s+(seguidores?|followers?|suscriptores?)\b',
        r'\bmi\s+(comunidad|audiencia|público)\b',
        r'\b(Instagram|TikTok|YouTube|Twitter|redes\s+sociales)\b',
    ],
    # Marca personal
    "personal_brand": [
        r'\bmi\s+(marca|proyecto|negocio|emprendimiento)\b',
        r'\b(monetizar|facturar|generar\s+ingresos)\b',
        r'\b(colaboración|sponsor|patrocinador)\b',
    ],
    # Relación parasocial
    "parasocial_relationship": [
        r'\bustedes\s+(saben|conocen|me\s+conocen)\b',
        r'\b(gracias\s+a\s+ustedes?|sin\s+ustedes?)\b',
        r'\bmi\s+(historia|experiencia)\s+con\s+ustedes\b',
    ],
}

DIVULGATION_INDICATORS = {
    # Referencias a estudios
    "study_references": [
        r'\b(un\s+)?estudio\s+(demuestra|revela|sugiere|indica)\b',
        r'\b(la\s+)?investigación\s+(científica\s+)?(demuestra|sugiere)\b',
        r'\b(según|de\s+acuerdo\s+con)\s+(la\s+)?ciencia\b',
    ],
    # Científicos como agentes
    "scientist_agents": [
        r'\b(los\s+)?científicos\s+(descubrieron|encontraron|afirman)\b',
        r'\b(los\s+)?investigadores\s+(han\s+)?(demostrado|descubierto)\b',
        r'\b(los\s+)?expertos\s+(señalan|indican|advierten)\b',
    ],
    # Datos curiosos
    "curiosity_markers": [
        r'\b(curioso|sorprendente|fascinante)\s+(es\s+que|resulta)\b',
        r'\¿sabías\s+que\b',
        r'\blo\s+que\s+(pocos|muchos)\s+saben\b',
    ],
    # Comparaciones didácticas
    "didactic_comparisons": [
        r'\bes\s+como\s+si\b',
        r'\bimagina\s+(que|un[ao]?)\b',
        r'\bpiensa\s+en\s+(un[ao]?|cómo)\b',
    ],
}

PRACTICAL_INDICATORS = {
    # Ingredientes con medidas
    "ingredients_measures": [
        r'\d+\s*(g|kg|ml|l|cucharada|taza|unidad)s?\s+(de\s+)?\w+',
        r'\b(harina|azúcar|sal|aceite|huevo|leche|mantequilla)\b',
    ],
    # Pasos numerados
    "numbered_steps": [
        r'^\s*(Paso\s+)?\d+[.):]\s+[A-ZÁÉÍÓÚÑ]',
        r'\bprimero,?\s+\w+.*\bluego,?\s+\w+',
    ],
    # Tiempos de preparación
    "preparation_times": [
        r'\btiempo\s+(de\s+)?(preparación|cocción)\s*[:\-]?\s*\d+',
        r'\bdurante\s+\d+\s*(minutos?|horas?)\b',
        r'\b\d+\s*°C\b',
    ],
    # Verbos imperativos
    "imperative_instructions": [
        r'\b(mezcl[ae]|bat[ae]|añad[ae]|horn[ae]a|cocin[ae]|cort[ae]|pel[ae])\b',
        r'\b(dobla|pega|recorta|pinta|mide|marca)\b',
    ],
}

CHILDREN_INDICATORS = {
    # Onomatopeyas
    "onomatopoeia": [
        r'\b¡?(Pum|Zas|Plop|Crac|Bum|Miau|Guau|Muuu|Piip)!?\b',
        r'\b(tic-tac|pim-pam|rin-rin)\b',
    ],
    # Fórmulas narrativas clásicas
    "classic_formulas": [
        r'\b(Había|Érase)\s+una\s+vez\b',
        r'\bcolorín\s+colorado\b',
        r'\by\s+fueron\s+felices\b',
    ],
    # Preguntas al lector
    "reader_questions": [
        r'\¿(Sabes|Puedes|Quieres|Adivina)\s+(qué|quién|cómo|dónde)\b',
        r'\¿(Te\s+gusta|Conoces|Has\s+visto)\b',
    ],
    # Repeticiones intencionales
    "intentional_repetitions": [
        r'\b(\w{3,})\s+y\s+\1\b',  # "grande y grande"
        r'\bmuy,?\s+muy\b',
    ],
    # Vocabulario simple y diminutivos
    "simple_vocabulary": [
        r'\b\w+it[oa]s?\b',  # Diminutivos: -ito, -ita
        r'\b(mamá|papá|abuelito|hermanito)\b',
    ],
}

DRAMA_INDICATORS = {
    # Personaje: diálogo - nombres con vocales (excluye romanos IVXLC)
    "character_dialogue_format": [
        r'^([A-ZÁÉÍÓÚÑ]*[AEIOUÁÉÍÓÚ][A-ZÁÉÍÓÚÑ]*)\s*[:\-—]+\s*[a-záéíóúñ¡¿]',  # PERSONAJE: diálogo
        r'^([A-ZÁÉÍÓÚÑ]*[AEIOUÁÉÍÓÚ][A-ZÁÉÍÓÚÑ]*)\s*\.\s*[-—]+',  # PERSONAJE. —
    ],
    # Acotaciones escénicas
    "stage_directions": [
        r'\((Se\s+levanta|Entra|Sale|Pausa|Silencio|Aparte)[^)]*\)',
        r'\((con|en\s+voz|mirando|hacia)[^)]*\)',
    ],
    # Estructura de actos/escenas
    "act_scene_structure": [
        r'^(ACTO|ESCENA|CUADRO|JORNADA)\s+([IVXLC]+|\d+)',
        r'\b(Primer|Segundo|Tercer)\s+(acto|cuadro)\b',
    ],
    # Sluglines de cine
    "sluglines": [
        r'^(INT\.|EXT\.)\s+[A-ZÁÉÍÓÚÑ\s]+\s*[-–—]\s*(DÍA|NOCHE|AMANECER)',
        r'^(INTERIOR|EXTERIOR)\s+[-–—]',
    ],
    # Transiciones de cine/TV
    "transitions": [
        r'^(FADE\s+(IN|OUT)|CORTE\s+A|FUNDIDO|DISOLVENCIA)',
        r'^(FIN\s+DE\s+)?(ACTO|ESCENA)',
    ],
}

GRAPHIC_INDICATORS = {
    # Onomatopeyas mayúsculas
    "onomatopoeia_caps": [
        r'\b(BOOM|CRASH|BANG|ZAP|POW|KABOOM|WHAM|CRACK|SPLASH)!*\b',
        r'\b(AAARGH|AAAH|NOOO|SIII)!*\b',
    ],
    # Acotaciones visuales
    "visual_directions": [
        r'\[(viñeta|plano|panel|splash|página)[^\]]*\]',
        r'\b(viñeta|panel)\s+\d+\b',
    ],
    # Puntuación enfática
    "emphatic_punctuation": [
        r'[!?]{2,}',
        r'\b[A-ZÁÉÍÓÚÑ]{4,}[!?]+',  # PALABRAS EN MAYÚSCULAS!
    ],
    # Globos de texto
    "speech_bubbles": [
        r'\b(globo|bocadillo)\s+(de\s+)?(texto|diálogo|pensamiento)\b',
        r'\b(off|voz\s+en\s+off)\b',
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
        # FICTION
        "dialog_markers": 2.0,
        "narrative_descriptions": 1.5,
        "character_actions": 1.5,
        "narrative_structures": 1.0,
        # SELF_HELP
        "direct_advice": 2.0,
        "abstract_concepts": 1.5,
        "tips_structure": 1.5,
        "rhetorical_questions": 1.0,
        # ESSAY
        "argumentation": 1.5,
        "references": 2.0,
        "abstract_reflection": 1.0,
        # TECHNICAL
        "technical_terms": 2.0,
        "instructions": 1.5,
        "code_markers": 2.5,
        # COOKBOOK (legacy -> PRACTICAL)
        "ingredients": 3.0,
        "cooking_instructions": 2.5,
        # MEMOIR
        "first_person_past": 1.5,
        "autobiographical": 1.5,
        "author_metacognition": 2.5,  # Muy discriminativo
        # BIOGRAPHY
        "birth_origin": 2.0,
        "sources_testimony": 3.0,  # Muy discriminativo
        "death_legacy": 2.0,
        # CELEBRITY
        "social_media_audience": 3.0,  # Exclusivo del género
        "personal_brand": 2.0,
        "parasocial_relationship": 2.5,
        # DIVULGATION
        "study_references": 2.0,
        "scientist_agents": 2.5,
        "curiosity_markers": 2.0,
        "didactic_comparisons": 1.5,
        # PRACTICAL
        "ingredients_measures": 3.0,
        "numbered_steps": 2.0,
        "preparation_times": 2.0,
        "imperative_instructions": 2.0,
        # CHILDREN
        "onomatopoeia": 2.5,
        "classic_formulas": 2.8,  # "Había una vez" muy discriminativo
        "reader_questions": 2.0,
        "intentional_repetitions": 1.5,
        "simple_vocabulary": 1.5,
        # DRAMA
        "character_dialogue_format": 3.0,  # Muy discriminativo
        "stage_directions": 2.5,
        "act_scene_structure": 3.0,  # Muy discriminativo
        "sluglines": 3.0,  # Guiones de cine
        "transitions": 2.0,
        # GRAPHIC
        "onomatopoeia_caps": 2.5,
        "visual_directions": 3.0,
        "emphatic_punctuation": 1.5,
        "speech_bubbles": 2.5,
    }

    # Configuración de muestreo múltiple
    SAMPLE_POSITIONS = [0.10, 0.50, 0.90]  # 10%, 50%, 90% del documento
    SAMPLE_SIZE = 5000  # Caracteres por muestra

    def classify(
        self,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DocumentClassification:
        """
        Clasifica un documento basándose en su contenido.

        Usa muestreo múltiple (10%, 50%, 90% del documento) para evitar
        sesgos por preámbulos, índices o secciones no representativas.

        Args:
            text: Texto del documento completo
            title: Título del documento (opcional, ayuda en clasificación)
            metadata: Metadatos adicionales (opcional)

        Returns:
            DocumentClassification con tipo, confianza e indicadores
        """
        # Obtener muestras del documento en múltiples posiciones
        samples = self._get_samples(text)
        combined_sample = "\n".join(samples)
        sample_lower = combined_sample.lower()

        logger.debug(
            f"Clasificando documento: {len(text)} chars, "
            f"{len(samples)} muestras de ~{len(combined_sample)} chars total"
        )

        # Calcular puntuación para cada tipo
        scores = {
            # Tipos principales
            DocumentType.FICTION: self._score_fiction(combined_sample, sample_lower),
            DocumentType.SELF_HELP: self._score_self_help(combined_sample, sample_lower),
            DocumentType.ESSAY: self._score_essay(combined_sample, sample_lower),
            DocumentType.TECHNICAL: self._score_technical(combined_sample, sample_lower),
            DocumentType.MEMOIR: self._score_memoir(combined_sample, sample_lower),
            # Nuevos tipos sincronizados con FeatureProfile
            DocumentType.BIOGRAPHY: self._score_biography(combined_sample, sample_lower),
            DocumentType.CELEBRITY: self._score_celebrity(combined_sample, sample_lower),
            DocumentType.DIVULGATION: self._score_divulgation(combined_sample, sample_lower),
            DocumentType.PRACTICAL: self._score_practical(combined_sample, sample_lower),
            DocumentType.CHILDREN: self._score_children(combined_sample, sample_lower),
            DocumentType.DRAMA: self._score_drama(combined_sample, sample_lower),
            DocumentType.GRAPHIC: self._score_graphic(combined_sample, sample_lower),
            # Legacy (mantenidos por compatibilidad, peso reducido)
            DocumentType.COOKBOOK: self._score_cookbook(combined_sample, sample_lower),
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

    def _get_samples(self, text: str) -> list[str]:
        """
        Extrae muestras del documento en múltiples posiciones.

        Para documentos cortos (<15000 chars), usa el texto completo.
        Para documentos largos, extrae muestras en 10%, 50% y 90% del texto.

        Args:
            text: Texto completo del documento

        Returns:
            Lista de muestras de texto
        """
        text_len = len(text)

        # Si el documento es corto, usar todo
        if text_len <= self.SAMPLE_SIZE * 3:
            return [text]

        samples = []
        for position in self.SAMPLE_POSITIONS:
            start = int(text_len * position)
            # Ajustar para no cortar palabras (buscar espacio cercano)
            if start > 0:
                # Buscar inicio de palabra/oración
                space_pos = text.find(" ", start)
                if space_pos != -1 and space_pos - start < 100:
                    start = space_pos + 1

            end = min(start + self.SAMPLE_SIZE, text_len)
            sample = text[start:end]

            # Evitar muestras duplicadas si el documento es pequeño
            if sample and sample not in samples:
                samples.append(sample)

        return samples if samples else [text[:self.SAMPLE_SIZE]]

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

    # ========================================================================
    # Nuevos métodos de scoring para tipos sincronizados con FeatureProfile
    # ========================================================================

    def _score_biography(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de biografía."""
        return self._count_matches(text, BIOGRAPHY_INDICATORS)

    def _score_celebrity(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de libros de famosos/influencers."""
        return self._count_matches(text, CELEBRITY_INDICATORS)

    def _score_divulgation(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de divulgación científica/histórica."""
        return self._count_matches(text, DIVULGATION_INDICATORS)

    def _score_practical(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de libros prácticos (cocina, DIY, guías)."""
        return self._count_matches(text, PRACTICAL_INDICATORS)

    def _score_children(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de literatura infantil/juvenil."""
        return self._count_matches(text, CHILDREN_INDICATORS)

    def _score_drama(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de teatro y guiones."""
        return self._count_matches(text, DRAMA_INDICATORS)

    def _score_graphic(self, text: str, text_lower: str) -> tuple[float, list[str]]:
        """Puntúa indicadores de novela gráfica/cómic."""
        return self._count_matches(text, GRAPHIC_INDICATORS)

    def _adjust_scores_from_title(
        self,
        title_lower: str,
        scores: dict[DocumentType, tuple[float, list[str]]],
    ) -> None:
        """Ajusta puntuaciones basándose en el título."""
        title_hints = {
            # Tipos principales
            DocumentType.FICTION: ["novela", "cuento", "relato", "historia de", "aventuras"],
            DocumentType.SELF_HELP: ["cómo", "secretos de", "guía para", "manual de vida",
                                     "felicidad", "éxito", "superación", "autoayuda"],
            DocumentType.ESSAY: ["ensayo", "reflexiones", "pensamiento", "filosofía"],
            DocumentType.TECHNICAL: ["manual", "guía técnica", "tutorial", "documentación"],
            DocumentType.COOKBOOK: ["recetas", "cocina", "gastronomía", "chef"],
            DocumentType.MEMOIR: ["memorias", "autobiografía", "mi vida", "recuerdos"],
            # Nuevos tipos
            DocumentType.BIOGRAPHY: ["biografía", "vida de", "vida y obra"],
            DocumentType.CELEBRITY: ["mi historia", "mi verdad", "sin filtros", "@"],
            DocumentType.DIVULGATION: ["divulgación", "ciencia", "historia de la"],
            DocumentType.PRACTICAL: ["guía práctica", "hágalo usted", "diy", "bricolaje",
                                     "jardín", "manualidades"],
            DocumentType.CHILDREN: ["infantil", "juvenil", "cuentos para niños", "fábulas"],
            DocumentType.DRAMA: ["teatro", "obra dramática", "comedia", "tragedia", "guión"],
            DocumentType.GRAPHIC: ["cómic", "novela gráfica", "manga", "historieta"],
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
