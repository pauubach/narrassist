"""
Sistema de corrección ortográfica multi-votante con arbitraje LLM.

Combina múltiples correctores ortográficos con votación ponderada por confianza:
1. pyspellchecker - Pure Python, diccionario español incluido
2. chunspell (hunspell) - Diccionario hunspell precompilado
3. symspellpy - Algoritmo SymSpell de alta velocidad
4. LanguageTool - Servidor local Java (gramática + ortografía)

Lógica de decisión:
- Si hay consenso con alta confianza (≥0.7) → Aceptar
- Si hay consenso con baja confianza (<0.7) → Consultar LLM
- Si hay conflicto entre votantes → Consultar LLM
- LLM solo recibe las palabras/frases en duda (optimización)

Uso:
    from narrative_assistant.nlp.orthography.voting_checker import VotingSpellingChecker

    checker = VotingSpellingChecker()
    result = checker.check(text)
"""

import contextlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...core.result import Result
from .base import (
    DetectionMethod,
    SpellingErrorType,
    SpellingIssue,
    SpellingReport,
    SpellingSeverity,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuración
# =============================================================================

# Umbrales de confianza
CONFIDENCE_HIGH = 0.75  # Consenso alto → aceptar sin LLM
CONFIDENCE_MEDIUM = 0.50  # Consenso medio → puede necesitar LLM
CONFIDENCE_LOW = 0.30  # Consenso bajo → siempre consultar LLM

# Pesos de cada votante (suman 1.0)
# Calibrados según evaluación con prueba_ortografia.txt (51 errores gold):
#
# Resultados medidos 2026-01-19:
# - patterns:       P=87.3%, R=69.7%, F1=77.5% → Mejor precisión Y buen recall
# - symspell:       P=74.2%, R=46.5%, F1=57.1% → Alta precisión, bajo recall
# - hunspell:       P=63.5%, R=54.5%, F1=58.7% → Equilibrado
# - languagetool:   P=62.2%, R=79.8%, F1=69.9% → Mejor recall, buena precisión
# - pyspellchecker: P=40.0%, R=62.6%, F1=48.8% → Bajo todo, ruidoso
# - beto:           P=26.6%, R=80.8%, F1=40.0% → Muy ruidoso pero alto recall
#
# Estrategia de pesos:
# - Mayor peso a votantes con mejor F1 y precision
# - BETO y pyspellchecker se usan principalmente para aumentar recall
VOTER_WEIGHTS = {
    "patterns": 0.26,  # MEJOR: P=87.3%, R=69.7%, F1=77.5% - Muy rápido y preciso
    "languagetool": 0.24,  # BUENO: P=62.2%, R=79.8%, F1=69.9% - Alto recall, contexto
    "symspell": 0.16,  # MEDIO: P=74.2%, R=46.5%, F1=57.1% - Muy rápido
    "hunspell": 0.14,  # MEDIO: P=63.5%, R=54.5%, F1=58.7% - Diccionario profesional
    "beto": 0.12,  # MEJORADO: P=45.3%, R=85.7%, F1=59.3% - BETO base
    "pyspellchecker": 0.08,  # BAJO:  P=40.0%, R=62.6% - Solo para recall
}
# Total: 0.26 + 0.24 + 0.16 + 0.14 + 0.12 + 0.08 = 1.00

# Umbral mínimo de votos para aceptar sin LLM
MIN_VOTERS_FOR_CONSENSUS = 2
MIN_CONFIDENCE_FOR_CONSENSUS = 0.65


class VoterStatus(Enum):
    """Estado de cada votante."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class Vote:
    """Voto de un corrector individual."""

    voter_name: str
    is_error: bool  # True si detecta error
    confidence: float  # 0.0-1.0
    suggestions: list[str] = field(default_factory=list)
    error_type: SpellingErrorType | None = None
    raw_response: dict | None = None


@dataclass
class VotingResult:
    """Resultado agregado de la votación."""

    word: str
    start_char: int
    end_char: int
    sentence: str

    # Votos individuales
    votes: list[Vote] = field(default_factory=list)

    # Resultado agregado
    is_error: bool = False
    aggregated_confidence: float = 0.0
    needs_llm_arbitration: bool = False

    # Después de arbitraje LLM (si aplica)
    llm_verdict: bool | None = None
    llm_confidence: float | None = None
    llm_explanation: str | None = None

    # Resultado final
    final_suggestions: list[str] = field(default_factory=list)
    final_error_type: SpellingErrorType = SpellingErrorType.MISSPELLING

    @property
    def voters_detecting_error(self) -> int:
        """Número de votantes que detectan error."""
        return sum(1 for v in self.votes if v.is_error)

    @property
    def voters_total(self) -> int:
        """Número total de votantes que respondieron."""
        return len(self.votes)

    @property
    def consensus_ratio(self) -> float:
        """Ratio de consenso (0.0-1.0)."""
        if not self.votes:
            return 0.0
        error_votes = self.voters_detecting_error
        return max(error_votes, len(self.votes) - error_votes) / len(self.votes)


# =============================================================================
# Votantes individuales
# =============================================================================


class BaseVoter:
    """Clase base para votantes."""

    name: str = "base"
    weight: float = 0.1
    _available: bool
    _init_error: str | None

    def __init__(self):
        self._available = False
        self._init_error: str | None = None

    @property
    def is_available(self) -> bool:
        # _available es bool, el tipo de retorno es correcto
        return self._available

    def check_word(self, word: str, context: str = "") -> Vote | None:
        """Verificar una palabra. Retorna None si no disponible."""
        raise NotImplementedError


class PySpellCheckerVoter(BaseVoter):
    """Votante usando pyspellchecker (pure Python)."""

    name = "pyspellchecker"
    weight = VOTER_WEIGHTS["pyspellchecker"]

    def __init__(self):
        super().__init__()
        try:
            from spellchecker import SpellChecker

            self._checker = SpellChecker(language="es")
            self._available = True
            logger.info("PySpellChecker inicializado correctamente")
        except ImportError:
            self._init_error = "pyspellchecker no instalado (pip install pyspellchecker)"
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Error inicializando pyspellchecker: {e}"
            logger.warning(self._init_error)

    def check_word(self, word: str, context: str = "") -> Vote | None:
        if not self._available:
            return None

        try:
            word_lower = word.lower()

            # Verificar si está en el diccionario
            is_unknown = word_lower in self._checker.unknown([word_lower])

            if is_unknown:
                suggestions = list(self._checker.candidates(word_lower) or [])[:5]
                # Confianza basada en distancia de edición
                if suggestions:
                    # Si hay sugerencias cercanas, más confianza
                    confidence = 0.7
                else:
                    confidence = 0.5

                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=confidence,
                    suggestions=suggestions,
                    error_type=SpellingErrorType.MISSPELLING,
                )
            else:
                return Vote(
                    voter_name=self.name,
                    is_error=False,
                    confidence=0.8,
                )
        except Exception as e:
            logger.debug(f"Error en pyspellchecker para '{word}': {e}")
            return None


class ChunspellVoter(BaseVoter):
    """Votante usando chunspell (hunspell precompilado)."""

    name = "hunspell"
    weight = VOTER_WEIGHTS["hunspell"]

    def __init__(self, dict_path: Path | None = None):
        super().__init__()
        try:
            # chunspell installs as 'hunspell' module
            import hunspell

            # Buscar diccionarios españoles
            dict_base = self._find_spanish_dict(dict_path)
            if dict_base:
                # Hunspell expects base path; it adds .aff and .dic automatically
                self._checker = hunspell.Hunspell(dict_base)
                self._available = True
                logger.info(f"Hunspell inicializado con diccionario: {dict_base}")
            else:
                self._init_error = "Diccionario español no encontrado para hunspell"
                logger.warning(self._init_error)

        except ImportError:
            self._init_error = "hunspell no instalado (pip install chunspell)"
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Error inicializando hunspell: {e}"
            logger.warning(self._init_error)

    def _find_spanish_dict(self, custom_path: Path | None = None) -> str | None:
        """Buscar diccionarios españoles en ubicaciones comunes.

        Returns path without extension - hunspell adds .aff and .dic automatically.
        """
        if custom_path:
            base_path = custom_path.with_suffix("")  # Remove extension if any
            if base_path.with_suffix(".aff").exists() and base_path.with_suffix(".dic").exists():
                return str(base_path)

        # Ubicaciones comunes (base paths without extension)
        common_paths = [
            Path.home() / ".narrative_assistant" / "dictionaries" / "es_ES",
            Path("/usr/share/hunspell/es_ES"),
            Path("/usr/share/myspell/es_ES"),
            Path("C:/Program Files/LibreOffice/share/extensions/dict-es/es_ES"),
        ]

        for base_path in common_paths:
            aff = base_path.with_suffix(".aff")
            dic = base_path.with_suffix(".dic")
            if aff.exists() and dic.exists():
                return str(base_path)

        return None

    def check_word(self, word: str, context: str = "") -> Vote | None:
        if not self._available:
            return None

        try:
            is_correct = self._checker.spell(word)

            if not is_correct:
                suggestions = self._checker.suggest(word)[:5]
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.85,  # Hunspell tiene alta precisión
                    suggestions=suggestions,
                    error_type=SpellingErrorType.MISSPELLING,
                )
            else:
                return Vote(
                    voter_name=self.name,
                    is_error=False,
                    confidence=0.90,
                )
        except Exception as e:
            logger.debug(f"Error en chunspell para '{word}': {e}")
            return None


class SymSpellVoter(BaseVoter):
    """Votante usando symspellpy (algoritmo SymSpell)."""

    name = "symspell"
    weight = VOTER_WEIGHTS["symspell"]

    def __init__(self, dict_path: Path | None = None):
        super().__init__()
        try:
            from symspellpy import SymSpell, Verbosity

            self._symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
            self._verbosity = Verbosity.CLOSEST

            # Cargar diccionario de frecuencias
            dict_loaded = self._load_dictionary(dict_path)

            if dict_loaded:
                self._available = True
                logger.info("SymSpell inicializado correctamente")
            else:
                self._init_error = "No se pudo cargar diccionario para SymSpell"
                logger.warning(self._init_error)

        except ImportError:
            self._init_error = "symspellpy no instalado (pip install symspellpy)"
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Error inicializando symspellpy: {e}"
            logger.warning(self._init_error)

    def _load_dictionary(self, custom_path: Path | None = None) -> bool:
        """Cargar diccionario de frecuencias español."""

        # Intentar cargar diccionario personalizado
        if custom_path and custom_path.exists():
            # El método load_dictionary retorna el tipo correcto
            loaded = self._symspell.load_dictionary(str(custom_path), term_index=0, count_index=1)
            return bool(loaded)

        # Buscar en ubicaciones comunes
        common_paths = [
            Path.home() / ".narrative_assistant" / "dictionaries" / "es_frequency.txt",
            Path.home() / ".narrative_assistant" / "dictionaries" / "es_frequency_raw.txt",
            Path.home() / ".narrative_assistant" / "dictionaries" / "es_50k.txt",
            Path.home() / ".narrative_assistant" / "dictionaries" / "spanish_frequency.txt",
        ]

        for path in common_paths:
            if path.exists():
                try:
                    loaded = self._symspell.load_dictionary(str(path), term_index=0, count_index=1)
                    if loaded:
                        logger.info(f"SymSpell: diccionario cargado desde {path}")
                        return True
                except Exception as e:
                    logger.debug(f"Error cargando {path}: {e}")
                    continue

        logger.warning("SymSpell: no se encontró diccionario español")
        return False

    def check_word(self, word: str, context: str = "") -> Vote | None:
        if not self._available:
            return None

        try:
            from symspellpy import Verbosity

            suggestions = self._symspell.lookup(
                word.lower(), Verbosity.CLOSEST, max_edit_distance=2
            )

            if not suggestions:
                # No encontrado - posible error
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.6,
                    suggestions=[],
                    error_type=SpellingErrorType.MISSPELLING,
                )

            best = suggestions[0]

            if best.term.lower() == word.lower():
                # Palabra encontrada exacta
                return Vote(
                    voter_name=self.name,
                    is_error=False,
                    confidence=0.85,
                )
            else:
                # Hay sugerencias diferentes
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.7 if best.distance <= 1 else 0.5,
                    suggestions=[s.term for s in suggestions[:5]],
                    error_type=SpellingErrorType.MISSPELLING,
                )

        except Exception as e:
            logger.debug(f"Error en symspell para '{word}': {e}")
            return None


class LanguageToolVoter(BaseVoter):
    """Votante usando LanguageTool (language_tool_python o servidor local)."""

    name = "languagetool"
    weight = VOTER_WEIGHTS["languagetool"]

    # Reglas de LanguageTool a deshabilitar por defecto
    # Evita falsos positivos con conjunciones/preposiciones comunes
    DEFAULT_DISABLED_RULES = [
        "SPANISH_WORD_REPEAT_RULE",  # Palabras repetidas (falso positivo con "y", "que")
        "WORD_REPEAT_RULE",  # Variante general
        "MORFOLOGIK_RULE_ES",  # A veces detecta neologismos válidos
    ]

    def __init__(self, disabled_rules: list[str] | None = None):
        super().__init__()
        self._tool = None
        self._use_python_lib = False
        self._disabled_rules = (
            disabled_rules if disabled_rules is not None else self.DEFAULT_DISABLED_RULES
        )

        # Configurar Java 17 si está disponible
        self._setup_java17()

        # Intentar primero language_tool_python (más fácil de usar)
        try:
            import language_tool_python

            self._tool = language_tool_python.LanguageTool("es")
            self._use_python_lib = True
            self._available = True
            logger.info("LanguageTool inicializado con language_tool_python")
            return
        except Exception as e:
            logger.debug(f"language_tool_python no disponible: {e}")

        # Fallback: usar cliente de servidor local
        try:
            from ..grammar.languagetool_client import get_languagetool_client

            self._client = get_languagetool_client()
            if self._client.is_available():
                self._available = True
                logger.info("LanguageTool votante inicializado (servidor local)")
            else:
                self._init_error = "LanguageTool no disponible"
                logger.warning(self._init_error)

        except ImportError:
            self._init_error = "Módulo LanguageTool no disponible"
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Error inicializando LanguageTool: {e}"
            logger.warning(self._init_error)

    def _setup_java17(self):
        """Configurar Java 17 si está disponible."""
        import os

        java17_paths = [
            r"C:\Program Files\Microsoft\jdk-17.0.17.10-hotspot",
            r"C:\Program Files\Eclipse Adoptium\jdk-17",
            r"C:\Program Files\Java\jdk-17",
        ]
        for java_path in java17_paths:
            if Path(java_path).exists():
                os.environ["JAVA_HOME"] = java_path
                os.environ["PATH"] = f"{java_path}\\bin;{os.environ.get('PATH', '')}"
                logger.debug(f"Java 17 configurado: {java_path}")
                return

    def close(self):
        """Cerrar el cliente LanguageTool."""
        if self._tool and self._use_python_lib:
            with contextlib.suppress(Exception):
                self._tool.close()

    def check_word(self, word: str, context: str = "") -> Vote | None:
        """LanguageTool necesita contexto, no palabras individuales."""
        return None

    def check_text(self, text: str) -> list[tuple[str, int, int, Vote]]:
        """Verificar texto completo con LanguageTool."""
        if not self._available:
            return []

        results = []
        try:
            if self._use_python_lib and self._tool:
                # Usar language_tool_python
                matches = self._tool.check(text)
                for match in matches:
                    # Filtrar reglas deshabilitadas
                    rule_id = getattr(match, "rule_id", getattr(match, "ruleId", ""))
                    if rule_id in self._disabled_rules:
                        continue

                    # language_tool_python usa snake_case (error_length, rule_id)
                    error_len = getattr(match, "error_length", getattr(match, "errorLength", 0))
                    word = text[match.offset : match.offset + error_len]
                    # Limpiar newlines/whitespace del word
                    word_clean = word.replace("\n", " ").replace("\r", " ").strip()
                    error_type = self._map_category(match.category or "")

                    vote = Vote(
                        voter_name=self.name,
                        is_error=True,
                        confidence=0.85,
                        suggestions=match.replacements[:5],
                        error_type=error_type,
                        raw_response={
                            "rule_id": rule_id,
                            "message": match.message,
                            "category": match.category,
                        },
                    )
                    # Ignorar errores en whitespace/newlines
                    if word_clean:
                        results.append((word_clean, match.offset, match.offset + error_len, vote))
            else:
                # Usar cliente de servidor local con reglas deshabilitadas
                check_result = self._client.check(
                    text, language="es", disabled_rules=self._disabled_rules
                )
                for match in getattr(check_result, "matches", []):
                    # Filtrar reglas deshabilitadas (por si el servidor no las filtró)
                    if match.rule_id in self._disabled_rules:
                        continue

                    word = text[match.offset : match.offset + match.length]
                    # Limpiar newlines/whitespace del word
                    word_clean = word.replace("\n", " ").replace("\r", " ").strip()
                    error_type = self._map_category(match.rule_category)

                    vote = Vote(
                        voter_name=self.name,
                        is_error=True,
                        confidence=0.85,
                        suggestions=match.replacements[:5],
                        error_type=error_type,
                        raw_response={
                            "rule_id": match.rule_id,
                            "message": match.message,
                            "category": match.rule_category,
                        },
                    )
                    # Ignorar errores en whitespace/newlines
                    if word_clean:
                        results.append(
                            (word_clean, match.offset, match.offset + match.length, vote)
                        )

        except Exception as e:
            logger.debug(f"Error en LanguageTool: {e}")

        return results

    def _map_category(self, category: str) -> SpellingErrorType:
        """Mapear categoría de LanguageTool a tipo de error."""
        category_lower = category.lower()

        if "typo" in category_lower:
            return SpellingErrorType.TYPO
        elif "spell" in category_lower:
            return SpellingErrorType.MISSPELLING
        elif "accent" in category_lower or "tilde" in category_lower:
            return SpellingErrorType.ACCENT
        elif "case" in category_lower or "mayus" in category_lower:
            return SpellingErrorType.CASE
        else:
            return SpellingErrorType.MISSPELLING


class PatternVoter(BaseVoter):
    """Votante usando patrones regex para errores comunes en español.

    Además de patrones regex, aplica reglas lingüísticas deterministas:
    - Esdrújulas sin tilde (regla sin excepción en español)
    - Interrogativas sin tilde en contexto de pregunta
    - h omitida detectada por raíz (cubre todas las conjugaciones)
    """

    name = "patterns"
    weight = VOTER_WEIGHTS["patterns"]

    # ----------------------------------------------------------------
    # Esdrújulas: mapa sin_tilde → con_tilde.
    # Regla RAE: TODA esdrújula lleva tilde, sin excepción.
    # Generado desde raíces morfológicas comunes para cubrir familias
    # de palabras completas sin memorizar formas individuales.
    # ----------------------------------------------------------------
    @staticmethod
    def _build_esdrujula_map() -> dict[str, str]:
        m: dict[str, str] = {}

        def _add_ico(ustem: str, astem: str):
            for s in ("ico", "ica", "icos", "icas"):
                m[ustem + s] = astem + s

        def _add_ido(ustem: str, astem: str):
            for s in ("ido", "ida", "idos", "idas"):
                m[ustem + s] = astem + s

        def _add_oaos(u: str, a: str):
            for s in ("o", "a", "os", "as"):
                m[u + s] = a + s

        def _add_pair(u: str, a: str):
            m[u] = a

        # --- sufijo -ico/-ica (familias completas) ---
        for us, ac in [
            ("cientific", "científic"),
            ("fantastic", "fantástic"),
            ("romantic", "romántic"),
            ("dramatic", "dramátic"),
            ("tecnic", "técnic"),
            ("practic", "práctic"),
            ("logic", "lógic"),
            ("tipic", "típic"),
            ("unic", "únic"),
            ("artistic", "artístic"),
            ("economic", "económic"),
            ("politic", "polític"),
            ("electronic", "electrónic"),
            ("automatic", "automátic"),
            ("simpatic", "simpátic"),
            ("mecanic", "mecánic"),
            ("organic", "orgánic"),
            ("dinamic", "dinámic"),
            ("estatic", "estátic"),
            ("cosmic", "cósmic"),
            ("comic", "cómic"),
            ("tragic", "trágic"),
            ("magic", "mágic"),
            ("basic", "básic"),
            ("plastic", "plástic"),
            ("elastic", "elástic"),
            ("domestic", "doméstic"),
            ("ecologic", "ecológic"),
            ("biologic", "biológic"),
            ("psicologic", "psicológic"),
            ("ideologic", "ideológic"),
            ("geographic", "geográfic"),
            ("caotic", "caótic"),
            ("exotic", "exótic"),
            ("periodic", "periódic"),
            ("tematic", "temátic"),
            ("sistematic", "sistemátic"),
            ("matematic", "matemátic"),
            ("informatic", "informátic"),
            ("acustic", "acústic"),
            ("optic", "óptic"),
            ("energetic", "energétic"),
            ("genetic", "genétic"),
            ("astronomic", "astronómic"),
            ("filosofic", "filosófic"),
            ("fonetic", "fonétic"),
            ("erotic", "erótic"),
            ("narcotic", "narcótic"),
            ("esceptic", "escéptic"),
            ("antiseptic", "antiséptic"),
            ("diagnostic", "diagnóstic"),
            ("pronostic", "pronóstic"),
            ("estoic", "estóic"),
            # También incluye médico/público/clásico/histórico:
            # altísima frecuencia en narrativa como sustantivo/adjetivo
            ("medic", "médic"),
            ("public", "públic"),
            ("classic", "clásic"),
            ("historic", "históric"),
        ]:
            _add_ico(us, ac)

        # --- sufijo -ido/-ida (adjetivos) ---
        for us, ac in [
            ("rap", "ráp"),
            ("sol", "sól"),
            ("liqu", "líqu"),
            ("val", "vál"),
            ("ac", "ác"),
            ("tim", "tím"),
            ("humed", "húmed"),
            ("nit", "nít"),
            ("luc", "lúc"),
            ("pal", "pál"),
            ("cal", "cál"),
            ("rig", "ríg"),
            ("plac", "plác"),
            ("viv", "vív"),
            ("esplend", "esplénd"),
        ]:
            _add_ido(us, ac)

        # --- sufijo -ogo/-oga ---
        for us, ac in [
            ("dialog", "diálog"),
            ("catalog", "catálog"),
            ("epilog", "epílog"),
            ("prolog", "prólog"),
            ("monolog", "monólog"),
        ]:
            _add_oaos(us, ac)

        # --- individuales (sustantivos, adjetivos, adverbios) ---
        indiv = {
            # -ono
            "telefono": "teléfono",
            "telefonos": "teléfonos",
            "microfono": "micrófono",
            "microfonos": "micrófonos",
            # -odo
            "metodo": "método",
            "metodos": "métodos",
            # -eno
            "fenomeno": "fenómeno",
            "fenomenos": "fenómenos",
            # -aro/-ara
            "pajaro": "pájaro",
            "pajaros": "pájaros",
            "cantaro": "cántaro",
            "cantaros": "cántaros",
            "barbaro": "bárbaro",
            "barbara": "bárbara",
            "barbaros": "bárbaros",
            "barbaras": "bárbaras",
            # -ulo/-ula
            "articulo": "artículo",
            "articulos": "artículos",
            "capitulo": "capítulo",
            "capitulos": "capítulos",
            "modulo": "módulo",
            "modulos": "módulos",
            "formula": "fórmula",
            "formulas": "fórmulas",
            "capsula": "cápsula",
            "capsulas": "cápsulas",
            "espectaculo": "espectáculo",
            "espectaculos": "espectáculos",
            "titulo": "título",
            "titulos": "títulos",
            "estimulo": "estímulo",
            "estimulos": "estímulos",
            "calculo": "cálculo",
            "calculos": "cálculos",
            "vinculo": "vínculo",
            "vinculos": "vínculos",
            "obstaculo": "obstáculo",
            "obstaculos": "obstáculos",
            "circulo": "círculo",
            "circulos": "círculos",
            "musculo": "músculo",
            "musculos": "músculos",
            "vehiculo": "vehículo",
            "vehiculos": "vehículos",
            "angulo": "ángulo",
            "angulos": "ángulos",
            "triangulo": "triángulo",
            "triangulos": "triángulos",
            "pendulo": "péndulo",
            "pendulos": "péndulos",
            "ridiculo": "ridículo",
            "ridicula": "ridícula",
            # -ero/-era
            "numero": "número",
            "numeros": "números",
            "genero": "género",
            "generos": "géneros",
            "atmosfera": "atmósfera",
            "atmosferas": "atmósferas",
            # -ara
            "lampara": "lámpara",
            "lamparas": "lámparas",
            "camara": "cámara",
            "camaras": "cámaras",
            # -ima/-imo
            "lagrima": "lágrima",
            "lagrimas": "lágrimas",
            "maximo": "máximo",
            "maxima": "máxima",
            "minimo": "mínimo",
            "minima": "mínima",
            "ultimo": "último",
            "ultima": "última",
            "ultimos": "últimos",
            "ultimas": "últimas",
            "optimo": "óptimo",
            "optima": "óptima",
            "pesimo": "pésimo",
            "pesima": "pésima",
            "proximo": "próximo",
            "proxima": "próxima",
            "intimo": "íntimo",
            "intima": "íntima",
            "legitimo": "legítimo",
            "legitima": "legítima",
            "victima": "víctima",
            "victimas": "víctimas",
            # -ina/-ino
            "maquina": "máquina",
            "maquinas": "máquinas",
            "pagina": "página",
            "paginas": "páginas",
            "fabrica": "fábrica",
            "fabricas": "fábricas",
            "musica": "música",
            "musicas": "músicas",
            # -ofo
            "filosofo": "filósofo",
            "filosofa": "filósofa",
            # -ipe
            "principe": "príncipe",
            "principes": "príncipes",
            # -aba
            "silaba": "sílaba",
            "silabas": "sílabas",
            # -igo
            "vertigo": "vértigo",
            # -ato
            "sabado": "sábado",
            "sabados": "sábados",
            # -isis/-esis
            "analisis": "análisis",
            "sintesis": "síntesis",
            "hipotesis": "hipótesis",
            "parentesis": "paréntesis",
            "genesis": "génesis",
            # -ito/-ita
            "parasito": "parásito",
            "parasitos": "parásitos",
            "proposito": "propósito",
            "propositos": "propósitos",
            "ejercito": "ejército",
            "ejercitos": "ejércitos",
            "credito": "crédito",
            "creditos": "créditos",
            "deposito": "depósito",
            "depositos": "depósitos",
            "transito": "tránsito",
            "habito": "hábito",
            "habitos": "hábitos",
            "ambito": "ámbito",
            "exito": "éxito",
            "exitos": "éxitos",
            "limite": "límite",
            "limites": "límites",
            "espiritu": "espíritu",
            "espiritus": "espíritus",
            # -oe
            "heroe": "héroe",
            "heroes": "héroes",
            # adverbios
            "rapidamente": "rápidamente",
            "ultimamente": "últimamente",
        }
        m.update(indiv)
        return m

    _ESDRUJULA_MAP: dict[str, str] = {}  # Populated in __init__

    # ----------------------------------------------------------------
    # Interrogativas: sin tilde → con tilde (en contexto de pregunta).
    # Regla RAE: pronombres/adverbios interrogativos siempre llevan
    # tilde en preguntas directas e indirectas.
    # ----------------------------------------------------------------
    _INTERROGATIVE_MAP: dict[str, str] = {
        "donde": "dónde",
        "como": "cómo",
        "cuando": "cuándo",
        "quien": "quién",
        "quienes": "quiénes",
        "que": "qué",
        "cual": "cuál",
        "cuales": "cuáles",
        "cuanto": "cuánto",
        "cuanta": "cuánta",
        "cuantos": "cuántos",
        "cuantas": "cuántas",
    }

    # ----------------------------------------------------------------
    # h omitida: raíces comunes que empiezan con h-.
    # Regla: si quitar la h produce un token reconocible, es error.
    # Cubre TODAS las conjugaciones/derivaciones de cada raíz.
    # ----------------------------------------------------------------
    _H_STEMS: dict[str, str] = {
        # raíz_sin_h → raíz_con_h (mínimo 3 chars para evitar FP)
        "abit": "habit",  # habitar, habitación, habitaba, habitante...
        "abitat": "habitat",
        "abl": "habl",  # hablar, hablaba, hablando...
        "onest": "honest",  # honesto, honestidad...
        "onor": "honor",  # honor, honorable...
        "onra": "honra",  # honra, honrado...
        "ombr": "hombr",  # hombre, hombros...
        "umild": "humild",  # humilde, humildad...
        "umed": "humed",  # húmedo, humedad...
        "uman": "human",  # humano, humanidad...
        "umor": "humor",  # humor, humorístico...
        "ospit": "hospit",  # hospital, hospitalario...
        "ostil": "hostil",  # hostil, hostilidad...
        "orribl": "horribl",  # horrible
        "orror": "horror",  # horror, horroroso...
        "ermanos": "hermanos",  # (ext. de patrón existente a plurales)
        "ermanas": "hermanas",
        "ijos": "hijos",
        "ijas": "hijas",
        "ermos": "hermos",  # hermoso, hermosura...
        "arin": "harin",  # harina
        "erramienta": "herramienta",
        "ielo": "hielo",
        "ierb": "hierb",
        "ierr": "hierr",
        "uelg": "huelg",  # huelga
        "uell": "huell",  # huella
        "uert": "huert",  # huerto, huerta
        "ues": "hues",  # hueso, huésped
    }

    # Patrones de errores comunes en español
    ERROR_PATTERNS = [
        # Confusión b/v
        (r"\b(estava|estavan|estuve|estubo)\b", "b_v", ["estaba", "estaban", "estuve", "estuvo"]),
        (r"\b(iva|ivan|ivas)\b", "b_v", ["iba", "iban", "ibas"]),
        (r"\b(haver|aver|habia|havia)\b", "b_v", ["haber", "a ver", "había", "había"]),
        (r"\b(tubo|tubieron|tubiste)\b", "b_v", ["tuvo", "tuvieron", "tuviste"]),
        (r"\b(boi|bamos|bais)\b", "b_v", ["voy", "vamos", "vais"]),
        (r"\b(bolver|bolber|bolvio)\b", "b_v", ["volver", "volver", "volvió"]),
        (r"\b(obserbar|obserbo)\b", "b_v", ["observar", "observo"]),
        (r"\b(recivir|recivi|recivio)\b", "b_v", ["recibir", "recibí", "recibió"]),
        (r"\b(escrivir|escrivio|escriví)\b", "b_v", ["escribir", "escribió", "escribí"]),
        (r"\b(berdad|berdadero)\b", "b_v", ["verdad", "verdadero"]),
        (r"\b(berduras|berde)\b", "b_v", ["verduras", "verde"]),
        (r"\b(bolo|boló)\b", "b_v", ["voló"]),  # "Un pájaro bolo" -> "voló"
        (r"\b(abraso|abrasos)\b", "b_v", ["abrazo", "abrazos"]),  # s/z confusion too
        (r"\b(nuebo|nueba|nuebos|nuebas)\b", "b_v", ["nuevo", "nueva", "nuevos", "nuevas"]),
        (r"\b(avuela|avuelo|avuelos|avuelas)\b", "b_v", ["abuela", "abuelo", "abuelos", "abuelas"]),
        (r"\b(todabia)\b", "b_v", ["todavía"]),
        (
            r"\b(lebanto|lebanta|lebantar|lebanvarse|levanvarse)\b",
            "b_v",
            ["levantó", "levanta", "levantar", "levantarse", "levantarse"],
        ),
        (r"\b(Havian|havian|Havia|havias)\b", "b_v", ["Habían", "habían", "Había", "habías"]),
        # Errores con h
        (r"\b(aver|aya|abia|abía|abian)\b", "h", ["haber", "haya", "había", "había", "habían"]),
        (
            r"\b(acia|asta|ola|ora|ombre|uevo)\b",
            "h",
            ["hacia", "hasta", "hola", "hora", "hombre", "huevo"],
        ),
        (r"\b(ermano|ermana|ijo|ija)\b", "h", ["hermano", "hermana", "hijo", "hija"]),
        (r"\b(abitacion|abitante|abitar)\b", "h", ["habitación", "habitante", "habitar"]),
        (r"\b(acer|aciendo|echo|emos)\b", "h", ["hacer", "haciendo", "hecho", "hemos"]),
        (r"\b(ubo|ubiera|ubieron)\b", "h", ["hubo", "hubiera", "hubieron"]),
        (r"\b(ablaban|ablaba|ablar|ablo)\b", "h", ["hablaban", "hablaba", "hablar", "habló"]),
        (r"\b(Abian|abian|Abia|abia)\b", "h", ["Habían", "habían", "Había", "había"]),
        # Verbos auxiliares con h omitida (contexto: "a ido" = "ha ido", "e estado" = "he estado")
        # Estos requieren contexto, pero los patrones pueden detectarlos en frases comunes
        (r"\ba\s+ido\b", "h", ["ha ido"]),
        (r"\be\s+estado\b", "h", ["he estado"]),
        (r"\ba\s+sido\b", "h", ["ha sido"]),
        (r"\ba\s+hecho\b", "h", ["ha hecho"]),
        (r"\be\s+ido\b", "h", ["he ido"]),
        # Confusión g/j (ante e, i)
        (
            r"\b(recojer|recojio|recojieron|recojí)\b",
            "g_j",
            ["recoger", "recogió", "recogieron", "recogí"],
        ),
        (r"\b(exijente|exijir|exijencia)\b", "g_j", ["exigente", "exigir", "exigencia"]),
        (r"\b(dirijer|dirijir|dirijio)\b", "g_j", ["dirigir", "dirigir", "dirigió"]),
        (r"\b(elejir|elejí|elejido)\b", "g_j", ["elegir", "elegí", "elegido"]),
        (r"\b(protejir|protejido|proteje)\b", "g_j", ["proteger", "protegido", "protege"]),
        (r"\b(correjir|correjido|corrije)\b", "g_j", ["corregir", "corregido", "corrige"]),
        # Confusión ll/y
        (r"\b(caye|cayes|cayendo)\b", "ll_y", ["calle", "calles", "callendo"]),
        (r"\b(poyo|poya)\b", "ll_y", ["pollo", "polla"]),
        (r"\b(vaya|baya|balla)\b", "ll_y", ["vaya", "vaya", "valla"]),
        (r"\b(oio|oió)\b", "ll_y", ["oyó", "oyó"]),
        # Redundancias y pleonasmos
        (r"\b(subir\s+arriba|bajar\s+abajo|salir\s+afuera|entrar\s+adentro)\b", "redundancy", []),
        (r"\b(mas\s+mejor|mas\s+peor|mas\s+mayor|mas\s+menor)\b", "redundancy", []),
        (r"\b(volver\s+a\s+regresar)\b", "redundancy", ["volver", "regresar"]),
        # ============================================================================
        # NOTA: Detección semántica de "riegos vs riesgos" ahora se hace en
        # semantic_checker.py con análisis contextual más robusto
        # ============================================================================
        # ============================================================================
        # FASE 2 - Medio Plazo (Panel de Expertos 2026-02)
        # ============================================================================
        # Repetición de palabras no funcionales (casa casa, libro libro, etc.)
        # Patrón: palabra de 4+ letras repetida inmediatamente
        (r"\b([a-záéíóúüñ]{4,})\s+\1\b", "repetition", []),
        # Dequeísmo: "de que" innecesario con verbos de pensamiento
        (
            r"\b(pienso|creo|opino|considero|parece|supongo|imagino|entiendo)\s+de\s+que\b",
            "dequeismo",
            [],
        ),
        # Queísmo: falta "de" con verbos pronominales
        (
            r"\b(me\s+acuerdo|te\s+acuerdas|se\s+acuerda|me\s+olvid[oóaé]|te\s+alegras?|se\s+alegr[aóaé])\s+que\b",
            "queismo",
            ["de que"],
        ),
        # Números 1-10 en cifras (solo en contexto narrativo, no técnico)
        # Este patrón es básico, idealmente requiere análisis de contexto
        (
            r"\b([1-9])\s+(personas?|niños?|hombres?|mujeres?|amigos?|hijos?|días?|años?|veces)\b",
            "style",
            [],
        ),
        # Gerundios excesivos: 3+ gerundios en ventana de 30 palabras
        # Patrón: detecta cadenas de gerundios
        # NOTA: Este patrón es simplificado. La implementación completa requeriría
        # análisis morfológico con spaCy para contar gerundios en ventana deslizante
        (r"(\w+ndo)\s+\S+\s+\S+\s+(\w+ndo)\s+\S+\s+\S+\s+(\w+ndo)", "style", []),
        # Palabras comúnmente mal escritas
        (r"\b(atravez|atraves)\b", "other", ["a través"]),
        (r"\b(enserio|encerio)\b", "other", ["en serio"]),
        (r"\b(asique|hací que)\b", "other", ["así que"]),
        (r"\b(alomejor|alamejor)\b", "other", ["a lo mejor"]),
        (r"\b(sobretodo)\b", "other", ["sobre todo"]),
        (r"\b(osea)\b", "other", ["o sea"]),
        (r"\b(porque|por que|porqué|por qué)\b", "accent", []),  # Requiere contexto
        (r"\b(sino|si no)\b", "other", []),  # Requiere contexto
        (r"\b(cuidad)\b", "other", ["ciudad"]),  # Omisión de letras
        (r"\b(siguente|sigiente)\b", "other", ["siguiente"]),  # Omisión de u
        # Acentos faltantes comunes (palabras agudas terminadas en vocal/n/s)
        (r"\b(dia|dias)\b", "accent", ["día", "días"]),
        (r"\b(tambien|ademas|quiza|quizas)\b", "accent", ["también", "además", "quizá", "quizás"]),
        (r"\b(asi|ahi|aqui|alli)\b", "accent", ["así", "ahí", "aquí", "allí"]),
        (r"\b(cafe|mama|papa|sofa)\b", "accent", ["café", "mamá", "papá", "sofá"]),
        # Condicional "sería" (común confusión con "seria" = grave)
        # "seria interesante" casi siempre es "sería interesante"
        (r"\b(seria)\b", "accent", ["sería"]),  # Requiere contexto pero alta probabilidad
        # Nombres propios comunes que claramente necesitan tilde
        # (excluimos Jose/Maria que pueden escribirse sin tilde en España)
        (
            r"\b(Lucia|Andres|Adrian|Ines|Ramon|Tomas|Simon|Ivan|Nicolas|Sebastian|Martin|Raul)\b",
            "accent",
            [
                "Lucía",
                "Andrés",
                "Adrián",
                "Inés",
                "Ramón",
                "Tomás",
                "Simón",
                "Iván",
                "Nicolás",
                "Sebastián",
                "Martín",
                "Raúl",
            ],
        ),
        # Verbos en pretérito perfecto simple (muy comunes)
        (
            r"\b(pregunto|respondio|penso|comenzo|termino|llego|paso|entro|salio|miro|hablo)\b",
            "accent",
            [
                "preguntó",
                "respondió",
                "pensó",
                "comenzó",
                "terminó",
                "llegó",
                "pasó",
                "entró",
                "salió",
                "miró",
                "habló",
            ],
        ),
        (
            r"\b(acerco|alejo|sento|levanto|cayo|oyo|sintio|decidio|siguio|subio|bajo)\b",
            "accent",
            [
                "acercó",
                "alejó",
                "sentó",
                "levantó",
                "cayó",
                "oyó",
                "sintió",
                "decidió",
                "siguió",
                "subió",
                "bajó",
            ],
        ),
        (r"\b(reian|reia|reias)\b", "accent", ["reían", "reía", "reías"]),
        (r"\b(sabia|sabian|sabias)\b", "accent", ["sabía", "sabían", "sabías"]),
        # Sustantivos comunes sin tilde
        (
            r"\b(jardin|arbol|arboles|pajaro|pajaros|sabado|domingo)\b",
            "accent",
            ["jardín", "árbol", "árboles", "pájaro", "pájaros", "sábado", "domingo"],
        ),
        (
            r"\b(poesia|filosofia|fantasia|energia|melancolia|alegria)\b",
            "accent",
            ["poesía", "filosofía", "fantasía", "energía", "melancolía", "alegría"],
        ),
        (
            r"\b(publico|clasico|historico|fantastico|romantico|dramatico)\b",
            "accent",
            ["público", "clásico", "histórico", "fantástico", "romántico", "dramático"],
        ),
        # Números cardinales sin tilde
        (
            r"\b(veintidos|veintitres|veintiseis)\b",
            "accent",
            ["veintidós", "veintitrés", "veintiséis"],
        ),
        # Palabras interrogativas/exclamativas sin tilde
        (r"\b(Que)\b", "accent", ["Qué"]),  # Al inicio de oración interrogativa
    ]

    def __init__(self):
        super().__init__()
        import re

        self._compiled_patterns = []
        for pattern, error_type, suggestions in self.ERROR_PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._compiled_patterns.append((compiled, error_type, suggestions))
            except re.error as e:
                logger.warning(f"Patrón inválido '{pattern}': {e}")

        # Construir mapa de esdrújulas (una sola vez)
        if not PatternVoter._ESDRUJULA_MAP:
            PatternVoter._ESDRUJULA_MAP = PatternVoter._build_esdrujula_map()

        self._available = len(self._compiled_patterns) > 0 or bool(PatternVoter._ESDRUJULA_MAP)
        if self._available:
            logger.info(
                f"PatternVoter inicializado con {len(self._compiled_patterns)} patrones "
                f"+ {len(PatternVoter._ESDRUJULA_MAP)} esdrújulas "
                f"+ {len(self._INTERROGATIVE_MAP)} interrogativas "
                f"+ {len(self._H_STEMS)} raíces h-"
            )

    def check_word(self, word: str, context: str = "") -> Vote | None:
        if not self._available:
            return None

        word_lower = word.lower()

        # Fase 1: Patrones regex explícitos (máxima confianza)
        for compiled, error_type, suggestions in self._compiled_patterns:
            if compiled.fullmatch(word_lower):
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.90,  # Alta confianza en patrones conocidos
                    suggestions=suggestions if suggestions else [],
                    error_type=self._map_error_type(error_type),
                )

        # Fase 2: Regla de esdrújulas (regla determinista RAE)
        esdrujula_result = self._check_esdrujula(word_lower)
        if esdrujula_result:
            return esdrujula_result

        # Fase 3: Interrogativas sin tilde en contexto de pregunta
        interrogative_result = self._check_interrogative(word_lower, context)
        if interrogative_result:
            return interrogative_result

        # Fase 4: h omitida por raíz (cubre conjugaciones)
        h_result = self._check_h_stem(word_lower)
        if h_result:
            return h_result

        return Vote(
            voter_name=self.name,
            is_error=False,
            confidence=0.5,  # Baja confianza si no coincide con patrones
        )

    def _check_esdrujula(self, word_lower: str) -> Vote | None:
        """Detecta esdrújulas sin tilde usando mapa morfológico."""
        # Solo palabras sin tilde
        if any(c in word_lower for c in "áéíóú"):
            return None
        suggestion = self._ESDRUJULA_MAP.get(word_lower)
        if suggestion:
            return Vote(
                voter_name=self.name,
                is_error=True,
                confidence=0.88,  # Alta confianza: regla RAE sin excepción
                suggestions=[suggestion],
                error_type=SpellingErrorType.ACCENT,
            )
        return None

    def _check_interrogative(self, word_lower: str, context: str) -> Vote | None:
        """Detecta interrogativas sin tilde en contexto de pregunta directa."""
        if not context:
            return None
        suggestion = self._INTERROGATIVE_MAP.get(word_lower)
        if not suggestion:
            return None
        # Verificar contexto de pregunta: ¿...? o ...?
        if "?" in context or "¿" in context:
            return Vote(
                voter_name=self.name,
                is_error=True,
                confidence=0.85,
                suggestions=[suggestion],
                error_type=SpellingErrorType.ACCENT,
            )
        return None

    def _check_h_stem(self, word_lower: str) -> Vote | None:
        """Detecta h omitida usando raíces morfológicas."""
        # Solo palabras que empiecen con vocal (candidatas a h omitida)
        if not word_lower or word_lower[0] not in "aeiou":
            return None
        for stem_no_h, stem_h in self._H_STEMS.items():
            if word_lower.startswith(stem_no_h):
                # Reconstruir la palabra con h
                corrected = stem_h + word_lower[len(stem_no_h) :]
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.85,
                    suggestions=[corrected],
                    error_type=SpellingErrorType.MISSPELLING,
                )
        return None

    def _map_error_type(self, error_type: str) -> SpellingErrorType:
        mapping = {
            "b_v": SpellingErrorType.MISSPELLING,
            "h": SpellingErrorType.MISSPELLING,
            "ll_y": SpellingErrorType.MISSPELLING,
            "accent": SpellingErrorType.ACCENT,
            "redundancy": SpellingErrorType.MISSPELLING,
            "other": SpellingErrorType.MISSPELLING,
        }
        return mapping.get(error_type, SpellingErrorType.MISSPELLING)


class BETOVoter(BaseVoter):
    """
    Votante usando BETO (BERT español) para detección de errores.

    Usa modelos BERT/RoBERTa españoles con fill-mask para detectar
    palabras que no encajan en el contexto.

    NOTA: El modelo NER (mrm8488) tiene P=26.6% - muy ruidoso.
    Preferimos el modelo base BETO que está mejor para MLM.
    """

    name = "beto"
    weight = VOTER_WEIGHTS["beto"]

    # Modelos disponibles por orden de preferencia (MLM > NER para ortografía)
    MODELS = [
        "dccuchile/bert-base-spanish-wwm-cased",  # BETO base - mejor para MLM
        "PlanTL-GOB-ES/roberta-base-bne",  # RoBERTa español BNE
        "bertin-project/bertin-roberta-base-spanish",  # SpanBERTa
        "mrm8488/bert-spanish-cased-finetuned-ner",  # NER - PEOR para ortografía
    ]

    def __init__(self, model_name: str | None = None):
        super().__init__()
        self._model = None
        self._tokenizer = None
        self._fill_mask = None

        try:
            import torch
            from transformers import AutoModelForMaskedLM, AutoTokenizer, pipeline

            # Seleccionar modelo
            model_to_use = model_name or self._find_available_model()

            if model_to_use:
                logger.info(f"Cargando modelo BETO: {model_to_use}...")

                # Usar fill-mask pipeline para detectar palabras que no encajan
                self._fill_mask = pipeline(
                    "fill-mask",
                    model=model_to_use,
                    tokenizer=model_to_use,
                    device=-1,  # CPU por defecto, cambiar a 0 para GPU
                    top_k=5,
                )
                self._model_name = model_to_use
                self._available = True
                logger.info(f"BETOVoter inicializado con {model_to_use}")
            else:
                self._init_error = "No se encontró modelo BETO/BERT español"
                logger.warning(self._init_error)

        except ImportError:
            self._init_error = "transformers no instalado (pip install transformers torch)"
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Error inicializando BETO: {e}"
            logger.warning(self._init_error)

    def _find_available_model(self) -> str | None:
        """Buscar modelo disponible (en cache o descargable)."""
        try:
            from pathlib import Path

            # Primero buscar en cache local
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

            for model_name in self.MODELS:
                # Verificar si está en cache
                model_cache = cache_dir / f"models--{model_name.replace('/', '--')}"
                if model_cache.exists():
                    return model_name

            # Si no hay ninguno en cache, usar el más ligero
            # Solo si hay conexión a internet
            return self.MODELS[0]  # Intentar descargar el primero

        except Exception:
            return None

    def check_word(self, word: str, context: str = "") -> Vote | None:
        """
        Verificar si una palabra encaja en el contexto usando BETO.

        Estrategia: Reemplazar la palabra con [MASK] y ver si el modelo
        predice la misma palabra. Si no, probablemente hay un error.
        """
        if not self._available or not context:
            return None

        try:
            # Crear versión con máscara
            word_lower = word.lower()
            context_lower = context.lower()

            # Encontrar posición de la palabra en el contexto
            import re

            pattern = re.compile(r"\b" + re.escape(word_lower) + r"\b", re.IGNORECASE)
            match = pattern.search(context_lower)

            if not match:
                return None

            # Reemplazar palabra con [MASK]
            masked_context = context[: match.start()] + "[MASK]" + context[match.end() :]

            # Obtener predicciones
            if self._fill_mask is None:
                return None
            predictions = self._fill_mask(masked_context)

            # Verificar si la palabra original está entre las predicciones
            predicted_words = [p["token_str"].lower().strip() for p in predictions]
            predicted_scores = {p["token_str"].lower().strip(): p["score"] for p in predictions}

            if word_lower in predicted_words:
                # La palabra encaja bien en el contexto
                score = predicted_scores.get(word_lower, 0.5)
                return Vote(
                    voter_name=self.name,
                    is_error=False,
                    confidence=min(0.95, score + 0.3),  # Alta confianza si el modelo la predice
                )
            else:
                # La palabra no encaja - posible error
                predictions[0]["token_str"] if predictions else ""
                return Vote(
                    voter_name=self.name,
                    is_error=True,
                    confidence=0.7,
                    suggestions=[p["token_str"] for p in predictions[:3]],
                    error_type=SpellingErrorType.MISSPELLING,
                )

        except Exception as e:
            logger.debug(f"Error en BETO para '{word}': {e}")
            return None


# =============================================================================
# Características de precisión/recall de cada votante (medidas 2026-01-19)
# =============================================================================

VOTER_CHARACTERISTICS = {
    # Votante: (precision, recall, fortaleza)
    # fortaleza: "precision" = confiar cuando dice ERROR (alta precision)
    #            "recall" = confiar cuando dice NO ERROR (alto recall)
    #            "balanced" = confianza equilibrada
    #
    # Medido con prueba_ortografia.txt (51 errores gold):
    "patterns": (0.873, 0.697, "precision"),  # P=87.3%, R=69.7% - MUY preciso
    "symspell": (0.742, 0.465, "precision"),  # P=74.2%, R=46.5% - Preciso
    "hunspell": (0.635, 0.545, "balanced"),  # P=63.5%, R=54.5% - Equilibrado
    "languagetool": (0.622, 0.798, "recall"),  # P=62.2%, R=79.8% - Alto recall
    "pyspellchecker": (0.400, 0.626, "recall"),  # P=40.0%, R=62.6% - Recall medio, ruidoso
    # BETO base (dccuchile/bert-base-spanish-wwm-cased) - mejor que NER model
    "beto": (0.453, 0.857, "recall"),  # P=45.3%, R=85.7% - BETO base, mejor que NER
}


# =============================================================================
# Agregador de votos inteligente
# =============================================================================


class VoteAggregator:
    """
    Agrega votos de múltiples correctores usando estrategia inteligente.

    Estrategia:
    1. Votantes de alta precisión (patterns, languagetool, beto):
       - Si dicen ERROR → probablemente ES error (confiar)
       - Si dicen NO ERROR → no es conclusivo (pueden tener bajo recall)

    2. Votantes de alto recall (pyspellchecker):
       - Si dicen NO ERROR → probablemente NO es error (confiar)
       - Si dicen ERROR → puede ser falso positivo (verificar con otros)

    3. Votantes equilibrados (symspell, hunspell):
       - Confianza proporcional a su peso
    """

    def __init__(
        self,
        min_confidence_for_consensus: float = MIN_CONFIDENCE_FOR_CONSENSUS,
        min_voters_for_consensus: int = MIN_VOTERS_FOR_CONSENSUS,
    ):
        self.min_confidence = min_confidence_for_consensus
        self.min_voters = min_voters_for_consensus

    def aggregate(self, voting_result: VotingResult) -> VotingResult:
        """Agregar votos usando estrategia inteligente."""

        if not voting_result.votes:
            voting_result.is_error = False
            voting_result.aggregated_confidence = 0.0
            voting_result.needs_llm_arbitration = False
            return voting_result

        # Fase 1: Clasificar votos por tipo de votante
        precision_voters_error = []  # Alta precisión que dicen ERROR
        precision_voters_ok = []  # Alta precisión que dicen OK
        recall_voters_error = []  # Alto recall que dicen ERROR
        recall_voters_ok = []  # Alto recall que dicen OK
        balanced_votes = []  # Votantes equilibrados

        for vote in voting_result.votes:
            chars = VOTER_CHARACTERISTICS.get(vote.voter_name, (0.5, 0.5, "balanced"))
            precision, recall, strength = chars

            if strength == "precision":
                if vote.is_error:
                    precision_voters_error.append((vote, precision))
                else:
                    precision_voters_ok.append((vote, recall))
            elif strength == "recall":
                if vote.is_error:
                    recall_voters_error.append((vote, precision))
                else:
                    recall_voters_ok.append((vote, recall))
            else:  # balanced
                balanced_votes.append((vote, (precision + recall) / 2))

        # Fase 2: Aplicar reglas de decisión inteligentes

        # Regla 0: LanguageTool tiene CONTEXTO - confiar para palabras cortas
        # Esto es crítico para errores como "a ido" -> "ha ido", "El estaba" -> "Él estaba"
        # PERO solo para palabras muy cortas donde el contexto es necesario
        lt_votes = [v for v in voting_result.votes if v.voter_name == "languagetool"]
        if lt_votes and lt_votes[0].is_error:
            lt_vote = lt_votes[0]
            word = voting_result.word.lower()

            # Para palabras muy cortas (1-2 chars), confiar en LanguageTool
            # porque necesitan contexto (a/ha, e/he, el/él)
            is_short_contextual = len(word) <= 2 and word in ["a", "e", "el"]

            if is_short_contextual and lt_vote.confidence >= 0.8:
                voting_result.is_error = True
                voting_result.aggregated_confidence = lt_vote.confidence
                voting_result.final_suggestions = lt_vote.suggestions
                voting_result.needs_llm_arbitration = False
                return voting_result

        # Regla 1: Si un votante de alta precisión dice ERROR con alta confianza → ES ERROR
        high_precision_errors = [
            (v, p) for v, p in precision_voters_error if v.confidence >= 0.8 and p >= 0.75
        ]
        if high_precision_errors:
            # Alta confianza en que es error
            best_vote, best_precision = max(
                high_precision_errors, key=lambda x: x[0].confidence * x[1]
            )
            voting_result.is_error = True
            voting_result.aggregated_confidence = min(
                0.95, best_vote.confidence * best_precision * 1.2
            )
            voting_result.needs_llm_arbitration = False

            # Agregar sugerencias
            voting_result.final_suggestions = self._aggregate_suggestions(voting_result.votes)
            return voting_result

        # Regla 2: Si un votante de alto recall dice NO ERROR → probablemente NO es error
        high_recall_ok = [(v, r) for v, r in recall_voters_ok if v.confidence >= 0.7 and r >= 0.75]
        if high_recall_ok and not precision_voters_error:
            # Si alto recall dice OK y ningún preciso dice error → NO es error
            voting_result.is_error = False
            voting_result.aggregated_confidence = 0.75
            voting_result.needs_llm_arbitration = False
            return voting_result

        # Regla 3: Conflicto entre precisión y recall → votación ponderada
        error_score = 0.0
        ok_score = 0.0
        total_weight = 0.0

        for vote in voting_result.votes:
            chars = VOTER_CHARACTERISTICS.get(vote.voter_name, (0.5, 0.5, "balanced"))
            precision, recall, strength = chars
            base_weight = VOTER_WEIGHTS.get(vote.voter_name, 0.1)

            if vote.is_error:
                # Ponderar por precisión del votante (¿cuánto confiar en su ERROR?)
                effective_weight = base_weight * precision * vote.confidence
                error_score += effective_weight
            else:
                # Ponderar por recall del votante (¿cuánto confiar en su OK?)
                effective_weight = base_weight * recall * vote.confidence
                ok_score += effective_weight

            total_weight += base_weight

        # Normalizar
        if total_weight > 0:
            error_score /= total_weight
            ok_score /= total_weight

        # Decisión final con sesgo hacia precisión (evitar falsos positivos)
        # Requiere que error_score sea significativamente mayor para declarar error
        precision_bias = 0.15  # Sesgo hacia NO marcar error si hay duda
        voting_result.is_error = error_score > (ok_score + precision_bias)
        voting_result.aggregated_confidence = max(error_score, ok_score)

        # Agregar sugerencias
        voting_result.final_suggestions = self._aggregate_suggestions(voting_result.votes)

        # Determinar si necesita arbitraje LLM
        voting_result.needs_llm_arbitration = self._needs_arbitration(
            voting_result, error_score, ok_score
        )

        return voting_result

    def _aggregate_suggestions(self, votes: list[Vote]) -> list[str]:
        """Agregar sugerencias de todos los votantes."""
        from collections import Counter

        all_suggestions = []
        for vote in votes:
            if vote.is_error and vote.suggestions:
                # Ponderar sugerencias por precisión del votante
                chars = VOTER_CHARACTERISTICS.get(vote.voter_name, (0.5, 0.5, "balanced"))
                precision = chars[0]
                # Añadir múltiples veces según precisión
                times = max(1, int(precision * 3))
                all_suggestions.extend(vote.suggestions[:3] * times)

        suggestion_counts = Counter(all_suggestions)
        return [s for s, _ in suggestion_counts.most_common(5)]

    def _needs_arbitration(self, result: VotingResult, error_score: float, ok_score: float) -> bool:
        """Determinar si necesita consultar LLM."""

        # Pocos votantes → necesita LLM
        if result.voters_total < self.min_voters:
            return True

        # Baja confianza general → necesita LLM
        if result.aggregated_confidence < self.min_confidence:
            return True

        # Scores muy cercanos (decisión incierta) → necesita LLM
        if abs(error_score - ok_score) < 0.15:
            return True

        # Conflicto entre votantes de alta precisión y alto recall
        error_votes = [v for v in result.votes if v.is_error]
        ok_votes = [v for v in result.votes if not v.is_error]

        if error_votes and ok_votes:
            # Verificar si hay conflicto entre tipos de votantes
            error_has_precision = any(
                VOTER_CHARACTERISTICS.get(v.voter_name, (0.5, 0.5, "balanced"))[2] == "precision"
                for v in error_votes
            )
            ok_has_recall = any(
                VOTER_CHARACTERISTICS.get(v.voter_name, (0.5, 0.5, "balanced"))[2] == "recall"
                for v in ok_votes
            )

            # Conflicto real: precisión dice error, recall dice ok
            if error_has_precision and ok_has_recall:
                # Esto es esperado, no necesita LLM si la diferencia es clara
                return not abs(error_score - ok_score) >= 0.25

        return False


# =============================================================================
# Árbitro LLM
# =============================================================================


class LLMArbitrator:
    """Árbitro LLM para casos dudosos."""

    _available: bool

    def __init__(self):
        self._available = False
        try:
            from ...llm.client import get_llm_client

            self._client = get_llm_client()
            self._available = True
        except Exception as e:
            logger.warning(f"LLM no disponible para arbitraje: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def arbitrate(self, word: str, sentence: str, votes: list[Vote]) -> tuple[bool, float, str]:
        """
        Arbitrar si una palabra es error ortográfico.

        Returns:
            (is_error, confidence, explanation)
        """
        if not self._available:
            return (False, 0.0, "LLM no disponible")

        try:
            from narrative_assistant.llm.sanitization import sanitize_for_prompt

            # Preparar contexto de votos para el LLM
            vote_summary = self._summarize_votes(votes)

            # Sanitizar texto del manuscrito antes de enviarlo al LLM (A-10)
            safe_word = sanitize_for_prompt(word, max_length=100)
            safe_sentence = sanitize_for_prompt(sentence, max_length=500)

            prompt = f"""Eres un experto en ortografía española. Analiza si la palabra marcada es un error ortográfico.

PALABRA: "{safe_word}"
CONTEXTO: "{safe_sentence}"

OPINIONES DE CORRECTORES:
{vote_summary}

Responde en formato JSON:
{{
    "es_error": true/false,
    "confianza": 0.0-1.0,
    "explicacion": "razón breve",
    "correccion": "palabra correcta si es error, o null"
}}

Solo responde con el JSON, sin texto adicional."""

            response = self._client.complete(
                prompt=prompt,
                temperature=0.1,
                max_tokens=200,
            )

            # Parsear respuesta
            import json
            import re

            # Extraer JSON de la respuesta
            json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return (
                    result.get("es_error", False),
                    result.get("confianza", 0.5),
                    result.get("explicacion", ""),
                )

            return (False, 0.5, "No se pudo parsear respuesta LLM")

        except Exception as e:
            logger.warning(f"Error en arbitraje LLM: {e}")
            return (False, 0.0, f"Error: {e}")

    def _summarize_votes(self, votes: list[Vote]) -> str:
        """Resumir votos para el prompt."""
        lines = []
        for vote in votes:
            status = "DETECTA ERROR" if vote.is_error else "NO detecta error"
            suggestions = (
                f" (sugerencias: {', '.join(vote.suggestions[:3])})" if vote.suggestions else ""
            )
            lines.append(
                f"- {vote.voter_name}: {status} (confianza: {vote.confidence:.0%}){suggestions}"
            )
        return "\n".join(lines)


# =============================================================================
# Corrector principal con votación
# =============================================================================


class VotingSpellingChecker:
    """
    Corrector ortográfico multi-votante con arbitraje LLM.
    """

    def __init__(
        self,
        use_pyspellchecker: bool = True,
        use_hunspell: bool = True,
        use_symspell: bool = True,
        use_patterns: bool = True,
        use_beto: bool = False,  # Desactivado por defecto (requiere transformers)
        use_languagetool: bool = True,
        use_llm_arbitration: bool = True,
        min_confidence: float = MIN_CONFIDENCE_FOR_CONSENSUS,
    ):
        self._voters: list[BaseVoter] = []
        self._lt_voter: LanguageToolVoter | None = None
        self._aggregator = VoteAggregator(min_confidence_for_consensus=min_confidence)
        self._arbitrator: LLMArbitrator | None = None

        # Inicializar votantes por orden de prioridad/precisión

        # 1. Patrones regex (rápido, alta precisión en casos conocidos)
        if use_patterns:
            pattern_voter = PatternVoter()
            if pattern_voter.is_available:
                self._voters.append(pattern_voter)

        # 2. PySpellChecker (Pure Python, diccionario español)
        if use_pyspellchecker:
            pyspell_voter = PySpellCheckerVoter()
            if pyspell_voter.is_available:
                self._voters.append(pyspell_voter)

        # 3. Hunspell (diccionario profesional)
        if use_hunspell:
            chunspell_voter = ChunspellVoter()
            if chunspell_voter.is_available:
                self._voters.append(chunspell_voter)

        # 4. SymSpell (basado en frecuencia, muy rápido)
        if use_symspell:
            symspell_voter = SymSpellVoter()
            if symspell_voter.is_available:
                self._voters.append(symspell_voter)

        # 5. BETO (transformer español - más lento pero preciso)
        if use_beto:
            beto_voter = BETOVoter()
            if beto_voter.is_available:
                self._voters.append(beto_voter)

        # 6. LanguageTool (servidor Java, gramática + ortografía)
        if use_languagetool:
            self._lt_voter = LanguageToolVoter()
            if not self._lt_voter.is_available:
                self._lt_voter = None

        # 7. LLM arbitrator (solo para casos dudosos)
        if use_llm_arbitration:
            self._arbitrator = LLMArbitrator()

        # Calcular peso total disponible
        total_weight = sum(VOTER_WEIGHTS.get(v.name, 0.1) for v in self._voters)
        if self._lt_voter:
            total_weight += VOTER_WEIGHTS.get("languagetool", 0.25)

        logger.info(
            f"VotingSpellingChecker inicializado con {len(self._voters)} votantes "
            f"(peso total: {total_weight:.0%}) "
            f"+ LanguageTool={'sí' if self._lt_voter else 'no'} "
            f"+ LLM={'sí' if self._arbitrator and self._arbitrator.is_available else 'no'}"
        )

    @property
    def available_voters(self) -> list[str]:
        """Lista de votantes disponibles."""
        voters = [v.name for v in self._voters]
        if self._lt_voter:
            voters.append("languagetool")
        return voters

    def check(
        self,
        text: str,
        known_entities: list[str] | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> Result[SpellingReport]:
        """
        Verificar texto con sistema de votación.

        Args:
            text: Texto a verificar
            known_entities: Nombres propios conocidos (no marcar como error)
            progress_callback: Callback de progreso (0.0-1.0, mensaje)

        Returns:
            Result con SpellingReport
        """
        import re

        if not text or not text.strip():
            return Result.success(SpellingReport())

        report = SpellingReport()
        known_words = {w.lower() for w in (known_entities or [])}

        # Extraer palabras del texto (mínimo 2 caracteres, o 1 para errores conocidos)
        # Incluimos palabras de 1-2 chars solo si pueden ser errores de h omitida (a, e, el)
        word_pattern = re.compile(r"\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,})\b")
        short_word_pattern = re.compile(r"\b([aeAE])\b")  # "a" -> "ha", "e" -> "he"
        words_to_check: list[tuple[str, int, int, str]] = []

        # Añadir palabras cortas especiales (posibles errores de h)
        for match in short_word_pattern.finditer(text):
            word = match.group(1)
            start = match.start()
            end = match.end()
            sentence = self._extract_sentence(text, start)
            words_to_check.append((word, start, end, sentence))

        for match in word_pattern.finditer(text):
            word = match.group(1)
            start = match.start()
            end = match.end()

            # Ignorar palabras conocidas
            if word.lower() in known_words:
                continue

            # Extraer oración como contexto
            sentence = self._extract_sentence(text, start)
            words_to_check.append((word, start, end, sentence))

        total_words = len(words_to_check)

        if progress_callback:
            progress_callback(0.1, f"Verificando {total_words} palabras...")

        # Fase 1: Obtener votos de LanguageTool (procesa texto completo)
        lt_results: dict[int, Vote] = {}
        lt_raw_results: list[tuple[str, int, int, Vote]] = []  # word, start, end, vote
        if self._lt_voter:
            lt_checks = self._lt_voter.check_text(text)
            for word, start, end, vote in lt_checks:
                lt_results[start] = vote
                lt_raw_results.append((word, start, end, vote))

        # Fase 2: Procesar cada palabra con votantes individuales
        voting_results: list[VotingResult] = []
        words_positions = {start for _, start, _, _ in words_to_check}

        for i, (word, start, end, sentence) in enumerate(words_to_check):
            if progress_callback and i % 50 == 0:
                progress = 0.1 + (0.6 * i / total_words)
                progress_callback(progress, f"Procesando palabra {i + 1}/{total_words}...")

            result = VotingResult(
                word=word,
                start_char=start,
                end_char=end,
                sentence=sentence,
            )

            # Recoger votos de cada votante
            for voter in self._voters:
                voter_vote = voter.check_word(word, sentence)
                if voter_vote:
                    result.votes.append(voter_vote)

            # Añadir voto de LanguageTool si existe
            if start in lt_results:
                result.votes.append(lt_results[start])

            # Agregar votos
            result = self._aggregator.aggregate(result)

            if result.is_error or result.needs_llm_arbitration:
                voting_results.append(result)

        # Fase 2b: Añadir errores de LanguageTool que no coinciden con palabras extraídas
        # (palabras muy cortas como "a", "e", "El" que no pasaron el filtro de longitud)
        for lt_word, lt_start, lt_end, lt_vote in lt_raw_results:
            if lt_start not in words_positions and lt_word.strip():
                # Este error de LT no fue procesado - añadirlo directamente
                sentence = self._extract_sentence(text, lt_start)
                result = VotingResult(
                    word=lt_word,
                    start_char=lt_start,
                    end_char=lt_end,
                    sentence=sentence,
                    votes=[lt_vote],
                )
                # LanguageTool tiene alta confianza en errores que detecta solo
                result.is_error = True
                result.aggregated_confidence = lt_vote.confidence
                result.final_suggestions = lt_vote.suggestions
                voting_results.append(result)

        if progress_callback:
            progress_callback(0.7, "Agregando resultados...")

        # Fase 3: Arbitraje LLM para casos dudosos
        if self._arbitrator and self._arbitrator.is_available:
            needs_arbitration = [r for r in voting_results if r.needs_llm_arbitration]

            if needs_arbitration:
                if progress_callback:
                    progress_callback(
                        0.75, f"Consultando LLM para {len(needs_arbitration)} casos dudosos..."
                    )

                for result in needs_arbitration:
                    is_error, confidence, explanation = self._arbitrator.arbitrate(
                        result.word,
                        result.sentence,
                        result.votes,
                    )
                    result.llm_verdict = is_error
                    result.llm_confidence = confidence
                    result.llm_explanation = explanation

                    # Actualizar resultado final basado en LLM
                    if confidence > 0.6:
                        result.is_error = is_error
                        result.aggregated_confidence = confidence

        if progress_callback:
            progress_callback(0.9, "Generando reporte...")

        # Fase 4: Convertir a SpellingIssues
        for result in voting_results:
            if result.is_error:
                # Filtrar palabras que sean solo whitespace/newlines
                if not result.word.strip():
                    continue
                issue = SpellingIssue(
                    word=result.word,
                    start_char=result.start_char,
                    end_char=result.end_char,
                    sentence=result.sentence,
                    error_type=result.final_error_type,
                    severity=SpellingSeverity.ERROR
                    if result.aggregated_confidence > 0.7
                    else SpellingSeverity.WARNING,
                    suggestions=result.final_suggestions,
                    confidence=result.aggregated_confidence,
                    detection_method=DetectionMethod.DICTIONARY,
                    explanation=result.llm_explanation
                    or f"Detectado por {result.voters_detecting_error}/{result.voters_total} correctores",
                )
                report.add_issue(issue)

        # Estadísticas finales
        report.processed_chars = len(text)
        report.processed_words = total_words

        if progress_callback:
            progress_callback(1.0, f"Completado: {len(report.issues)} errores encontrados")

        return Result.success(report)

    def _extract_sentence(self, text: str, position: int) -> str:
        """Extraer la oración que contiene la posición dada."""
        start = position
        while start > 0 and text[start - 1] not in ".!?\n":
            start -= 1

        end = position
        while end < len(text) and text[end] not in ".!?\n":
            end += 1

        sentence = text[start : end + 1].strip()
        if len(sentence) > 200:
            word_start = position - start
            context_start = max(0, word_start - 80)
            context_end = min(len(sentence), word_start + 80)
            sentence = "..." + sentence[context_start:context_end] + "..."

        return sentence


# =============================================================================
# Singleton thread-safe
# =============================================================================

_lock = threading.Lock()
_instance: VotingSpellingChecker | None = None


def get_voting_spelling_checker(**kwargs) -> VotingSpellingChecker:
    """Obtener instancia singleton del corrector con votación."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = VotingSpellingChecker(**kwargs)

    return _instance


def reset_voting_spelling_checker() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None
