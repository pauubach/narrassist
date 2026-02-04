"""
Detector de variantes ortográficas según la RAE.

Identifica palabras que utilizan grafías no preferidas por la RAE
cuando existe una variante más recomendada. Por ejemplo:
- sicología → psicología
- obscuro → oscuro
- substancia → sustancia

La RAE suele aceptar ambas formas pero recomienda una sobre la otra.
Este detector alerta sobre el uso de variantes no preferidas.
"""

import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import OrthographicVariantsConfig
from ..types import CorrectionCategory

# ============================================================================
# VARIANTES ORTOGRÁFICAS RAE
# ============================================================================
# Formato: "variante_no_preferida": ("variante_preferida", "explicación")
# ============================================================================

# Simplificación de grupos consonánticos
SIMPLIFIED_CONSONANTS = {
    # ps- → s- (RAE prefiere la forma etimológica con ps-)
    "sicología": ("psicología", "La RAE prefiere la forma con ps-"),
    "sicológico": ("psicológico", "La RAE prefiere la forma con ps-"),
    "sicológica": ("psicológica", "La RAE prefiere la forma con ps-"),
    "sicólogo": ("psicólogo", "La RAE prefiere la forma con ps-"),
    "sicóloga": ("psicóloga", "La RAE prefiere la forma con ps-"),
    "siquiatra": ("psiquiatra", "La RAE prefiere la forma con ps-"),
    "siquiatría": ("psiquiatría", "La RAE prefiere la forma con ps-"),
    "siquiátrico": ("psiquiátrico", "La RAE prefiere la forma con ps-"),
    "seudo": ("pseudo", "La RAE prefiere la forma con ps-"),
    "seudónimo": ("pseudónimo", "La RAE prefiere la forma con ps-"),
    # obs- → os- (RAE prefiere la forma simplificada)
    "obscuro": ("oscuro", "La RAE prefiere la forma simplificada"),
    "obscura": ("oscura", "La RAE prefiere la forma simplificada"),
    "obscuridad": ("oscuridad", "La RAE prefiere la forma simplificada"),
    "obscurecer": ("oscurecer", "La RAE prefiere la forma simplificada"),
    # subs- → sus- (RAE prefiere la forma simplificada en algunos casos)
    "substancia": ("sustancia", "La RAE prefiere la forma simplificada"),
    "substancial": ("sustancial", "La RAE prefiere la forma simplificada"),
    "substancioso": ("sustancioso", "La RAE prefiere la forma simplificada"),
    "subscribir": ("suscribir", "La RAE prefiere la forma simplificada"),
    "subscripción": ("suscripción", "La RAE prefiere la forma simplificada"),
    "subscriptor": ("suscriptor", "La RAE prefiere la forma simplificada"),
    "substituir": ("sustituir", "La RAE prefiere la forma simplificada"),
    "substitución": ("sustitución", "La RAE prefiere la forma simplificada"),
    "substituto": ("sustituto", "La RAE prefiere la forma simplificada"),
    "substraer": ("sustraer", "La RAE prefiere la forma simplificada"),
    "substracción": ("sustracción", "La RAE prefiere la forma simplificada"),
    # trans- → tras- (ambas válidas, pero trans- es más formal)
    "trasporte": ("transporte", "La forma 'transporte' es más frecuente en el uso culto"),
    "trasportista": ("transportista", "La forma 'transportista' es más frecuente"),
    "traspasar": ("transpasar", "Ambas formas válidas; 'traspasar' es más común"),
    # gn- → n- (simplificación)
    "nomo": ("gnomo", "La RAE prefiere la forma etimológica con gn-"),
    "nóstico": ("gnóstico", "La RAE prefiere la forma etimológica con gn-"),
    # mn- → n- (simplificación)
    "nemotecnia": ("mnemotecnia", "La RAE prefiere la forma con mn-"),
    "nemotécnico": ("mnemotécnico", "La RAE prefiere la forma con mn-"),
    # pt- → t- (simplificación)
    "setiembre": ("septiembre", "La RAE prefiere la forma con pt-"),
    "sétimo": ("séptimo", "La RAE prefiere la forma con pt-"),
}

# Grafías con h- intermedia o inicial
H_VARIANTS = {
    # Formas con h- preferidas
    "armonía": ("harmonía", "La RAE acepta ambas, pero 'armonía' sin h es más común"),
    "armónico": ("harmónico", "La RAE acepta ambas, pero 'armónico' sin h es más común"),
    # Formas sin h- incorrectas
    "aora": ("ahora", "La forma correcta es con h"),
    "asta": ("hasta", "La forma correcta es con h (preposición)"),  # Ojo: asta = cuerno
    "aver": ("haber", "La forma correcta es con h"),
    "ay": ("hay", "La forma correcta es con h (verbo haber)"),  # Ojo: ay = interjección
    "echo": ("hecho", "Verificar: 'echo' (verbo echar) vs 'hecho' (verbo hacer)"),
    "ombre": ("hombre", "La forma correcta es con h"),
    "ora": ("hora", "La forma correcta es con h"),
}

