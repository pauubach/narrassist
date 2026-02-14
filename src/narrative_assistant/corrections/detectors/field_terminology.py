"""
Detector de terminología especializada por campo.

Detecta cuando se usan términos técnicos de un campo que no corresponde
al tipo de documento, o sugiere alternativas más accesibles para
audiencia general.
"""

import json
import logging
from pathlib import Path

from ..base import BaseDetector, CorrectionIssue
from ..config import DocumentField, DocumentProfile, FieldDictionaryConfig
from ..types import CorrectionCategory, FieldTermIssueType

logger = logging.getLogger(__name__)


class FieldDictionary:
    """
    Diccionario de términos especializados por campo.

    Carga y gestiona diccionarios JSON con terminología técnica
    de cada campo (jurídico, médico, informático, etc.).
    """

    def __init__(self, dictionaries_path: Path | None = None):
        """
        Inicializa el diccionario de campos.

        Args:
            dictionaries_path: Ruta a la carpeta de diccionarios.
                              Por defecto: ~/.narrative_assistant/dictionaries
        """
        if dictionaries_path is None:
            dictionaries_path = Path.home() / ".narrative_assistant" / "dictionaries"

        self.dictionaries_path = dictionaries_path
        self.dictionaries: dict[str, dict] = {}
        self._loaded_fields: set[DocumentField] = set()

    def load(self, fields: list[DocumentField] | None = None) -> None:
        """
        Carga los diccionarios de los campos especificados.

        Args:
            fields: Lista de campos a cargar. Si None, carga todos.
        """
        fields_path = self.dictionaries_path / "fields"

        if not fields_path.exists():
            logger.warning(f"Field dictionaries path not found: {fields_path}")
            return

        for json_file in fields_path.glob("*.json"):
            field_name = json_file.stem  # legal, medical, technical, etc.

            # Mapear nombre de archivo a enum
            try:
                field_enum = DocumentField(field_name)
            except ValueError:
                logger.warning(f"Unknown field in dictionary: {field_name}")
                continue

            if fields is not None and field_enum not in fields:
                continue

            try:
                with open(json_file, encoding="utf-8") as f:
                    self.dictionaries[field_name] = json.load(f)
                self._loaded_fields.add(field_enum)
                logger.info(f"Loaded field dictionary: {field_name}")
            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")

    def get_term_info(self, term: str) -> dict[DocumentField, dict]:
        """
        Obtiene información sobre un término en todos los campos.

        Args:
            term: Término a buscar

        Returns:
            Dict con {field: {info del término}} para cada campo donde existe
        """
        result = {}
        term_lower = term.lower()

        for field_name, dictionary in self.dictionaries.items():
            terms = dictionary.get("terms", {})
            if term_lower in terms:
                try:
                    field_enum = DocumentField(field_name)
                    result[field_enum] = terms[term_lower]
                except ValueError:
                    pass

        return result

    def get_accessible_alternative(self, term: str, field: DocumentField) -> str | None:
        """
        Obtiene una alternativa más accesible para un término técnico.

        Args:
            term: Término técnico
            field: Campo del término

        Returns:
            Alternativa accesible o None
        """
        term_info = self.get_term_info(term)

        if field in term_info:
            return term_info[field].get("accessible_alternative")

        return None

    def is_field_term(self, term: str) -> bool:
        """Verifica si un término es específico de algún campo."""
        return len(self.get_term_info(term)) > 0

    def get_term_fields(self, term: str) -> list[DocumentField]:
        """Obtiene los campos donde se usa un término."""
        return list(self.get_term_info(term).keys())


