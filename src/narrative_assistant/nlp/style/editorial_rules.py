"""
Sistema de reglas editoriales personalizables.

Las reglas editoriales son preferencias de estilo específicas de cada editorial
o corrector, NO errores gramaticales. Ejemplos:
- "nuestros corazones" -> "nuestro corazón" (órganos únicos en singular)
- "quizás" -> "quizá" (preferencia editorial)
- "período" -> "periodo" (sin tilde diacrítica)

Uso:
    from narrative_assistant.nlp.style.editorial_rules import (
        EditorialRulesChecker,
        get_editorial_checker,
    )

    checker = get_editorial_checker()
    result = checker.check(text, custom_rules=[...])
"""

import contextlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from ..grammar.base import GrammarSeverity

logger = logging.getLogger(__name__)


class EditorialRuleType(Enum):
    """Tipos de reglas editoriales."""

    # Sustituciones simples
    WORD_REPLACEMENT = "word_replacement"  # quizás -> quizá

    # Patrones regex
    PATTERN_REPLACEMENT = "pattern_replacement"  # período -> periodo

    # Reglas contextuales (requieren análisis)
    CONTEXTUAL = "contextual"  # nuestros corazones -> nuestro corazón

    # Formato y puntuación
    PUNCTUATION = "punctuation"  # guiones cortos -> largos

    # Estilo numérico
    NUMBER_STYLE = "number_style"  # edades con números, años con letra

    # Posesivos
    POSSESSIVE = "possessive"  # exceso de posesivos

    # Comillas y marcadores
    QUOTATION = "quotation"  # comillas bajas obligatorias


class EditorialRuleCategory(Enum):
    """Categorías de reglas para organización."""

    ORTHOGRAPHY = "orthography"  # Ortografía (tildes opcionales)
    LEXICON = "lexicon"  # Léxico (palabras preferidas)
    SYNTAX = "syntax"  # Sintaxis (construcciones)
    PUNCTUATION = "punctuation"  # Puntuación
    NUMBERS = "numbers"  # Números y cantidades
    STYLE = "style"  # Estilo general


@dataclass
class EditorialRule:
    """
    Una regla editorial personalizable.

    Attributes:
        id: Identificador único de la regla
        name: Nombre descriptivo
        description: Explicación de la regla
        rule_type: Tipo de regla
        category: Categoría para organización
        pattern: Patrón a buscar (regex o texto)
        replacement: Texto de reemplazo (si aplica)
        context_words: Palabras de contexto para reglas contextuales
        severity: Severidad del aviso
        enabled: Si la regla está activa
        examples: Ejemplos de uso
    """

    id: str
    name: str
    description: str
    rule_type: EditorialRuleType
    category: EditorialRuleCategory
    pattern: str
    replacement: str | None = None
    context_words: list[str] = field(default_factory=list)
    severity: GrammarSeverity = GrammarSeverity.STYLE
    enabled: bool = True
    examples: list[tuple[str, str]] = field(default_factory=list)

    # Función de validación personalizada (opcional)
    validator: Callable[[str, re.Match], bool] | None = None


@dataclass
class EditorialIssue:
    """Un problema encontrado por una regla editorial."""

    rule_id: str
    rule_name: str
    text: str
    replacement: str | None
    start: int
    end: int
    severity: GrammarSeverity
    explanation: str
    category: EditorialRuleCategory


@dataclass
class EditorialReport:
    """Reporte de análisis editorial."""

    issues: list[EditorialIssue] = field(default_factory=list)
    rules_applied: int = 0
    text_length: int = 0

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict:
        return {
            "issues": [
                {
                    "rule_id": i.rule_id,
                    "rule_name": i.rule_name,
                    "text": i.text,
                    "replacement": i.replacement,
                    "start": i.start,
                    "end": i.end,
                    "severity": i.severity.value,
                    "explanation": i.explanation,
                    "category": i.category.value,
                }
                for i in self.issues
            ],
            "rules_applied": self.rules_applied,
            "text_length": self.text_length,
            "issue_count": self.issue_count,
        }


