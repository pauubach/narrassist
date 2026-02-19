"""
Detector de variaciones regionales del español.

Detecta cuando se mezclan variantes regionales (español de España, México,
Argentina, etc.) en el mismo documento, lo cual puede ser inconsistente
a menos que sea intencional (diálogos de personajes de distintas regiones).

También sugiere alternativas según la variante regional configurada.
"""

import json
import logging
from pathlib import Path

from ..base import BaseDetector, CorrectionIssue
from ..config import RegionalConfig
from ..types import CorrectionCategory, RegionalIssueType

logger = logging.getLogger(__name__)


class RegionalDictionary:
    """
    Diccionario de términos regionales del español.

    Carga y gestiona diccionarios JSON con términos específicos
    de cada variante regional.
    """

    def __init__(self, dictionaries_path: Path | None = None):
        """
        Inicializa el diccionario regional.

        Args:
            dictionaries_path: Ruta a la carpeta de diccionarios.
                              Por defecto: ~/.narrative_assistant/dictionaries
        """
        if dictionaries_path is None:
            from pathlib import Path

            dictionaries_path = Path.home() / ".narrative_assistant" / "dictionaries"

        self.dictionaries_path = dictionaries_path
        self.dictionaries: dict[str, dict] = {}
        self._loaded = False

    def load(self, regions: list[str] | None = None) -> None:
        """
        Carga los diccionarios de las regiones especificadas.

        Args:
            regions: Lista de códigos de región (es_ES, es_MX, etc.)
                    Si None, carga todos los disponibles.
        """
        regional_path = self.dictionaries_path / "regional"

        if not regional_path.exists():
            logger.warning(f"Regional dictionaries path not found: {regional_path}")
            self._loaded = True
            return

        # Cargar diccionarios
        for json_file in regional_path.glob("*.json"):
            region_code = json_file.stem  # es_ES, es_MX, etc.

            if regions is not None and region_code not in regions:
                continue

            try:
                with open(json_file, encoding="utf-8") as f:
                    self.dictionaries[region_code] = json.load(f)
                logger.info(f"Loaded regional dictionary: {region_code}")
            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")

        self._loaded = True

    def get_term_info(self, term: str) -> dict[str, dict]:
        """
        Obtiene información sobre un término en todas las regiones.

        Args:
            term: Término a buscar

        Returns:
            Dict con {region: {info del término}} para cada región donde existe
        """
        if not self._loaded:
            self.load()

        result = {}
        term_lower = term.lower()

        for region, dictionary in self.dictionaries.items():
            terms = dictionary.get("terms", {})
            if term_lower in terms:
                result[region] = terms[term_lower]

        return result

    def get_regional_alternative(self, term: str, target_region: str) -> str | None:
        """
        Obtiene la alternativa de un término en la región objetivo.

        Args:
            term: Término a buscar
            target_region: Región objetivo (es_ES, es_MX, etc.)

        Returns:
            Término alternativo en la región objetivo, o None
        """
        term_info = self.get_term_info(term)

        if target_region in term_info:
            return term_info[target_region].get("preferred") or term

        # Buscar en otras regiones si hay un mapping
        for region, info in term_info.items():
            if region == target_region:
                continue
            # Ver si tiene equivalente para la región objetivo
            equivalents = info.get("equivalents", {})
            if target_region in equivalents:
                return equivalents[target_region]

        return None

    def is_regional_term(self, term: str) -> bool:
        """Verifica si un término es específico de alguna región."""
        return len(self.get_term_info(term)) > 0

    def get_term_regions(self, term: str) -> list[str]:
        """Obtiene las regiones donde se usa un término."""
        return list(self.get_term_info(term).keys())


