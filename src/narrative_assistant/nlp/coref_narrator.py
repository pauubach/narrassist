"""
Mixin de coreference resolver: Narrator detection (LLM, patterns, gender inference, dialogue detection).

Extraido de coreference_resolver.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re

from .coreference_resolver import (
    NARRATOR_PATTERNS,
    CorefMethod,
    Gender,
    Mention,
)

logger = logging.getLogger(__name__)


class CorefNarratorMixin:
    """
    Mixin: Narrator detection (LLM, patterns, gender inference, dialogue detection).

    Requiere que la clase que hereda tenga:
    - self.config (CorefConfig)
    - self.methods (dict[CorefMethod, CorefMethodInterface])
    """

    def _detect_narrator(
        self,
        text: str,
        mentions: list[Mention],
    ) -> tuple[str, Gender] | None:
        """
        Detecta el nombre del narrador en primera persona usando LLM.

        El LLM analiza semánticamente el texto para identificar si hay un
        narrador en primera persona y cuál es su nombre/género.

        Returns:
            Tupla (nombre_narrador, género) o None si no se detecta
        """
        # Verificar si hay pronombres de primera persona (indicador de narrador)
        has_first_person = any(
            word in text.lower() for word in ["yo", " me ", " mi ", " mis ", "mí"]
        )

        if not has_first_person:
            return None

        # Usar LLM para detectar narrador semánticamente
        if hasattr(self, "_methods") and CorefMethod.LLM in self._methods:
            llm_method = self._methods[CorefMethod.LLM]
            if llm_method.client and llm_method.client.is_available:
                return self._detect_narrator_with_llm(text, llm_method.client)

        # Fallback a patrones si LLM no está disponible
        return self._detect_narrator_with_patterns(text, mentions)

    def _detect_narrator_with_llm(
        self,
        text: str,
        llm_client,
    ) -> tuple[str, Gender] | None:
        """Detecta el narrador usando LLM para análisis semántico."""
        from narrative_assistant.llm.sanitization import sanitize_for_prompt

        # Sanitizar texto del manuscrito antes de enviarlo al LLM (A-10)
        text_sample = sanitize_for_prompt(
            text[:2000] if len(text) > 2000 else text, max_length=2000
        )

        prompt = f"""Analiza el siguiente texto narrativo en español.

TEXTO:
{text_sample}

PREGUNTA: ¿El texto está narrado en primera persona? Si es así, ¿el narrador se presenta o identifica con un nombre propio en algún momento?