# =============================================================================
# REGLAS PREDEFINIDAS - Basadas en las reglas editoriales proporcionadas
# =============================================================================

SINGULAR_BODY_PARTS = ["corazón", "cerebro", "mente", "vida", "alma", "cabeza"]

PREDEFINED_RULES: list[EditorialRule] = [
    # -------------------------------------------------------------------------
    # ÓRGANOS ÚNICOS EN SINGULAR
    # -------------------------------------------------------------------------
    EditorialRule(
        id="singular_body_parts",
        name="Órganos únicos en singular",
        description="Partes del cuerpo únicas (corazón, cerebro, mente, vida) "
        "deben ir en singular con posesivos plurales",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.SYNTAX,
        pattern=r"\b(nuestros?|vuestros?|sus)\s+(corazones|cerebros|mentes|vidas|almas|cabezas)\b",
        replacement=None,  # Se calcula dinámicamente
        context_words=SINGULAR_BODY_PARTS,
        severity=GrammarSeverity.STYLE,
        examples=[
            ("nuestros corazones", "nuestro corazón"),
            ("sus mentes", "su mente"),
            ("vuestras vidas", "vuestra vida"),
        ],
    ),
    # -------------------------------------------------------------------------
    # NÚMEROS: EDADES VS AÑOS
    # -------------------------------------------------------------------------
    EditorialRule(
        id="age_with_digits",
        name="Edades con números",
        description="Las edades se escriben con cifras",
        rule_type=EditorialRuleType.NUMBER_STYLE,
        category=EditorialRuleCategory.NUMBERS,
        pattern=r"\b(tenía|tiene|cumplió|cumple|con)\s+(un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciséis|diecisiete|dieciocho|diecinueve|veinte|veintiuno|veintidós|veintitrés|veinticuatro|veinticinco|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)\s+años",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("tenía veinte años", "tenía 20 años"),
            ("cumplió treinta años", "cumplió 30 años"),
        ],
    ),
    EditorialRule(
        id="years_with_letters",
        name="Duración en años con letra",
        description="Los periodos de tiempo (duración) se escriben con letra",
        rule_type=EditorialRuleType.NUMBER_STYLE,
        category=EditorialRuleCategory.NUMBERS,
        pattern=r"\b(durante|hace|desde hace|por|en)\s+(\d+)\s+años\b",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("durante 5 años", "durante cinco años"),
            ("hace 10 años", "hace diez años"),
        ],
    ),
    # -------------------------------------------------------------------------
    # DOBLES ESPACIOS
    # -------------------------------------------------------------------------
    EditorialRule(
        id="double_spaces",
        name="Dobles espacios",
        description="No debe haber espacios dobles",
        rule_type=EditorialRuleType.PATTERN_REPLACEMENT,
        category=EditorialRuleCategory.PUNCTUATION,
        pattern=r"  +",
        replacement=" ",
        severity=GrammarSeverity.WARNING,
        examples=[
            ("palabra  palabra", "palabra palabra"),
        ],
    ),
    # -------------------------------------------------------------------------
    # EXPRESIONES PREFERIDAS
    # -------------------------------------------------------------------------
    EditorialRule(
        id="por_contra",
        name="Por contra -> Por el contrario",
        description="'Por contra' debe ser 'por el contrario'",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.LEXICON,
        pattern=r"\bpor contra\b",
        replacement="por el contrario",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("por contra, él pensaba", "por el contrario, él pensaba"),
        ],
    ),
    # -------------------------------------------------------------------------
    # PARTITIVOS CON ARTÍCULO
    # -------------------------------------------------------------------------
    EditorialRule(
        id="resto_de_articulo",
        name="El resto de + artículo",
        description="'El resto de X' requiere artículo: 'el resto del/de los/de la/de las X'",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.SYNTAX,
        pattern=r"\bel resto de\s+(?!la\s|el\s|los\s|las\s)(\w+)",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("el resto de soldados", "el resto de los soldados"),
            ("el resto de gente", "el resto de la gente"),
        ],
    ),
    EditorialRule(
        id="mayoria_de_articulo",
        name="La mayoría de + artículo",
        description="'La mayoría de X' requiere artículo",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.SYNTAX,
        pattern=r"\bla mayoría de\s+(?!la\s|el\s|los\s|las\s)(\w+)",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("la mayoría de personas", "la mayoría de las personas"),
        ],
    ),
    EditorialRule(
        id="mayor_parte_de_articulo",
        name="La mayor parte de + artículo",
        description="'La mayor parte de X' requiere artículo",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.SYNTAX,
        pattern=r"\bla mayor parte de\s+(?!la\s|el\s|los\s|las\s)(\w+)",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("la mayor parte de tiempo", "la mayor parte del tiempo"),
        ],
    ),
    # -------------------------------------------------------------------------
    # DEMOSTRATIVOS SIN ACENTO (RAE 2010)
    # -------------------------------------------------------------------------
    EditorialRule(
        id="demonstratives_no_accent",
        name="Demostrativos sin acento",
        description="Los demostrativos no llevan tilde (RAE 2010)",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.ORTHOGRAPHY,
        pattern=r"\b(éste|ésta|éstos|éstas|ése|ésa|ésos|ésas|aquél|aquélla|aquéllos|aquéllas)\b",
        replacement=None,  # Se calcula quitando la tilde
        severity=GrammarSeverity.STYLE,
        examples=[
            ("éste es el libro", "este es el libro"),
            ("aquélla mujer", "aquella mujer"),
        ],
    ),
    # -------------------------------------------------------------------------
    # SOLO SIN ACENTO (RAE 2010)
    # -------------------------------------------------------------------------
    EditorialRule(
        id="solo_no_accent",
        name="Solo sin acento",
        description="'Solo' (adverbio) no lleva tilde (RAE 2010)",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.ORTHOGRAPHY,
        pattern=r"\bsólo\b",
        replacement="solo",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("sólo quería", "solo quería"),
        ],
    ),
    # -------------------------------------------------------------------------
    # GUIONES: CORTOS -> LARGOS EN INCISOS
    # -------------------------------------------------------------------------
    EditorialRule(
        id="dash_inciso",
        name="Guiones largos en incisos",
        description="Los incisos usan raya (—), no guion corto (-)",
        rule_type=EditorialRuleType.PUNCTUATION,
        category=EditorialRuleCategory.PUNCTUATION,
        pattern=r"(\s)-([^-\d])([^-]*[^-\s])-(\s)",
        replacement=r"\1—\2\3—\4",
        severity=GrammarSeverity.STYLE,
        examples=[
            (" -dijo ella- ", " —dijo ella— "),
        ],
    ),
    # -------------------------------------------------------------------------
    # AÚN ASÍ -> AUN ASÍ
    # -------------------------------------------------------------------------
    EditorialRule(
        id="aun_asi",
        name="Aun así (sin tilde)",
        description="'Aun así' (= incluso así) no lleva tilde",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.ORTHOGRAPHY,
        pattern=r"\baún así\b",
        replacement="aun así",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("aún así, continuó", "aun así, continuó"),
        ],
    ),
    # -------------------------------------------------------------------------
    # AGUDIZAR -> AGUZAR (SENTIDOS)
    # -------------------------------------------------------------------------
    EditorialRule(
        id="aguzar_sentidos",
        name="Aguzar (sentidos)",
        description="Para los sentidos se usa 'aguzar', no 'agudizar'",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.LEXICON,
        pattern=r"\bagudiz\w*\s+(el\s+)?(oído|vista|olfato|tacto|gusto|sentido|oreja|ingeni)",
        replacement=None,  # Requiere conjugación
        severity=GrammarSeverity.STYLE,
        examples=[
            ("agudizó el oído", "aguzó el oído"),
            ("agudizar la vista", "aguzar la vista"),
        ],
    ),
    # -------------------------------------------------------------------------
    # PUNTUACIÓN INTERROGATIVA
    # -------------------------------------------------------------------------
    EditorialRule(
        id="entonces_interrogativo",
        name="Entonces + interrogación",
        description="'Entonces, ¿' debe ser 'Entonces ¿' (sin coma)",
        rule_type=EditorialRuleType.PUNCTUATION,
        category=EditorialRuleCategory.PUNCTUATION,
        pattern=r"\b(Entonces|Pero|Y|O),\s*¿",
        replacement=None,  # Se quita la coma
        severity=GrammarSeverity.STYLE,
        examples=[
            ("Entonces, ¿qué hacemos?", "Entonces ¿qué hacemos?"),
            ("Pero, ¿por qué?", "Pero ¿por qué?"),
        ],
    ),
    # -------------------------------------------------------------------------
    # QUIZÁS -> QUIZÁ
    # -------------------------------------------------------------------------
    EditorialRule(
        id="quiza_preferido",
        name="Quizá (preferido)",
        description="Preferir 'quizá' sobre 'quizás'",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.LEXICON,
        pattern=r"\bquizás\b",
        replacement="quizá",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("quizás venga", "quizá venga"),
        ],
    ),
    # -------------------------------------------------------------------------
    # PERÍODO -> PERIODO
    # -------------------------------------------------------------------------
    EditorialRule(
        id="periodo_sin_tilde",
        name="Periodo (sin tilde)",
        description="'Periodo' sin tilde (forma preferida RAE)",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.ORTHOGRAPHY,
        pattern=r"\bperíodo\b",
        replacement="periodo",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("el período de prueba", "el periodo de prueba"),
        ],
    ),
    # -------------------------------------------------------------------------
    # CARDÍACO -> CARDIACO
    # -------------------------------------------------------------------------
    EditorialRule(
        id="cardiaco_sin_tilde",
        name="Cardiaco (sin tilde)",
        description="'Cardiaco' sin tilde (forma preferida)",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.ORTHOGRAPHY,
        pattern=r"\bcardíaco\b",
        replacement="cardiaco",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("ataque cardíaco", "ataque cardiaco"),
        ],
    ),
    # -------------------------------------------------------------------------
    # SISTEMA INMUNITARIO (NO INMUNOLÓGICO)
    # -------------------------------------------------------------------------
    EditorialRule(
        id="sistema_inmunitario",
        name="Sistema inmunitario",
        description="'Sistema inmunitario', no 'inmunológico' ni 'inmune'",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.LEXICON,
        pattern=r"\bsistema\s+(inmunológico|inmune)\b",
        replacement="sistema inmunitario",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("sistema inmunológico", "sistema inmunitario"),
            ("sistema inmune", "sistema inmunitario"),
        ],
    ),
    # -------------------------------------------------------------------------
    # ALIMENTICIO -> ALIMENTARIO
    # -------------------------------------------------------------------------
    EditorialRule(
        id="alimentario",
        name="Alimentario (no alimenticio)",
        description="Preferir 'alimentario' sobre 'alimenticio'",
        rule_type=EditorialRuleType.WORD_REPLACEMENT,
        category=EditorialRuleCategory.LEXICON,
        pattern=r"\balimenticio\b",
        replacement="alimentario",
        severity=GrammarSeverity.STYLE,
        examples=[
            ("sector alimenticio", "sector alimentario"),
        ],
    ),
    # -------------------------------------------------------------------------
    # EXCESO DE ADVERBIOS EN -MENTE
    # -------------------------------------------------------------------------
    EditorialRule(
        id="adverbios_mente",
        name="Exceso de adverbios en -mente",
        description="Detectar acumulación de adverbios terminados en -mente",
        rule_type=EditorialRuleType.CONTEXTUAL,
        category=EditorialRuleCategory.STYLE,
        pattern=r"\b\w+mente\b.*\b\w+mente\b",
        severity=GrammarSeverity.INFO,
        examples=[
            ("rápidamente y eficientemente", "con rapidez y eficiencia"),
        ],
    ),
]