class RegionalDetector(BaseDetector):
    """
    Detecta mezcla de variantes regionales y sugiere alternativas.

    Usa diccionarios de términos regionales para identificar
    inconsistencias en el uso del español de distintas variantes.
    """

    # Términos regionales comunes (fallback si no hay diccionarios)
    BUILTIN_REGIONAL_TERMS = {
        # España
        "ordenador": {
            "region": "es_ES",
            "alternatives": {"es_MX": "computadora", "es_AR": "computadora"},
        },
        "móvil": {"region": "es_ES", "alternatives": {"es_MX": "celular", "es_AR": "celular"}},
        "coche": {"region": "es_ES", "alternatives": {"es_MX": "carro", "es_AR": "auto"}},
        "piso": {
            "region": "es_ES",
            "alternatives": {"es_MX": "departamento", "es_AR": "departamento"},
        },
        "vale": {"region": "es_ES", "alternatives": {"es_MX": "ok", "es_AR": "dale"}},
        "mola": {
            "region": "es_ES",
            "alternatives": {"es_MX": "está padre", "es_AR": "está copado"},
        },
        "guay": {"region": "es_ES", "alternatives": {"es_MX": "chido", "es_AR": "copado"}},
        "tío": {"region": "es_ES", "alternatives": {"es_MX": "güey", "es_AR": "che"}},
        "gilipollas": {"region": "es_ES", "alternatives": {"es_MX": "pendejo", "es_AR": "boludo"}},
        "curro": {"region": "es_ES", "alternatives": {"es_MX": "chamba", "es_AR": "laburo"}},
        "pasta": {"region": "es_ES", "alternatives": {"es_MX": "lana", "es_AR": "guita"}},
        "tíos": {"region": "es_ES", "alternatives": {"es_MX": "güeyes", "es_AR": "pibes"}},
        "chaval": {"region": "es_ES", "alternatives": {"es_MX": "chamaco", "es_AR": "pibe"}},
        "majo": {"region": "es_ES", "alternatives": {"es_MX": "chido", "es_AR": "copado"}},
        # México
        "computadora": {"region": "es_MX", "alternatives": {"es_ES": "ordenador"}},
        "celular": {"region": "es_MX", "alternatives": {"es_ES": "móvil"}},
        "carro": {"region": "es_MX", "alternatives": {"es_ES": "coche"}},
        "departamento": {"region": "es_MX", "alternatives": {"es_ES": "piso"}},
        "chido": {"region": "es_MX", "alternatives": {"es_ES": "guay"}},
        "güey": {"region": "es_MX", "alternatives": {"es_ES": "tío"}},
        "chamba": {"region": "es_MX", "alternatives": {"es_ES": "curro"}},
        "lana": {"region": "es_MX", "alternatives": {"es_ES": "pasta"}},
        "chamaco": {"region": "es_MX", "alternatives": {"es_ES": "chaval"}},
        "padre": {"region": "es_MX", "alternatives": {"es_ES": "guay"}},  # como adjetivo
        # Argentina
        "laburo": {"region": "es_AR", "alternatives": {"es_ES": "curro", "es_MX": "chamba"}},
        "guita": {"region": "es_AR", "alternatives": {"es_ES": "pasta", "es_MX": "lana"}},
        "pibe": {"region": "es_AR", "alternatives": {"es_ES": "chaval", "es_MX": "chamaco"}},
        "copado": {"region": "es_AR", "alternatives": {"es_ES": "guay", "es_MX": "chido"}},
        "boludo": {"region": "es_AR", "alternatives": {"es_ES": "gilipollas", "es_MX": "pendejo"}},
        "che": {"region": "es_AR", "alternatives": {"es_ES": "tío", "es_MX": "güey"}},
        "bárbaro": {"region": "es_AR", "alternatives": {"es_ES": "genial", "es_MX": "padre"}},
        "mina": {"region": "es_AR", "alternatives": {"es_ES": "tía", "es_MX": "chava"}},
        "bondi": {"region": "es_AR", "alternatives": {"es_ES": "autobús", "es_MX": "camión"}},
    }

    def __init__(
        self,
        config: RegionalConfig | None = None,
        dictionary: RegionalDictionary | None = None,
    ):
        self.config = config or RegionalConfig()
        self.dictionary = dictionary or RegionalDictionary()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.REGIONAL

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
    ) -> list[CorrectionIssue]:
        """
        Detecta variaciones regionales en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (opcional, para mejor tokenización)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues = []
        target_region = self.config.target_region

        # Obtener tokens
        if spacy_doc is not None:
            tokens = [
                (token.text, token.idx, token.idx + len(token.text))
                for token in spacy_doc
                if token.is_alpha
            ]
        else:
            import re

            tokens = [
                (m.group(), m.start(), m.end())
                for m in re.finditer(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b", text)
            ]

        # Detectar términos regionales
        found_regions: dict[str, list[tuple[str, int, int]]] = {}  # {region: [(term, start, end), ...]}

        for word, start, end in tokens:
            word_lower = word.lower()

            # Buscar en diccionarios cargados
            term_info = self.dictionary.get_term_info(word_lower)

            # Si no hay en diccionarios, usar built-in
            if not term_info and word_lower in self.BUILTIN_REGIONAL_TERMS:
                builtin = self.BUILTIN_REGIONAL_TERMS[word_lower]
                region = builtin["region"]

                if region not in found_regions:
                    found_regions[region] = []
                found_regions[region].append((word, start, end, builtin))

            elif term_info:
                for region, info in term_info.items():
                    if region not in found_regions:
                        found_regions[region] = []
                    found_regions[region].append((word, start, end, info))

        # Analizar resultados
        if len(found_regions) > 1 and self.config.detect_mixed_variants:
            # Hay mezcla de variantes
            issues.extend(
                self._create_mixed_variant_issues(found_regions, target_region, text, chapter_index)
            )
        elif self.config.suggest_regional_alternatives:
            # Sugerir alternativas si no es la región objetivo
            issues.extend(
                self._create_alternative_issues(found_regions, target_region, text, chapter_index)
            )

        return issues

    def _create_mixed_variant_issues(
        self,
        found_regions: dict,
        target_region: str,
        text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """Crea issues por mezcla de variantes regionales."""
        issues = []

        # Encontrar la región dominante (más términos)
        dominant_region = max(found_regions.keys(), key=lambda r: len(found_regions[r]))

        # Reportar términos de otras regiones
        for region, terms in found_regions.items():
            if region == dominant_region:
                continue

            for word, start, end, info in terms[:5]:  # Limitar a 5 por región
                # Obtener alternativa de la región dominante o objetivo
                alternative = None
                if isinstance(info, dict):
                    alternatives = info.get("alternatives", {})
                    alternative = alternatives.get(target_region) or alternatives.get(
                        dominant_region
                    )

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=RegionalIssueType.MIXED_REGIONAL.value,
                        start_char=start,
                        end_char=end,
                        text=word,
                        explanation=(
                            f"Mezcla de variantes regionales: '{word}' es típico de "
                            f"{self._region_name(region)}, pero el texto usa principalmente "
                            f"{self._region_name(dominant_region)}"
                        ),
                        suggestion=alternative,
                        confidence=0.75,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id="REGIONAL_MIXED",
                        extra_data={
                            "term_region": region,
                            "dominant_region": dominant_region,
                            "alternative": alternative,
                        },
                    )
                )

        return issues

    def _create_alternative_issues(
        self,
        found_regions: dict,
        target_region: str,
        text: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """Crea issues sugiriendo alternativas para la región objetivo."""
        issues = []

        for region, terms in found_regions.items():
            if region == target_region:
                continue

            for word, start, end, info in terms[:3]:  # Limitar a 3 por región
                alternative = None
                if isinstance(info, dict):
                    alternatives = info.get("alternatives", {})
                    alternative = alternatives.get(target_region)

                if alternative:
                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=RegionalIssueType.SUGGESTED_ALTERNATIVE.value,
                            start_char=start,
                            end_char=end,
                            text=word,
                            explanation=(
                                f"'{word}' es típico de {self._region_name(region)}. "
                                f"En {self._region_name(target_region)} se usa '{alternative}'"
                            ),
                            suggestion=alternative,
                            confidence=0.7,
                            context=self._extract_context(text, start, end),
                            chapter_index=chapter_index,
                            rule_id="REGIONAL_ALT",
                            extra_data={
                                "term_region": region,
                                "target_region": target_region,
                            },
                        )
                    )

        return issues

    def _region_name(self, code: str) -> str:
        """Convierte código de región a nombre legible."""
        names = {
            "es_ES": "español de España",
            "es_MX": "español de México",
            "es_AR": "español de Argentina",
            "es_CO": "español de Colombia",
            "es_CL": "español de Chile",
            "es_PE": "español de Perú",
        }
        return names.get(code, code)