# Diccionario built-in con términos comunes por campo
BUILTIN_FIELD_TERMS = {
    # Términos jurídicos
    "jurisprudencia": {
        "field": DocumentField.LEGAL,
        "definition": "Conjunto de sentencias que interpretan la ley",
        "accessible_alternative": "sentencias de los tribunales",
    },
    "demandante": {
        "field": DocumentField.LEGAL,
        "definition": "Persona que presenta una demanda",
        "accessible_alternative": "quien presenta la demanda",
    },
    "demandado": {
        "field": DocumentField.LEGAL,
        "definition": "Persona contra quien se presenta la demanda",
        "accessible_alternative": "persona demandada",
    },
    "otrosí": {
        "field": DocumentField.LEGAL,
        "definition": "Además, en escritos judiciales",
        "accessible_alternative": "además",
    },
    "reconvención": {
        "field": DocumentField.LEGAL,
        "definition": "Contrademanda del demandado",
        "accessible_alternative": "demanda del demandado contra el demandante",
    },
    "litispendencia": {
        "field": DocumentField.LEGAL,
        "definition": "Existencia de otro proceso sobre lo mismo",
        "accessible_alternative": "proceso judicial ya en curso",
    },
    "desistimiento": {
        "field": DocumentField.LEGAL,
        "definition": "Renuncia a la acción o al derecho",
        "accessible_alternative": "renuncia al proceso",
    },
    "caducidad": {
        "field": DocumentField.LEGAL,
        "definition": "Extinción de un derecho por el paso del tiempo",
        "accessible_alternative": "pérdida del derecho por no ejercerlo a tiempo",
    },
    "prescripción": {
        "field": DocumentField.LEGAL,
        "definition": "Adquisición o extinción de derechos por el tiempo",
        "accessible_alternative": "cuando pasa demasiado tiempo",
    },
    "allanamiento": {
        "field": DocumentField.LEGAL,
        "definition": "Aceptación de las pretensiones del demandante",
        "accessible_alternative": "aceptación de lo que pide el demandante",
    },
    # Términos médicos
    "etiología": {
        "field": DocumentField.MEDICAL,
        "definition": "Estudio de las causas de las enfermedades",
        "accessible_alternative": "causa de la enfermedad",
    },
    "patogénesis": {
        "field": DocumentField.MEDICAL,
        "definition": "Mecanismo de desarrollo de una enfermedad",
        "accessible_alternative": "cómo se desarrolla la enfermedad",
    },
    "profilaxis": {
        "field": DocumentField.MEDICAL,
        "definition": "Prevención de enfermedades",
        "accessible_alternative": "prevención",
    },
    "idiopático": {
        "field": DocumentField.MEDICAL,
        "definition": "De causa desconocida",
        "accessible_alternative": "de causa desconocida",
    },
    "iatrogénico": {
        "field": DocumentField.MEDICAL,
        "definition": "Causado por el tratamiento médico",
        "accessible_alternative": "causado por el tratamiento",
    },
    "sintomatología": {
        "field": DocumentField.MEDICAL,
        "definition": "Conjunto de síntomas",
        "accessible_alternative": "síntomas",
    },
    "posología": {
        "field": DocumentField.MEDICAL,
        "definition": "Dosificación de medicamentos",
        "accessible_alternative": "dosis del medicamento",
    },
    "anamnesis": {
        "field": DocumentField.MEDICAL,
        "definition": "Historia clínica del paciente",
        "accessible_alternative": "historial médico",
    },
    "diagnóstico diferencial": {
        "field": DocumentField.MEDICAL,
        "definition": "Lista de posibles diagnósticos",
        "accessible_alternative": "posibles diagnósticos",
    },
    "pronóstico": {
        "field": DocumentField.MEDICAL,
        "definition": "Predicción de la evolución",
        "accessible_alternative": "evolución esperada",
    },
    # Términos informáticos/técnicos
    "algoritmo": {
        "field": DocumentField.TECHNICAL,
        "definition": "Secuencia de pasos para resolver un problema",
        "accessible_alternative": "conjunto de instrucciones",
    },
    "backend": {
        "field": DocumentField.TECHNICAL,
        "definition": "Parte del servidor de una aplicación",
        "accessible_alternative": "parte interna del sistema",
    },
    "frontend": {
        "field": DocumentField.TECHNICAL,
        "definition": "Interfaz de usuario de una aplicación",
        "accessible_alternative": "parte visible para el usuario",
    },
    "api": {
        "field": DocumentField.TECHNICAL,
        "definition": "Interfaz de programación",
        "accessible_alternative": "conexión entre sistemas",
    },
    "framework": {
        "field": DocumentField.TECHNICAL,
        "definition": "Marco de trabajo para desarrollo",
        "accessible_alternative": "herramienta de desarrollo",
    },
    "deploy": {
        "field": DocumentField.TECHNICAL,
        "definition": "Desplegar una aplicación",
        "accessible_alternative": "poner en funcionamiento",
    },
    "cache": {
        "field": DocumentField.TECHNICAL,
        "definition": "Almacenamiento temporal para acelerar",
        "accessible_alternative": "memoria temporal",
    },
    "bug": {
        "field": DocumentField.TECHNICAL,
        "definition": "Error en el software",
        "accessible_alternative": "error",
    },
    "debugging": {
        "field": DocumentField.TECHNICAL,
        "definition": "Proceso de encontrar y corregir errores",
        "accessible_alternative": "corrección de errores",
    },
    "refactoring": {
        "field": DocumentField.TECHNICAL,
        "definition": "Reestructurar código sin cambiar funcionalidad",
        "accessible_alternative": "reorganizar el código",
    },
    # Términos de negocios
    "roi": {
        "field": DocumentField.BUSINESS,
        "definition": "Retorno de la inversión",
        "accessible_alternative": "beneficio de la inversión",
    },
    "kpi": {
        "field": DocumentField.BUSINESS,
        "definition": "Indicador clave de rendimiento",
        "accessible_alternative": "indicador de éxito",
    },
    "stakeholder": {
        "field": DocumentField.BUSINESS,
        "definition": "Parte interesada",
        "accessible_alternative": "persona interesada",
    },
    "benchmark": {
        "field": DocumentField.BUSINESS,
        "definition": "Punto de referencia para comparar",
        "accessible_alternative": "referencia de comparación",
    },
    "outsourcing": {
        "field": DocumentField.BUSINESS,
        "definition": "Subcontratación de servicios",
        "accessible_alternative": "subcontratación",
    },
    "feedback": {
        "field": DocumentField.BUSINESS,
        "definition": "Retroalimentación",
        "accessible_alternative": "opinión",
    },
    "briefing": {
        "field": DocumentField.BUSINESS,
        "definition": "Reunión informativa breve",
        "accessible_alternative": "reunión de información",
    },
    "brainstorming": {
        "field": DocumentField.BUSINESS,
        "definition": "Lluvia de ideas",
        "accessible_alternative": "generar ideas en grupo",
    },
    # Términos académicos
    "metodología": {
        "field": DocumentField.ACADEMIC,
        "definition": "Conjunto de métodos de investigación",
        "accessible_alternative": "método de estudio",
    },
    "hipótesis": {
        "field": DocumentField.ACADEMIC,
        "definition": "Suposición que se intenta comprobar",
        "accessible_alternative": "suposición inicial",
    },
    "paradigma": {
        "field": DocumentField.ACADEMIC,
        "definition": "Marco teórico de referencia",
        "accessible_alternative": "forma de entender algo",
    },
    "epistemología": {
        "field": DocumentField.ACADEMIC,
        "definition": "Teoría del conocimiento",
        "accessible_alternative": "estudio del conocimiento",
    },
    "hermenéutica": {
        "field": DocumentField.ACADEMIC,
        "definition": "Arte de interpretar textos",
        "accessible_alternative": "interpretación de textos",
    },
    "praxis": {
        "field": DocumentField.ACADEMIC,
        "definition": "Práctica, acción",
        "accessible_alternative": "práctica",
    },
    "heurística": {
        "field": DocumentField.ACADEMIC,
        "definition": "Método de descubrimiento",
        "accessible_alternative": "método de búsqueda",
    },
}