# =============================================================================
# CHECKER
# =============================================================================


class EditorialRulesChecker:
    """
    Verificador de reglas editoriales.

    Aplica reglas predefinidas y personalizadas al texto.
    """

    def __init__(self, rules: list[EditorialRule] | None = None):
        """
        Inicializa el checker.

        Args:
            rules: Lista de reglas a usar. Si es None, usa las predefinidas.
        """
        self.rules = rules if rules is not None else PREDEFINED_RULES.copy()
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compila los patrones regex."""
        for rule in self.rules:
            if rule.enabled and rule.pattern:
                try:
                    self._compiled_patterns[rule.id] = re.compile(
                        rule.pattern, re.IGNORECASE | re.UNICODE
                    )
                except re.error as e:
                    logger.warning(f"Patrón inválido en regla {rule.id}: {e}")

    def add_rule(self, rule: EditorialRule) -> None:
        """Añade una regla personalizada."""
        self.rules.append(rule)
        if rule.enabled and rule.pattern:
            try:
                self._compiled_patterns[rule.id] = re.compile(
                    rule.pattern, re.IGNORECASE | re.UNICODE
                )
            except re.error as e:
                logger.warning(f"Patrón inválido en regla {rule.id}: {e}")

    def remove_rule(self, rule_id: str) -> bool:
        """Elimina una regla por ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                self._compiled_patterns.pop(rule_id, None)
                return True
        return False

    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Habilita o deshabilita una regla."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = enabled
                return True
        return False

    def check(
        self,
        text: str,
        custom_rules: list[EditorialRule] | None = None,
        categories: list[EditorialRuleCategory] | None = None,
    ) -> EditorialReport:
        """
        Analiza el texto buscando problemas editoriales.

        Args:
            text: Texto a analizar
            custom_rules: Reglas adicionales para este análisis
            categories: Categorías a verificar (None = todas)

        Returns:
            EditorialReport con los problemas encontrados
        """
        report = EditorialReport(text_length=len(text))

        # Combinar reglas
        all_rules = self.rules.copy()
        if custom_rules:
            for rule in custom_rules:
                all_rules.append(rule)
                if rule.pattern and rule.id not in self._compiled_patterns:
                    with contextlib.suppress(re.error):
                        self._compiled_patterns[rule.id] = re.compile(
                            rule.pattern, re.IGNORECASE | re.UNICODE
                        )

        # Aplicar cada regla
        for rule in all_rules:
            if not rule.enabled:
                continue

            if categories and rule.category not in categories:
                continue

            report.rules_applied += 1
            pattern = self._compiled_patterns.get(rule.id)

            if not pattern:
                continue

            # Buscar coincidencias
            for match in pattern.finditer(text):
                # Validación personalizada
                if rule.validator and not rule.validator(text, match):
                    continue

                # Calcular reemplazo
                replacement = self._calculate_replacement(rule, match)

                # Explicación
                explanation = self._generate_explanation(rule, match)

                issue = EditorialIssue(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    text=match.group(0),
                    replacement=replacement,
                    start=match.start(),
                    end=match.end(),
                    severity=rule.severity,
                    explanation=explanation,
                    category=rule.category,
                )
                report.issues.append(issue)

        return report

    def _calculate_replacement(self, rule: EditorialRule, match: re.Match) -> str | None:
        """Calcula el texto de reemplazo para una coincidencia."""

        if rule.replacement:
            # Reemplazo simple o con grupos
            try:
                return match.expand(rule.replacement)
            except re.error:
                return rule.replacement

        # Casos especiales
        if rule.id == "singular_body_parts":
            return self._fix_singular_body_part(match)

        if rule.id == "demonstratives_no_accent":
            return self._remove_accent(match.group(0))

        if rule.id == "entonces_interrogativo":
            # Quitar la coma
            text = match.group(0)
            return text.replace(", ¿", " ¿").replace(",¿", " ¿")  # type: ignore[no-any-return]

        if rule.id == "aguzar_sentidos":
            return self._fix_aguzar(match)

        return None

    def _fix_singular_body_part(self, match: re.Match) -> str:
        """Corrige 'nuestros corazones' -> 'nuestro corazón'."""
        text = match.group(0).lower()

        # Mapeo posesivos plural -> singular
        possessive_map = {
            "nuestros": "nuestro",
            "nuestras": "nuestra",
            "vuestros": "vuestro",
            "vuestras": "vuestra",
            "sus": "su",
        }

        # Mapeo sustantivos plural -> singular
        noun_map = {
            "corazones": "corazón",
            "cerebros": "cerebro",
            "mentes": "mente",
            "vidas": "vida",
            "almas": "alma",
            "cabezas": "cabeza",
        }

        words = text.split()
        if len(words) >= 2:
            poss = possessive_map.get(words[0], words[0])
            noun = noun_map.get(words[1], words[1])
            return f"{poss} {noun}"

        return text  # type: ignore[no-any-return]

    def _remove_accent(self, word: str) -> str:
        """Quita la tilde de un demostrativo."""
        accent_map = {
            "é": "e",
            "á": "a",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "É": "E",
            "Á": "A",
            "Í": "I",
            "Ó": "O",
            "Ú": "U",
        }
        result = word
        for accented, plain in accent_map.items():
            result = result.replace(accented, plain)
        return result

    def _fix_aguzar(self, match: re.Match) -> str:
        """Corrige agudizar -> aguzar para sentidos."""
        text = match.group(0)
        # Conjugaciones de agudizar -> aguzar
        replacements = {
            "agudizo": "aguzo",
            "agudizas": "aguzas",
            "agudiza": "aguza",
            "agudizamos": "aguzamos",
            "agudizan": "aguzan",
            "agudizó": "aguzó",
            "agudizaron": "aguzaron",
            "agudizaba": "aguzaba",
            "agudizaban": "aguzaban",
            "agudizar": "aguzar",
            "agudizando": "aguzando",
        }
        for old, new in replacements.items():
            if old in text.lower():
                return text.replace(old, new).replace(old.capitalize(), new.capitalize())  # type: ignore[no-any-return]
        return text.replace("agudiz", "aguz")  # type: ignore[no-any-return]

    def _generate_explanation(self, rule: EditorialRule, match: re.Match) -> str:
        """Genera una explicación para el problema."""
        base = rule.description

        if rule.examples:
            example = rule.examples[0]
            base += f" Ejemplo: '{example[0]}' → '{example[1]}'"

        return base

    def get_rules_by_category(self, category: EditorialRuleCategory) -> list[EditorialRule]:
        """Obtiene todas las reglas de una categoría."""
        return [r for r in self.rules if r.category == category]

    def get_enabled_rules(self) -> list[EditorialRule]:
        """Obtiene todas las reglas habilitadas."""
        return [r for r in self.rules if r.enabled]

    def to_dict(self) -> dict:
        """Serializa las reglas a diccionario."""
        return {
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "rule_type": r.rule_type.value,
                    "category": r.category.value,
                    "pattern": r.pattern,
                    "replacement": r.replacement,
                    "severity": r.severity.value,
                    "enabled": r.enabled,
                    "examples": r.examples,
                }
                for r in self.rules
            ]
        }