# Grafías con b/v
BV_VARIANTS = {
    # Formas incorrectas comunes
    "haver": ("haber", "Se escribe con b"),
    "iva": ("iba", "Se escribe con b (verbo ir)"),
    "ivamos": ("íbamos", "Se escribe con b (verbo ir)"),
    "ivan": ("iban", "Se escribe con b (verbo ir)"),
    "tubo": ("tuvo", "Verificar: 'tubo' (cilindro) vs 'tuvo' (verbo tener)"),
    "balla": ("vaya", "Verificar: 'valla' (cerca) vs 'vaya' (verbo ir)"),
    "bello": ("vello", "Verificar: 'bello' (bonito) vs 'vello' (pelo)"),
    "bienes": ("vienes", "Verificar: 'bienes' (posesiones) vs 'vienes' (verbo venir)"),
    "botar": ("votar", "Verificar: 'botar' (saltar/tirar) vs 'votar' (sufragar)"),
    "grabar": ("gravar", "Verificar: 'grabar' (registrar) vs 'gravar' (imponer impuesto)"),
    "rebelar": ("revelar", "Verificar: 'rebelar' (sublevarse) vs 'revelar' (descubrir)"),
    "sabia": ("savia", "Verificar: 'sabia' (erudita) vs 'savia' (jugo vegetal)"),
}

# Grafías con ll/y
LLY_VARIANTS = {
    "arrollar": ("arrojar", "Verificar: 'arrollar' (enrollar/atropellar) vs 'arrojar' (lanzar)"),
    "callado": ("cayado", "Verificar: 'callado' (silencioso) vs 'cayado' (bastón)"),
    "halla": ("haya", "Verificar: 'halla' (encontrar) vs 'haya' (verbo haber/árbol)"),
    "malla": ("maya", "Verificar: 'malla' (red) vs 'maya' (civilización/planta)"),
    "pollo": ("poyo", "Verificar: 'pollo' (ave) vs 'poyo' (banco de piedra)"),
    "rallar": ("rayar", "Verificar: 'rallar' (desmenuzar) vs 'rayar' (hacer rayas)"),
    "valla": ("vaya", "Verificar: 'valla' (cerca) vs 'vaya' (verbo ir)"),
}

# Acentuación de palabras con doble forma válida
ACCENT_VARIANTS = {
    # Formas con tilde preferidas
    "periodo": ("período", "Ambas válidas; 'período' con tilde es más tradicional"),
    "olimpiada": ("olimpíada", "Ambas válidas; RAE prefiere sin tilde en uso actual"),
    "austriaco": ("austríaco", "Ambas válidas; forma esdrújula menos frecuente"),
    "cardiaco": ("cardíaco", "Ambas válidas; forma esdrújula es más técnica"),
    "policiaco": ("policíaco", "Ambas válidas; forma esdrújula menos frecuente"),
    "amoniaco": ("amoníaco", "Ambas válidas; forma esdrújula es más técnica"),
    "maniaco": ("maníaco", "Ambas válidas; forma esdrújula es más tradicional"),
    "zodiaco": ("zodíaco", "Ambas válidas; forma esdrújula menos frecuente"),
    "elegiaco": ("elegíaco", "Ambas válidas; forma esdrújula es más culta"),
    # Adverbios interrogativos
    "adonde": ("adónde", "Verificar: 'adonde' (relativo) vs 'adónde' (interrogativo)"),
    "como": ("cómo", "Verificar: 'como' (comparativo) vs 'cómo' (interrogativo)"),
    "cual": ("cuál", "Verificar: 'cual' (relativo) vs 'cuál' (interrogativo)"),
    "cuando": ("cuándo", "Verificar: 'cuando' (temporal) vs 'cuándo' (interrogativo)"),
    "cuanto": ("cuánto", "Verificar: 'cuanto' (relativo) vs 'cuánto' (interrogativo)"),
    "donde": ("dónde", "Verificar: 'donde' (relativo) vs 'dónde' (interrogativo)"),
    "que": ("qué", "Verificar: 'que' (relativo) vs 'qué' (interrogativo)"),
    "quien": ("quién", "Verificar: 'quien' (relativo) vs 'quién' (interrogativo)"),
}

# Extranjerismos adaptados
ADAPTED_LOANWORDS = {
    # Formas no adaptadas → adaptadas
    "ballet": ("balé", "La RAE propone la adaptación 'balé', aunque 'ballet' es muy usado"),
    "beige": ("beis", "La RAE propone la adaptación 'beis'"),
    "bungalow": ("bungaló", "La RAE propone la adaptación 'bungaló'"),
    "chalet": ("chalé", "La RAE propone la adaptación 'chalé'"),
    "commodity": ("comoditi", "La RAE propone usar 'materia prima' o 'bien básico'"),
    "copyright": ("derechos de autor", "La RAE recomienda 'derechos de autor'"),
    "dossier": ("dosier", "La RAE propone la adaptación 'dosier'"),
    "elite": ("élite", "La forma con tilde es la correcta en español"),
    "gay": ("gai", "La RAE propone la adaptación 'gai', aunque 'gay' es muy usado"),
    "gourmet": ("gurmet", "La RAE propone la adaptación 'gurmet' o 'gastrónomo'"),
    "jazz": ("yaz", "La RAE propone la adaptación 'yaz', aunque 'jazz' es estándar"),
    "jersey": ("yérsey", "La RAE propone la adaptación 'yérsey'"),
    "marketing": ("márquetin", "La RAE propone la adaptación o 'mercadotecnia'"),
    "parking": ("párquin", "La RAE propone la adaptación o 'aparcamiento'"),
    "pizza": ("piza", "La RAE acepta 'pizza' pero propone 'piza'"),
    "puzzle": ("puzle", "La RAE propone la adaptación 'puzle'"),
    "standard": ("estándar", "La forma adaptada al español es 'estándar'"),
    "stress": ("estrés", "La forma adaptada al español es 'estrés'"),
    "whisky": ("güisqui", "La RAE propone la adaptación 'güisqui'"),
}