class FieldTerminologyDetector(BaseDetector):
    """
    Detecta uso de terminología especializada fuera de contexto.

    Identifica términos técnicos de campos específicos y alerta
    cuando aparecen en documentos de otro tipo, o sugiere
    alternativas más accesibles.
    """

    def __init__(
        self,
        config: FieldDictionaryConfig | None = None,
        profile: DocumentProfile | None = None,
        dictionary: FieldDictionary | None = None,
    ):
        self.config = config or FieldDictionaryConfig()
        self.profile = profile or DocumentProfile()
        self.dictionary = dictionary or FieldDictionary()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.TERMINOLOGY

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
    ) -> list[CorrectionIssue]:
        """
        Detecta terminología especializada en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues = []

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

        # Buscar términos especializados
        found_terms: dict[DocumentField, list] = {}

        for word, start, end in tokens:
            word_lower = word.lower()

            # Buscar en diccionarios cargados
            term_info = self.dictionary.get_term_info(word_lower)

            # Si no hay en diccionarios, usar built-in
            if not term_info and word_lower in BUILTIN_FIELD_TERMS:
                builtin = BUILTIN_FIELD_TERMS[word_lower]
                field = builtin["field"]

                if field not in found_terms:
                    found_terms[field] = []  # type: ignore[index]
                found_terms[field].append((word, start, end, builtin))  # type: ignore[index]

            elif term_info:
                for field, info in term_info.items():
                    if field not in found_terms:
                        found_terms[field] = []
                    found_terms[field].append((word, start, end, info))

        # Analizar resultados según el perfil del documento
        for field, terms in found_terms.items():
            # ¿El campo es relevante para este documento?
            is_relevant = self.profile.is_field_relevant(field)

            for word, start, end, info in terms[:10]:  # Limitar
                # Si el campo NO es relevante, alertar sobre término inesperado
                if not is_relevant and self.config.alert_unexpected_field_terms:
                    issues.append(
                        CorrectionIssue(
                            category=self.category.value,
                            issue_type=FieldTermIssueType.UNEXPECTED_FIELD_TERM.value,
                            start_char=start,
                            end_char=end,
                            text=word,
                            explanation=(
                                f"'{word}' es un término de {self._field_name(field)}, "
                                f"pero el documento está configurado como "
                                f"{self._field_name(self.profile.document_field)}"
                            ),
                            suggestion=info.get("accessible_alternative"),
                            confidence=0.7,
                            context=self._extract_context(text, start, end),
                            chapter_index=chapter_index,
                            rule_id="FIELD_UNEXPECTED",
                            extra_data={
                                "term_field": field.value,
                                "document_field": self.profile.document_field.value,
                                "definition": info.get("definition"),
                            },
                        )
                    )

                # Si hay que sugerir alternativas accesibles
                elif self.config.suggest_accessible_alternatives:
                    alternative = info.get("accessible_alternative")
                    if alternative and self.profile.audience != AudienceType.SPECIALIST:
                        issues.append(
                            CorrectionIssue(
                                category=self.category.value,
                                issue_type=FieldTermIssueType.NEEDS_GLOSSARY.value,
                                start_char=start,
                                end_char=end,
                                text=word,
                                explanation=(
                                    f"'{word}' puede requerir explicación para "
                                    f"lectores no especializados"
                                ),
                                suggestion=alternative,
                                confidence=0.6,
                                context=self._extract_context(text, start, end),
                                chapter_index=chapter_index,
                                rule_id="FIELD_NEEDS_GLOSSARY",
                                extra_data={
                                    "term_field": field.value,
                                    "definition": info.get("definition"),
                                },
                            )
                        )

        return issues

    def _field_name(self, field: DocumentField) -> str:
        """Convierte campo a nombre legible."""
        names = {
            DocumentField.GENERAL: "uso general",
            DocumentField.LITERARY: "literatura",
            DocumentField.JOURNALISTIC: "periodismo",
            DocumentField.ACADEMIC: "ámbito académico",
            DocumentField.TECHNICAL: "ámbito técnico/informático",
            DocumentField.LEGAL: "ámbito jurídico",
            DocumentField.MEDICAL: "ámbito médico",
            DocumentField.BUSINESS: "ámbito empresarial",
            DocumentField.SELFHELP: "autoayuda",
            DocumentField.CULINARY: "gastronomía",
        }
        return names.get(field, field.value)


# Import AudienceType for the detector
from ..config import AudienceType


def get_field_detector(
    config: FieldDictionaryConfig | None = None,
    profile: DocumentProfile | None = None,
) -> FieldTerminologyDetector:
    """Obtiene una instancia del detector de terminología de campo."""
    return FieldTerminologyDetector(config=config, profile=profile)
