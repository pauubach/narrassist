"""
Detector de cambios de registro narrativo.

Detecta cambios de registro narrativo (formal/informal, tecnico/coloquial)
que pueden indicar inconsistencias en la voz del narrador o entre escenas.

Diferencia con deviations.py:
- deviations.py: Desviaciones de voz por personaje individual
- register.py: Cambios de registro en la narracion general o entre escenas
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


class RegisterType(Enum):
    """Tipos de registro narrativo."""
    FORMAL_LITERARY = "formal_literary"  # Vocabulario culto, sintaxis elaborada
    NEUTRAL = "neutral"                   # Estandar, equilibrado
    COLLOQUIAL = "colloquial"            # Informal, cercano
    TECHNICAL = "technical"               # Jerga especializada
    POETIC = "poetic"                     # Metaforico, lirico


# Indicadores de registro formal/literario
FORMAL_INDICATORS: Set[str] = {
    # Verbos formales
    'contemplar', 'observar', 'percibir', 'manifestar', 'acontecer',
    'transcurrir', 'acaecer', 'proferir', 'esgrimir', 'denotar',
    'considerar', 'apreciar', 'constatar', 'evidenciar', 'inferir',
    'dilucidar', 'elucidar', 'discernir', 'vislumbrar', 'atisbar',
    # Conectores formales
    'asimismo', 'no obstante', 'sin embargo', 'empero', 'por ende',
    'en consecuencia', 'cabe destacar', 'en virtud de', 'habida cuenta',
    'ora', 'antano', 'otrora', 'acaso', 'ciertamente',
    # Vocabulario culto
    'vastedad', 'magnanimo', 'ignominia', 'sempiterno', 'inexorable',
    'pletora', 'aquiescencia', 'desazón', 'pesadumbre', 'congoja',
    'melancolía', 'añoranza', 'tribulación', 'zozobra', 'desasosiego',
    # Formas verbales cultas
    'hubiese', 'hubiere', 'aconteciese', 'acaeciere',
}

# Indicadores de registro coloquial
# NOTA: Usamos palabras completas, no substrings, para evitar falsos positivos
COLLOQUIAL_INDICATORS: Set[str] = {
    # Expresiones coloquiales clasicas
    'mola', 'flipar', 'currar', 'mogollon', 'rollo', 'molar',
    'flipante', 'pasada', 'guay', 'chulo', 'majo',
    'lio', 'movida', 'chungo', 'petar', 'tope', 'mazo',
    # Muletillas clasicas
    'colega', 'chaval', 'chavala', 'pavo', 'tronco',
    # Intensificadores coloquiales
    'flipando', 'petando', 'molando', 'brutal',
    # Lenguaje juvenil moderno / Gen Z
    'bro', 'crack', 'random', 'cringe', 'mood',
    'vibe', 'vibes', 'crush', 'hype', 'ghostear',
    'stalkear', 'shippear', 'trolear', 'lol', 'wtf',
    'pov', 'slay', 'based', 'goat', 'lit',
    'fam', 'squad', 'flow', 'chill', 'lowkey',
    'highkey', 'flex', 'savage', 'salty', 'sus',
    # Expresiones juveniles en espanol
    'flipo', 'locura', 'posta', 'heavy', 'fuerte',
    'rayada', 'rallado', 'colgado', 'pirao', 'empanao',
    'quedada', 'plan', 'rato', 'pego', 'morro',
}

# Patrones tecnicos por dominio
TECHNICAL_PATTERNS: List[str] = [
    # Medicos
    r'\b(diagnostico|sintoma|patologia|etiologia|pronostico|anamnesis)\b',
    r'\b(quirurgico|intervencion|lesion|traumatismo|secuela)\b',
    # Legales
    r'\b(jurisprudencia|tipificacion|prescripcion|prevaricacion)\b',
    r'\b(sentencia|dictamen|fallo|resolucion|alegato|demanda)\b',
    # Tecnologicos
    r'\b(algoritmo|interfaz|protocolo|implementacion|parametro)\b',
    r'\b(sistema|proceso|funcion|modulo|componente|arquitectura)\b',
    # Cientificos
    r'\b(hipotesis|variable|correlacion|metodologia|paradigma)\b',
    r'\b(experimento|muestra|analisis|resultado|conclusion)\b',
]

# Patrones poeticos
POETIC_PATTERNS: List[str] = [
    # Similes elaborados
    r'como\s+\w+\s+de\s+\w+\s+\w+',
    # Verbos poeticos
    r'\b(susurraba|murmuraba|danzaba|flotaba|brillaba|centelleaba)\b',
    # Personificacion de elementos naturales
    r'(el|la)\s+(luna|sol|viento|noche|mar|cielo)\s+(lloraba|cantaba|danzaba|susurraba|gritaba)',
    # Metaforas de color con verbos
    r'(sangraba|lloraba)\s+(carmesi|escarlata)',
]


@dataclass
class RegisterAnalysis:
    """Analisis de registro de un segmento de texto."""

    text_segment: str
    chapter: int
    position: int
    is_dialogue: bool

    primary_register: RegisterType
    register_scores: Dict[RegisterType, float] = field(default_factory=dict)
    confidence: float = 0.5

    # Indicadores encontrados
    formal_indicators: List[str] = field(default_factory=list)
    colloquial_indicators: List[str] = field(default_factory=list)
    technical_terms: List[str] = field(default_factory=list)
    poetic_devices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return {
            "text_segment": self.text_segment[:200] if self.text_segment else "",
            "chapter": self.chapter,
            "position": self.position,
            "is_dialogue": self.is_dialogue,
            "primary_register": self.primary_register.value,
            "register_scores": {k.value: v for k, v in self.register_scores.items()},
            "confidence": self.confidence,
            "formal_indicators": self.formal_indicators[:5],
            "colloquial_indicators": self.colloquial_indicators[:5],
            "technical_terms": self.technical_terms[:5],
            "poetic_devices": self.poetic_devices[:5],
        }


@dataclass
class RegisterChange:
    """Un cambio de registro detectado."""

    from_register: RegisterType
    to_register: RegisterType
    chapter: int
    position: int
    context_before: str
    context_after: str
    severity: str  # 'high', 'medium', 'low', 'none'
    explanation: str

    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return {
            "from_register": self.from_register.value,
            "to_register": self.to_register.value,
            "chapter": self.chapter,
            "position": self.position,
            "context_before": self.context_before[:100] if self.context_before else "",
            "context_after": self.context_after[:100] if self.context_after else "",
            "severity": self.severity,
            "explanation": self.explanation,
        }


class RegisterAnalyzer:
    """Analizador de registro narrativo."""

    def __init__(self):
        """Inicializa el analizador."""
        # Limpiar indicadores (remover entradas vacias)
        self.formal_set = {w for w in FORMAL_INDICATORS if w.strip()}
        self.colloquial_set = {w for w in COLLOQUIAL_INDICATORS if w.strip()}

        # Compilar patrones tecnicos y poeticos
        self.technical_patterns = []
        for pattern in TECHNICAL_PATTERNS:
            try:
                self.technical_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid technical pattern: {pattern}")

        self.poetic_patterns = []
        for pattern in POETIC_PATTERNS:
            try:
                self.poetic_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid poetic pattern: {pattern}")

    def analyze_segment(
        self,
        text: str,
        chapter: int,
        position: int,
        is_dialogue: bool = False
    ) -> RegisterAnalysis:
        """
        Analiza el registro de un segmento de texto.

        Args:
            text: Texto a analizar
            chapter: Numero de capitulo
            position: Posicion en el texto
            is_dialogue: Si es dialogo o narracion

        Returns:
            Analisis del registro
        """
        if not text or not text.strip():
            return RegisterAnalysis(
                text_segment="",
                chapter=chapter,
                position=position,
                is_dialogue=is_dialogue,
                primary_register=RegisterType.NEUTRAL,
                register_scores={r: 0.2 for r in RegisterType},
                confidence=0.0
            )

        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        # Encontrar indicadores formales (palabras completas o frases)
        formal_found = []
        for indicator in self.formal_set:
            if ' ' in indicator:
                # Es una frase, buscar como substring
                if indicator in text_lower:
                    formal_found.append(indicator)
            else:
                # Es una palabra, buscar en set de palabras
                if indicator in words:
                    formal_found.append(indicator)

        # Encontrar indicadores coloquiales (palabras completas)
        colloquial_found = [w for w in self.colloquial_set if w in words]

        # Encontrar terminos tecnicos
        technical_found = []
        for pattern in self.technical_patterns:
            matches = pattern.findall(text_lower)
            if matches:
                if isinstance(matches[0], tuple):
                    technical_found.extend([m[0] for m in matches])
                else:
                    technical_found.extend(matches)

        # Encontrar dispositivos poeticos
        poetic_found = []
        for pattern in self.poetic_patterns:
            matches = pattern.findall(text_lower)
            if matches:
                if isinstance(matches[0], tuple):
                    poetic_found.extend([' '.join(m) for m in matches])
                else:
                    poetic_found.extend(matches)

        # Calcular scores
        scores = self._calculate_scores(
            len(words),
            len(formal_found),
            len(colloquial_found),
            len(technical_found),
            len(poetic_found)
        )

        # Determinar registro primario
        primary = max(scores.items(), key=lambda x: x[1])[0]
        confidence = scores[primary]

        return RegisterAnalysis(
            text_segment=text[:200] + "..." if len(text) > 200 else text,
            chapter=chapter,
            position=position,
            is_dialogue=is_dialogue,
            primary_register=primary,
            register_scores=scores,
            confidence=confidence,
            formal_indicators=formal_found,
            colloquial_indicators=colloquial_found,
            technical_terms=technical_found[:5],
            poetic_devices=poetic_found[:5]
        )

    def _calculate_scores(
        self,
        total_words: int,
        formal_count: int,
        colloquial_count: int,
        technical_count: int,
        poetic_count: int
    ) -> Dict[RegisterType, float]:
        """
        Calcula scores normalizados por tipo de registro.

        Args:
            total_words: Total de palabras unicas
            formal_count: Indicadores formales encontrados
            colloquial_count: Indicadores coloquiales encontrados
            technical_count: Terminos tecnicos encontrados
            poetic_count: Dispositivos poeticos encontrados

        Returns:
            Diccionario con scores por tipo de registro
        """
        if total_words == 0:
            return {r: 0.2 for r in RegisterType}

        # Normalizar por longitud del texto
        norm = max(total_words / 100, 1)

        # Calcular scores individuales
        formal_score = min(formal_count / norm, 1.0) * 1.5  # Boost formal
        colloquial_score = min(colloquial_count / norm, 1.0) * 1.5  # Boost colloquial
        technical_score = min(technical_count / norm, 1.0) * 1.2
        poetic_score = min(poetic_count / norm, 1.0) * 1.2

        # Score neutral es inverso a los otros
        other_total = formal_score + colloquial_score + technical_score + poetic_score
        neutral_score = max(0.1, 1 - other_total * 0.5)

        scores = {
            RegisterType.FORMAL_LITERARY: formal_score,
            RegisterType.NEUTRAL: neutral_score,
            RegisterType.COLLOQUIAL: colloquial_score,
            RegisterType.TECHNICAL: technical_score,
            RegisterType.POETIC: poetic_score,
        }

        # Normalizar para que sumen 1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores


class RegisterChangeDetector:
    """Detector de cambios de registro en documentos."""

    def __init__(self, analyzer: Optional[RegisterAnalyzer] = None):
        """
        Inicializa el detector.

        Args:
            analyzer: Analizador de registro (opcional)
        """
        self.analyzer = analyzer or RegisterAnalyzer()
        self.analyses: List[RegisterAnalysis] = []

    def analyze_document(
        self,
        segments: List[Tuple[str, int, int, bool]]
    ) -> List[RegisterAnalysis]:
        """
        Analiza todos los segmentos del documento.

        Args:
            segments: Lista de tuplas (text, chapter, position, is_dialogue)

        Returns:
            Lista de analisis de registro
        """
        self.analyses = []

        for text, chapter, position, is_dialogue in segments:
            analysis = self.analyzer.analyze_segment(
                text, chapter, position, is_dialogue
            )
            self.analyses.append(analysis)

        logger.info(f"Analyzed {len(self.analyses)} segments for register")
        return self.analyses

    def detect_changes(
        self,
        min_severity: str = 'medium'
    ) -> List[RegisterChange]:
        """
        Detecta cambios significativos de registro.

        Args:
            min_severity: Severidad minima para reportar ('low', 'medium', 'high')

        Returns:
            Lista de cambios de registro detectados
        """
        changes = []

        # Filtrar solo narracion (no dialogos) para comparar
        narrative_analyses = [a for a in self.analyses if not a.is_dialogue]

        if len(narrative_analyses) < 2:
            return changes

        for i in range(1, len(narrative_analyses)):
            prev = narrative_analyses[i - 1]
            curr = narrative_analyses[i]

            # Si son del mismo registro, saltar
            if prev.primary_register == curr.primary_register:
                continue

            # Calcular severidad del cambio
            severity = self._calculate_severity(prev, curr)

            if self._should_report(severity, min_severity):
                changes.append(RegisterChange(
                    from_register=prev.primary_register,
                    to_register=curr.primary_register,
                    chapter=curr.chapter,
                    position=curr.position,
                    context_before=prev.text_segment,
                    context_after=curr.text_segment,
                    severity=severity,
                    explanation=self._generate_explanation(prev, curr)
                ))

        logger.info(f"Detected {len(changes)} register changes")
        return changes

    def _calculate_severity(
        self,
        prev: RegisterAnalysis,
        curr: RegisterAnalysis
    ) -> str:
        """
        Calcula severidad del cambio de registro.

        Args:
            prev: Analisis anterior
            curr: Analisis actual

        Returns:
            Severidad ('high', 'medium', 'low', 'none')
        """
        # Distancia entre registros
        register_distance = {
            (RegisterType.FORMAL_LITERARY, RegisterType.COLLOQUIAL): 'high',
            (RegisterType.COLLOQUIAL, RegisterType.FORMAL_LITERARY): 'high',
            (RegisterType.TECHNICAL, RegisterType.COLLOQUIAL): 'high',
            (RegisterType.COLLOQUIAL, RegisterType.TECHNICAL): 'high',
            (RegisterType.POETIC, RegisterType.TECHNICAL): 'medium',
            (RegisterType.TECHNICAL, RegisterType.POETIC): 'medium',
            (RegisterType.FORMAL_LITERARY, RegisterType.TECHNICAL): 'low',
            (RegisterType.TECHNICAL, RegisterType.FORMAL_LITERARY): 'low',
            (RegisterType.POETIC, RegisterType.FORMAL_LITERARY): 'low',
            (RegisterType.FORMAL_LITERARY, RegisterType.POETIC): 'low',
            (RegisterType.NEUTRAL, RegisterType.COLLOQUIAL): 'medium',
            (RegisterType.COLLOQUIAL, RegisterType.NEUTRAL): 'medium',
            (RegisterType.NEUTRAL, RegisterType.FORMAL_LITERARY): 'low',
            (RegisterType.FORMAL_LITERARY, RegisterType.NEUTRAL): 'low',
        }

        pair = (prev.primary_register, curr.primary_register)
        if pair in register_distance:
            return register_distance[pair]

        # Si cambia pero no esta en la tabla
        if prev.primary_register != curr.primary_register:
            return 'low'

        return 'none'

    def _should_report(self, severity: str, min_severity: str) -> bool:
        """
        Determina si debe reportarse segun severidad minima.

        Args:
            severity: Severidad del cambio
            min_severity: Severidad minima requerida

        Returns:
            True si debe reportarse
        """
        severity_order = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
        return severity_order.get(severity, 0) >= severity_order.get(min_severity, 0)

    def _generate_explanation(
        self,
        prev: RegisterAnalysis,
        curr: RegisterAnalysis
    ) -> str:
        """
        Genera explicacion del cambio.

        Args:
            prev: Analisis anterior
            curr: Analisis actual

        Returns:
            Explicacion textual del cambio
        """
        explanations = []

        if prev.formal_indicators and curr.colloquial_indicators:
            explanations.append(
                f"Cambio de lenguaje formal ('{prev.formal_indicators[0]}') "
                f"a coloquial ('{curr.colloquial_indicators[0]}')"
            )
        elif prev.colloquial_indicators and curr.formal_indicators:
            explanations.append(
                f"Cambio de lenguaje coloquial ('{prev.colloquial_indicators[0]}') "
                f"a formal ('{curr.formal_indicators[0]}')"
            )
        elif prev.technical_terms and curr.poetic_devices:
            explanations.append(
                f"Cambio de registro tecnico a poetico"
            )
        elif prev.poetic_devices and curr.technical_terms:
            explanations.append(
                f"Cambio de registro poetico a tecnico"
            )
        else:
            explanations.append(
                f"Cambio de registro {prev.primary_register.value} "
                f"a {curr.primary_register.value}"
            )

        return "; ".join(explanations)

    def get_register_distribution(self) -> Dict[RegisterType, int]:
        """
        Devuelve distribucion de registros en el documento.

        Returns:
            Diccionario con conteo por tipo de registro
        """
        distribution = Counter(a.primary_register for a in self.analyses)
        return dict(distribution)

    def get_summary(self) -> Dict:
        """
        Devuelve resumen del analisis de registro.

        Returns:
            Diccionario con resumen
        """
        if not self.analyses:
            return {
                'total_segments': 0,
                'narrative_segments': 0,
                'dialogue_segments': 0,
                'distribution': {},
                'dominant_register': None,
            }

        narrative = [a for a in self.analyses if not a.is_dialogue]
        dialogue = [a for a in self.analyses if a.is_dialogue]
        distribution = self.get_register_distribution()

        dominant = max(distribution.items(), key=lambda x: x[1])[0] if distribution else None

        return {
            'total_segments': len(self.analyses),
            'narrative_segments': len(narrative),
            'dialogue_segments': len(dialogue),
            'distribution': {k.value: v for k, v in distribution.items()},
            'dominant_register': dominant.value if dominant else None,
        }


def analyze_register_changes(
    segments: List[Tuple[str, int, int, bool]],
    min_severity: str = 'medium'
) -> Tuple[List[RegisterAnalysis], List[RegisterChange]]:
    """
    Funcion de conveniencia para analizar cambios de registro.

    Args:
        segments: Lista de tuplas (text, chapter, position, is_dialogue)
        min_severity: Severidad minima para reportar

    Returns:
        Tupla de (analisis, cambios)
    """
    detector = RegisterChangeDetector()
    analyses = detector.analyze_document(segments)
    changes = detector.detect_changes(min_severity)
    return analyses, changes