# =============================================================================
# SINGLETON
# =============================================================================

import threading

_lock = threading.Lock()
_instance: EditorialRulesChecker | None = None


def get_editorial_checker() -> EditorialRulesChecker:
    """Obtiene la instancia singleton del checker editorial."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = EditorialRulesChecker()
    return _instance


def reset_editorial_checker() -> None:
    """Resetea la instancia singleton."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# PARSER DE REGLAS EN TEXTO LIBRE
# =============================================================================


def _make_word_pattern(text: str) -> str:
    """
    Crea un patrón regex para buscar texto con word boundaries correctos.

    Maneja casos especiales como palabras que terminan en puntuación.
    """
    escaped = re.escape(text)

    # Si empieza con letra/numero, usar \b al inicio
    if text and text[0].isalnum():
        escaped = r"\b" + escaped
    else:
        # Si empieza con puntuación, usar (?<!\w) para no-palabra antes
        escaped = r"(?<!\w)" + escaped

    # Si termina con letra/numero, usar \b al final
    if text and text[-1].isalnum():
        escaped = escaped + r"\b"
    else:
        # Si termina con puntuación, usar (?!\w) para no-palabra después
        escaped = escaped + r"(?!\w)"

    return escaped


def parse_user_rules(rules_text: str) -> list[EditorialRule]:
    """
    Parsea reglas editoriales escritas en texto libre por el usuario.

    Formatos soportados:
    - Sustituciones: "palabra" -> "reemplazo" o palabra -> reemplazo
    - Preferencias: preferir X sobre Y
    - Evitar: evitar X / no usar X
    - Patrones descriptivos (interpretados con heurísticas)

    Args:
        rules_text: Texto libre con las reglas del usuario

    Returns:
        Lista de EditorialRule parseadas
    """
    if not rules_text or not rules_text.strip():
        return []

    rules: list[EditorialRule] = []
    rule_counter = 0

    # Patrones de parsing
    # 1. Sustitución explícita con comillas: "X" -> "Y"
    substitution_quoted = re.compile(r'"([^"]+)"\s*[-=]>\s*"([^"]+)"', re.UNICODE)

    # 1b. Sustitución sin comillas: palabra -> otra (o frase corta)
    substitution_unquoted = re.compile(r"(\S+)\s*[-=]>\s*(.+?)(?:\s*[\(\[]|$)", re.UNICODE)

    # 2. Preferir X sobre Y
    prefer_pattern = re.compile(
        r'preferir\s+"([^"]+)"\s+(?:sobre|a|en vez de|en lugar de)\s+"([^"]+)"',
        re.IGNORECASE | re.UNICODE,
    )

    # 2b. Preferir sin comillas
    prefer_unquoted = re.compile(
        r"preferir\s+(\S+)\s+(?:sobre|a|en vez de|en lugar de)\s+(\S+)", re.IGNORECASE | re.UNICODE
    )

    # 3. Evitar / No usar
    avoid_pattern = re.compile(
        r'(?:evitar|no usar|prohibido|incorrecto)[:\s]+["\']?([^"\']+?)["\']?\s*$',
        re.IGNORECASE | re.UNICODE,
    )

    # 4. X (no Y) - formato común
    not_pattern = re.compile(
        r"([^(]+?)\s*\((?:no|nunca|incorrecto)[:\s]*([^)]+)\)", re.IGNORECASE | re.UNICODE
    )

    # Procesar línea por línea
    for line in rules_text.split("\n"):
        line = line.strip()

        # Ignorar líneas vacías, comentarios y headers
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Quitar bullet points
        if line.startswith("-") or line.startswith("*") or line.startswith("•"):
            line = line[1:].strip()

        # Intentar cada patrón
        rule = None

        # 1. Sustitución con comillas: "X" -> "Y"
        match = substitution_quoted.search(line)
        if match:
            old_text = match.group(1).strip()
            new_text = match.group(2).strip()

            if old_text and new_text and old_text != new_text:
                rule_counter += 1
                rule = EditorialRule(
                    id=f"user_rule_{rule_counter}",
                    name=f"{old_text} -> {new_text}",
                    description=f"Sustituir '{old_text}' por '{new_text}'",
                    rule_type=EditorialRuleType.WORD_REPLACEMENT,
                    category=EditorialRuleCategory.LEXICON,
                    pattern=_make_word_pattern(old_text),
                    replacement=new_text,
                    severity=GrammarSeverity.STYLE,
                )

        # 1b. Sustitución sin comillas: palabra -> otra
        if not rule:
            match = substitution_unquoted.search(line)
            if match:
                old_text = match.group(1).strip()
                new_text = match.group(2).strip()

                # Limpiar comillas residuales
                old_text = old_text.strip("\"'")
                new_text = new_text.strip("\"'")

                if old_text and new_text and old_text != new_text and len(old_text) > 1:
                    rule_counter += 1
                    rule = EditorialRule(
                        id=f"user_rule_{rule_counter}",
                        name=f"{old_text} -> {new_text}",
                        description=f"Sustituir '{old_text}' por '{new_text}'",
                        rule_type=EditorialRuleType.WORD_REPLACEMENT,
                        category=EditorialRuleCategory.LEXICON,
                        pattern=_make_word_pattern(old_text),
                        replacement=new_text,
                        severity=GrammarSeverity.STYLE,
                    )

        # 2. Preferir "X" sobre "Y" (con comillas)
        if not rule:
            match = prefer_pattern.search(line)
            if match:
                preferred = match.group(1).strip()
                avoid = match.group(2).strip()

                if preferred and avoid:
                    rule_counter += 1
                    rule = EditorialRule(
                        id=f"user_rule_{rule_counter}",
                        name=f"Preferir '{preferred}'",
                        description=f"Preferir '{preferred}' en lugar de '{avoid}'",
                        rule_type=EditorialRuleType.WORD_REPLACEMENT,
                        category=EditorialRuleCategory.LEXICON,
                        pattern=_make_word_pattern(avoid),
                        replacement=preferred,
                        severity=GrammarSeverity.STYLE,
                    )

        # 2b. Preferir sin comillas
        if not rule:
            match = prefer_unquoted.search(line)
            if match:
                preferred = match.group(1).strip()
                avoid = match.group(2).strip()

                if preferred and avoid and len(preferred) > 1:
                    rule_counter += 1
                    rule = EditorialRule(
                        id=f"user_rule_{rule_counter}",
                        name=f"Preferir '{preferred}'",
                        description=f"Preferir '{preferred}' en lugar de '{avoid}'",
                        rule_type=EditorialRuleType.WORD_REPLACEMENT,
                        category=EditorialRuleCategory.LEXICON,
                        pattern=_make_word_pattern(avoid),
                        replacement=preferred,
                        severity=GrammarSeverity.STYLE,
                    )

        # 3. Evitar X
        if not rule:
            match = avoid_pattern.search(line)
            if match:
                to_avoid = match.group(1).strip()

                if to_avoid:
                    rule_counter += 1
                    rule = EditorialRule(
                        id=f"user_rule_{rule_counter}",
                        name=f"Evitar '{to_avoid}'",
                        description=f"Evitar el uso de '{to_avoid}'",
                        rule_type=EditorialRuleType.WORD_REPLACEMENT,
                        category=EditorialRuleCategory.STYLE,
                        pattern=_make_word_pattern(to_avoid),
                        replacement=None,  # Solo marcar, no sugerir reemplazo
                        severity=GrammarSeverity.INFO,
                    )

        # 4. X (no Y)
        if not rule:
            match = not_pattern.search(line)
            if match:
                correct = match.group(1).strip()
                incorrect = match.group(2).strip()

                if correct and incorrect:
                    rule_counter += 1
                    rule = EditorialRule(
                        id=f"user_rule_{rule_counter}",
                        name=f"{correct} (no {incorrect})",
                        description=f"Usar '{correct}', no '{incorrect}'",
                        rule_type=EditorialRuleType.WORD_REPLACEMENT,
                        category=EditorialRuleCategory.LEXICON,
                        pattern=_make_word_pattern(incorrect),
                        replacement=correct,
                        severity=GrammarSeverity.STYLE,
                    )

        if rule:
            rules.append(rule)

    logger.info(f"Parseadas {len(rules)} reglas del usuario")
    return rules


def check_with_user_rules(
    text: str,
    user_rules_text: str,
    include_predefined: bool = True,
) -> EditorialReport:
    """
    Verifica un texto usando reglas definidas por el usuario.

    Args:
        text: Texto a analizar
        user_rules_text: Texto libre con las reglas del usuario
        include_predefined: Si incluir las reglas predefinidas

    Returns:
        EditorialReport con los problemas encontrados
    """
    # Parsear reglas del usuario
    user_rules = parse_user_rules(user_rules_text)

    # Crear checker
    if include_predefined:
        checker = get_editorial_checker()
        return checker.check(text, custom_rules=user_rules)
    else:
        # Solo reglas del usuario
        checker = EditorialRulesChecker(rules=user_rules)
        return checker.check(text)