class OrthographicVariantsDetector(BaseDetector):
    """
    Detector de variantes ortográficas según la RAE.

    Identifica palabras que usan grafías no preferidas por la RAE
    y sugiere las formas recomendadas.

    Categorías de detección:
    - Simplificación de grupos consonánticos (ps-, obs-, subs-, etc.)
    - Grafías con h
    - Confusiones b/v
    - Confusiones ll/y
    - Variantes de acentuación
    - Extranjerismos no adaptados
    """

    def __init__(self, config: Optional["OrthographicVariantsConfig"] = None):
        self.config = config or OrthographicVariantsConfig()

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.ORTHOGRAPHY

    @property
    def requires_spacy(self) -> bool:
        return False  # Funciona solo con regex

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta variantes ortográficas no preferidas.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (no utilizado)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Detectar cada categoría si está habilitada
        if self.config.check_consonant_groups:
            issues.extend(
                self._detect_variants(text, SIMPLIFIED_CONSONANTS, "consonant_group", chapter_index)
            )

        if self.config.check_h_variants:
            issues.extend(self._detect_variants(text, H_VARIANTS, "h_variant", chapter_index))

        if self.config.check_bv_confusion:
            issues.extend(self._detect_variants(text, BV_VARIANTS, "bv_confusion", chapter_index))

        if self.config.check_lly_confusion:
            issues.extend(self._detect_variants(text, LLY_VARIANTS, "lly_confusion", chapter_index))

        if self.config.check_accent_variants:
            issues.extend(
                self._detect_variants(text, ACCENT_VARIANTS, "accent_variant", chapter_index)
            )

        if self.config.check_loanword_adaptation:
            issues.extend(
                self._detect_variants(text, ADAPTED_LOANWORDS, "unadapted_loanword", chapter_index)
            )

        return issues

    def _detect_variants(
        self,
        text: str,
        variants_dict: dict[str, tuple[str, str]],
        issue_type: str,
        chapter_index: int | None,
    ) -> list[CorrectionIssue]:
        """
        Detecta variantes de un diccionario específico.

        Args:
            text: Texto a analizar
            variants_dict: Diccionario de variantes {palabra: (sugerencia, explicación)}
            issue_type: Tipo de issue para categorización
            chapter_index: Índice del capítulo

        Returns:
            Lista de CorrectionIssue
        """
        issues = []

        for variant, (preferred, explanation) in variants_dict.items():
            # Buscar la variante (case insensitive, palabra completa)
            pattern = re.compile(r"\b" + re.escape(variant) + r"\b", re.IGNORECASE)

            for match in pattern.finditer(text):
                original = match.group()
                start = match.start()
                end = match.end()

                # Preservar capitalización
                suggestion = self._preserve_case(original, preferred)

                # Determinar confianza según el tipo
                confidence = self._get_confidence(issue_type)

                # Crear mensaje de explicación
                full_explanation = f'"{original}" → "{suggestion}". {explanation}'

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=issue_type,
                        start_char=start,
                        end_char=end,
                        text=original,
                        explanation=full_explanation,
                        suggestion=suggestion,
                        confidence=confidence,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id=f"rae_variant_{variant}",
                        extra_data={
                            "variant": variant,
                            "preferred": preferred,
                            "variant_type": issue_type,
                        },
                    )
                )

        return issues

    def _preserve_case(self, original: str, replacement: str) -> str:
        """Preserva la capitalización del original en el reemplazo."""
        if original.isupper():
            return replacement.upper()
        elif original[0].isupper():
            return replacement.capitalize()
        return replacement

    def _get_confidence(self, issue_type: str) -> float:
        """Obtiene la confianza según el tipo de variante."""
        confidence_map = {
            "consonant_group": 0.95,  # Muy claras
            "h_variant": 0.70,  # Pueden ser homófonos válidos
            "bv_confusion": 0.65,  # Pueden ser homófonos válidos
            "lly_confusion": 0.60,  # Pueden ser homófonos válidos
            "accent_variant": 0.50,  # Depende del contexto
            "unadapted_loanword": 0.40,  # Informativo, no crítico
        }
        return confidence_map.get(issue_type, self.config.base_confidence)