Responde en formato:
NARRADOR_PRIMERA_PERSONA: [sí/no]
NOMBRE_NARRADOR: [nombre si se identifica, o "desconocido"]
GENERO_NARRADOR: [masculino/femenino/desconocido]
EVIDENCIA: [frase donde se identifica, si existe]"""

        try:
            response = llm_client.complete(
                prompt=prompt,
                system="Eres un experto en análisis narrativo. Detecta narradores en primera persona con precisión. Busca patrones como 'me llamo X', 'soy X', 'mi nombre es X', o cualquier forma en que el narrador revele su identidad.",
                max_tokens=200,
                temperature=0.1,
            )

            if not response:
                return None

            # Parsear respuesta
            is_first_person = (
                "sí" in response.lower() and "NARRADOR_PRIMERA_PERSONA:" in response.upper()
            )

            if not is_first_person:
                return None

            # Extraer nombre
            name_match = re.search(
                r"NOMBRE_NARRADOR:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ]+)", response, re.IGNORECASE
            )
            if name_match:
                name = name_match.group(1).strip()
                if name.lower() in ("desconocido", "no", "ninguno", "sin"):
                    return None

                # Extraer género
                gender = Gender.NEUTRAL
                if "GENERO_NARRADOR:" in response.upper():
                    if "femenino" in response.lower():
                        gender = Gender.FEMININE
                    elif "masculino" in response.lower():
                        gender = Gender.MASCULINE

                logger.info(f"Narrador detectado por LLM: {name} ({gender.value})")
                return (name, gender)

        except Exception as e:
            logger.debug(f"Error detectando narrador con LLM: {e}")

        return None

    def _detect_narrator_with_patterns(
        self,
        text: str,
        mentions: list[Mention],
    ) -> tuple[str, Gender] | None:
        """Fallback: detecta narrador con patrones regex."""
        for pattern in NARRATOR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1)
                gender = self._infer_narrator_gender(text, name, mentions)
                logger.info(f"Narrador detectado por patrones: {name} ({gender.value})")
                return (name, gender)
        return None

    def _infer_narrator_gender(
        self,
        text: str,
        name: str,
        mentions: list[Mention],
    ) -> Gender:
        """
        Infiere el género del narrador basándose en contexto.

        Busca adjetivos y participios que concuerden con el narrador.
        """
        # Buscar patrones de género en el contexto del narrador
        # "soy una persona curiosa", "he sido tímido/tímida"
        fem_patterns = [
            r"\bsoy\s+(?:una|la)\b",
            r"\bhe\s+sido\s+\w+a\b",  # participios femeninos
            r"\bestoy\s+\w+a\b",  # adjetivos femeninos
            r"\bfui\s+\w+a\b",
            r"\bera\s+\w+a\b",
            r"\bme\s+siento\s+\w+a\b",
        ]
        masc_patterns = [
            r"\bsoy\s+(?:un|el)\b",
            r"\bhe\s+sido\s+\w+o\b",  # participios masculinos
            r"\bestoy\s+\w+o\b",  # adjetivos masculinos
            r"\bfui\s+\w+o\b",
            r"\bera\s+\w+o\b",
            r"\bme\s+siento\s+\w+o\b",
        ]

        fem_count = sum(1 for p in fem_patterns if re.search(p, text, re.IGNORECASE))
        masc_count = sum(1 for p in masc_patterns if re.search(p, text, re.IGNORECASE))

        if fem_count > masc_count:
            return Gender.FEMININE
        elif masc_count > fem_count:
            return Gender.MASCULINE

        # Intentar inferir del nombre
        if name.endswith("a"):
            return Gender.FEMININE
        elif name.endswith("o"):
            return Gender.MASCULINE

        return Gender.NEUTRAL

    def _is_in_dialogue(self, text: str, start_char: int, end_char: int) -> bool:
        """
        Determina si una posición está dentro de un diálogo.

        Detecta diálogos entre:
        - Guiones largos (—) o medios (–) o simples (-)
        - Comillas españolas («»)
        - Comillas inglesas ("")
        """
        # Buscar el inicio del contexto relevante (última línea/párrafo)
        line_start = text.rfind("\n", 0, start_char)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        line_text = (
            text[line_start : end_char + 50] if end_char + 50 < len(text) else text[line_start:]
        )

        # Posición relativa dentro de la línea
        rel_pos = start_char - line_start

        # Detectar si hay guion de diálogo al inicio
        line_stripped = line_text.lstrip()
        if line_stripped.startswith(("-", "—", "–")):
            # Está en línea de diálogo
            # Verificar si está después del cierre del diálogo (narrador)
            # Patrón: "- Texto del diálogo - dijo el narrador."
            # El segundo guion marca el fin del diálogo
            guion_positions = [i for i, c in enumerate(line_text) if c in "-—–"]
            if len(guion_positions) >= 2:
                # Hay apertura y cierre
                second_guion = guion_positions[1]
                if rel_pos > second_guion:
                    # Está después del cierre, es narración
                    return False
            return True

        # Detectar comillas
        # Contar comillas antes de la posición
        quotes_before = line_text[:rel_pos]
        open_spanish = quotes_before.count("«") - quotes_before.count("»")
        open_english = quotes_before.count('"') % 2  # Alternancia abrir/cerrar

        return bool(open_spanish > 0 or open_english > 0)
