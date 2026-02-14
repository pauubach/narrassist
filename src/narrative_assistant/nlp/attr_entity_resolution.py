"""
Mixin de resolución de entidades para extracción de atributos.

Implementa CESP (Cascading Extraction with Syntactic Priority):
scope gramatical, proximidad, género, sujeto elíptico, pronombres
posesivos, cláusulas relativas.

Extraído de attributes.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AttributeEntityResolutionMixin:
    """
    Mixin con métodos de resolución de entidades y validación de valores.

    Proporciona:
    - Validación de valores por tipo de atributo
    - Búsqueda de entidad más cercana (CESP)
    - Resolución de entidad desde tokens spaCy
    - Inferencia de categoría y clave de atributo

    Requiere que la clase que hereda tenga:
    - self._is_inside_dialogue() (de AttributeContextMixin)
    - self._is_inside_relative_clause() (de AttributeContextMixin)
    """

    def _validate_value(self, key, value: str) -> bool:
        """Valida que el valor sea apropiado para el tipo de atributo."""
        from .attributes import (
            BUILD_TYPES,
            COLORS,
            FACIAL_HAIR_DESCRIPTORS,
            HAIR_MODIFICATIONS,
            PERSONALITY_TRAITS,
            AttributeKey,
        )

        if not value:
            return False

        value_lower = value.lower()

        if key == AttributeKey.EYE_COLOR:
            return value_lower in COLORS

        if key == AttributeKey.HAIR_COLOR:
            # Solo colores válidos, NO tipos de cabello (largo/corto son hair_type)
            return value_lower in COLORS

        if key == AttributeKey.HAIR_MODIFICATION:
            # Modificaciones: teñido, natural, decolorado, mechas, etc.
            return (
                value_lower in HAIR_MODIFICATIONS
                or "teñid" in value_lower
                or "de bote" in value_lower
            )

        if key == AttributeKey.BUILD:
            return value_lower in BUILD_TYPES

        if key == AttributeKey.FACIAL_HAIR:
            return value_lower in FACIAL_HAIR_DESCRIPTORS

        if key == AttributeKey.PERSONALITY:
            return value_lower in PERSONALITY_TRAITS

        if key == AttributeKey.AGE:
            try:
                age = int(value)
                return 0 < age < 200
            except ValueError:
                return False

        if key == AttributeKey.APPARENT_AGE:
            # Numeric apparent age
            try:
                age = int(value)
                return 0 < age < 200
            except ValueError:
                pass
            # Descriptive age (joven, anciano, treintañero, etc.)
            age_descriptors = {
                "joven", "viejo", "vieja", "anciano", "anciana",
                "adolescente", "niño", "niña", "maduro", "madura", "mayor",
                "sexagenario", "sexagenaria", "septuagenario", "septuagenaria",
                "octogenario", "octogenaria", "nonagenario", "nonagenaria",
                "cincuentón", "cincuentona", "cuarentón", "cuarentona",
                "treintañero", "treintañera", "veinteañero", "veinteañera",
                "de mediana edad",
            }
            return value_lower in age_descriptors

        if key == AttributeKey.PROFESSION:
            # Excluir palabras genéricas que no son profesiones
            excluded = {
                "hombre",
                "mujer",
                "persona",
                "tipo",
                "chico",
                "chica",
                "joven",
                "viejo",
                "niño",
                "niña",
                "señor",
                "señora",
                "alto",
                "bajo",
                "grande",
                "pequeño",
                "bueno",
                "malo",
                "mejor",
                "peor",
                "primero",
                "primera",
                "último",
                "última",
            }
            return value_lower not in excluded and len(value) > 3

        # Para otros tipos, aceptar cualquier valor no vacío
        return len(value) > 1

    def _find_nearest_entity(
        self,
        text: str,
        position: int,
        entity_mentions: list[tuple] | None,
    ) -> str | None:
        """
        Encuentra la entidad más cercana a una posición.

        Útil para resolver "sus ojos" o pronombres como "ella".
        Resuelve correferencias usando contexto y prioriza entidades tipo PERSON.
        Maneja sujetos elípticos en español.

        Args:
            text: Texto completo
            position: Posición del atributo a resolver
            entity_mentions: Lista de (name, start, end, entity_type) o (name, start, end)

        Returns:
            Nombre de la entidad más probable o None
        """
        from .attributes import _is_location_entity, _is_person_entity, _normalize_entity_mentions

        if not entity_mentions:
            return None

        # Normalizar menciones al formato de 4 elementos
        normalized_mentions = _normalize_entity_mentions(entity_mentions)

        # ===== Resolución por scope gramatical (reemplaza ventana fija) =====
        # Usa ScopeResolver cacheado con dep parsing, RC filtering e identidad copulativa
        resolver = getattr(self, "_scope_resolver", None)
        if resolver is not None:
            try:
                scope_result = resolver.find_nearest_entity_by_scope(
                    position, normalized_mentions, prefer_subject=True
                )
                if scope_result is not None:
                    entity_name, confidence = scope_result
                    if confidence >= 0.5:
                        logger.debug(
                            f"Entidad resuelta por scope gramatical: '{entity_name}' "
                            f"(confianza={confidence:.2f})"
                        )
                        return entity_name  # type: ignore[no-any-return]
            except Exception as e:
                logger.debug(f"Scope resolution fallback: {e}")

        # ===== FALLBACK: Heurísticas mejoradas con ventana ampliada =====
        # Usar scope de oraciones en vez de chars fijos cuando sea posible,
        # con 1500 chars como safety limit (antes era 400)
        MAX_WINDOW = 1500
        context_start = max(0, position - MAX_WINDOW)
        context = text[context_start:position]

        # También extraer un poco adelante (20 chars) para detectar patrones que inician en position
        context_forward = text[position: position + 20]

        # Buscar todas las entidades antes de la posición con sus distancias
        candidates = []
        for name, start, end, entity_type in normalized_mentions:
            if end <= position:
                distance = position - end
                if distance < MAX_WINDOW:
                    candidates.append((name, start, end, distance, entity_type))

        if not candidates:
            return None

        # Clasificar entidades por tipo usando entity_type real del NER
        # También detectar si están dentro de cláusulas relativas
        person_candidates = []
        location_candidates = []

        for name, start, end, distance, entity_type in candidates:
            # Detectar si la entidad está dentro de una cláusula relativa
            in_relative_clause = self._is_inside_relative_clause(text, start, end, position)  # type: ignore[attr-defined]

            # Aplicar penalización por cláusula relativa
            relative_clause_penalty = 300 if in_relative_clause else 0
            adjusted_distance = distance + relative_clause_penalty

            # Si tenemos entity_type del NER, usarlo directamente
            if entity_type is not None:
                if _is_person_entity(entity_type):
                    person_candidates.append((name, start, end, adjusted_distance))
                elif _is_location_entity(entity_type):
                    location_candidates.append((name, start, end, adjusted_distance))
                # ORG y otros tipos se ignoran para atributos físicos
            else:
                # Fallback: heurística por nombre si no hay entity_type
                name_words = name.split()
                is_likely_person = (
                    len(name_words) <= 2
                    and not any(
                        word.lower() in ["parque", "del", "de", "la", "el", "retiro", "madrid"]
                        for word in name_words
                    )
                    and name[0].isupper()
                )

                if is_likely_person:
                    person_candidates.append((name, start, end, adjusted_distance))
                else:
                    location_candidates.append((name, start, end, adjusted_distance))

        # Buscar límites de oración (. ! ?) para entender contexto
        last_sentence_break = max(context.rfind("."), context.rfind("!"), context.rfind("?"))

        # Buscar pronombres o verbos en 3ª persona que indican sujeto elíptico
        immediate_context = context[-50:] if len(context) > 50 else context

        # IMPORTANTE: Separar pronombres de sujeto de artículos/determinantes
        has_subject_pronoun = bool(
            re.search(r"\b(ella|él)\b", immediate_context, re.IGNORECASE)
        )
        has_pronoun = has_subject_pronoun  # Solo pronombres de sujeto reales

        # Buscar verbos en 3ª persona tanto en contexto anterior como en el inicio del match
        combined_context = immediate_context + " " + context_forward
        has_3rd_person_verb = bool(
            re.search(
                r"\b(tenía|era|estaba|llevaba|parecía|mostraba|lucía|vestía|"
                r"miraba|miraban|caminaba|sonreía|hablaba|portaba|exhibía|"
                r"presentaba|aparentaba|revelaba|transmitía|observaba)\b",
                combined_context,
                re.IGNORECASE,
            )
        )

        # Detectar pronombres posesivos
        has_possessive = bool(
            re.search(
                r"\b(su|sus)\b", immediate_context + " " + context_forward, re.IGNORECASE
            )
        )

        # Detectar "la/lo/le" como pronombre OBJETO
        has_object_pronoun = bool(
            re.search(
                r"\b(la|lo|le)\s+(?:saludó|vio|miró|abrazó|besó|llamó|llevó|trajo|cogió|tomó|dejó|encontró|conoció|reconoció|observó|siguió|esperó|ayudó)",
                immediate_context,
                re.IGNORECASE,
            )
        )

        # Detectar pronombres de sujeto explícitos o indicadores de género
        subject_pronoun_match = re.search(
            r"\b(él|ella)\b", immediate_context + " " + context_forward, re.IGNORECASE
        )
        gender_noun_match = re.search(
            r"\b(hombre|mujer|chico|chica|señor|señora|niño|niña)\b",
            immediate_context + " " + context_forward,
            re.IGNORECASE,
        )

        # Caso -1: Pronombre de sujeto explícito o indicador de género
        if (subject_pronoun_match or gender_noun_match) and person_candidates:
            result = self._resolve_by_gender(
                subject_pronoun_match, gender_noun_match, person_candidates, MAX_WINDOW
            )
            if result is not None:
                return result

        # Caso 0: Pronombre posesivo refiriéndose al objeto
        if has_possessive and has_object_pronoun and person_candidates:
            result = self._resolve_possessive_object(
                immediate_context, context_forward, person_candidates
            )
            if result is not None:
                return result

        # Caso 1: Sujeto elíptico (verbo en 3ª persona sin sujeto)
        has_possessive_reference = has_possessive and not has_object_pronoun
        if (has_3rd_person_verb or has_possessive_reference) and not has_pronoun and last_sentence_break > 0:
            result = self._resolve_elliptic_subject(
                context, context_start, last_sentence_break, person_candidates
            )
            if result is not None:
                return result

        # Caso 2 y 3: Pronombre o búsqueda general
        if person_candidates:
            # Ordenar por distancia y tomar el más cercano
            person_candidates.sort(key=lambda x: x[3])
            return person_candidates[0][0]

        # Si no hay personas, penalizar lugares severamente
        all_candidates = location_candidates
        if all_candidates:
            scored_candidates = []
            for name, start, end, distance in all_candidates:
                # Penalizar lugares muy fuertemente (x5)
                score = distance * 5
                scored_candidates.append((name, score))

            scored_candidates.sort(key=lambda x: x[1])
            # Solo retornar lugar si está MUY cerca (distancia * 5 < 100)
            if scored_candidates[0][1] < 100:
                return scored_candidates[0][0]

        return None

    def _resolve_by_gender(
        self, subject_pronoun_match, gender_noun_match, person_candidates, max_window
    ) -> str | None:
        """Resuelve entidad por coincidencia de género (él/ella, hombre/mujer)."""
        # Determinar género
        is_feminine = False
        if subject_pronoun_match:
            pronoun = subject_pronoun_match.group(1).lower()
            is_feminine = pronoun == "ella"
        elif gender_noun_match:
            noun = gender_noun_match.group(1).lower()
            is_feminine = noun in ("mujer", "chica", "señora", "niña")

        # Nombres femeninos comunes en español
        feminine_names = {
            "maría", "ana", "elena", "laura", "carmen", "isabel", "rosa",
            "lucía", "marta", "paula", "sara", "andrea", "claudia", "sofía",
            "julia", "clara", "alba", "irene", "nuria", "eva", "raquel",
            "silvia", "cristina", "patricia", "mónica", "beatriz", "alicia",
        }
        # Nombres masculinos comunes en español
        masculine_names = {
            "juan", "pedro", "carlos", "antonio", "josé", "luis", "miguel",
            "francisco", "javier", "david", "daniel", "pablo", "alejandro",
            "sergio", "fernando", "alberto", "manuel", "rafael", "jorge",
            "mario", "andrés", "roberto", "enrique", "ricardo", "diego",
        }

        # Buscar candidatos con género coincidente
        gendered_candidates = []
        for name, start, end, distance in person_candidates:
            name_lower = name.lower()
            first_name = name_lower.split()[0] if name_lower else ""

            name_is_feminine = first_name in feminine_names or (
                first_name.endswith("a") and first_name not in masculine_names
            )
            name_is_masculine = first_name in masculine_names or (
                first_name.endswith("o") and first_name not in feminine_names
            )

            # Calcular ajuste de distancia por género
            gender_adjustment = 0
            if is_feminine and name_is_feminine or not is_feminine and name_is_masculine:
                gender_adjustment = -100  # Gran boost para coincidencia de género
            elif is_feminine and name_is_masculine or not is_feminine and name_is_feminine:
                gender_adjustment = 200  # Penalización fuerte por género incorrecto

            adjusted_distance = distance + gender_adjustment
            gendered_candidates.append((name, adjusted_distance, distance))

        if gendered_candidates:
            # Ordenar por distancia ajustada
            gendered_candidates.sort(key=lambda x: x[1])
            best_candidate = gendered_candidates[0]
            # Aceptar si la distancia ajustada es razonable
            if best_candidate[1] < max_window:
                logger.debug(
                    f"Género detectado ({'femenino' if is_feminine else 'masculino'}): "
                    f"seleccionando '{best_candidate[0]}' (dist={best_candidate[2]}, "
                    f"ajustada={best_candidate[1]})"
                )
                return best_candidate[0]  # type: ignore[no-any-return]

        return None

    def _resolve_possessive_object(
        self, immediate_context, context_forward, person_candidates
    ) -> str | None:
        """Resuelve entidad cuando hay pronombre posesivo + pronombre objeto."""
        search_text = immediate_context + " " + context_forward
        # Patrón mejorado: pronombre objeto + verbo ... posesivo
        obj_pronoun_match = re.search(
            r"\b(la|lo)\s+(?:saludó|vio|miró|abrazó|besó|llamó|llevó).*?\b(su|sus)\b",
            search_text,
            re.IGNORECASE | re.DOTALL,
        )

        if obj_pronoun_match:
            obj_pronoun = obj_pronoun_match.group(1).lower()
            is_feminine = obj_pronoun == "la"

            gendered_candidates = []
            for name, start, end, distance in person_candidates:
                name_lower = name.lower()
                gender_score = 0

                if is_feminine:
                    if name_lower.endswith("a") or name_lower in [
                        "maría", "ana", "elena", "laura", "carmen", "isabel",
                    ]:
                        gender_score = -50
                else:
                    if name_lower.endswith("o") or name_lower in [
                        "juan", "pedro", "carlos", "antonio", "josé", "luis",
                    ]:
                        gender_score = -50

                if is_feminine and not name_lower.endswith("a"):
                    gender_score = 100
                if not is_feminine and not name_lower.endswith("o"):
                    gender_score = 100

                adjusted_distance = distance + gender_score
                gendered_candidates.append((name, adjusted_distance))

            if gendered_candidates:
                gendered_candidates.sort(key=lambda x: x[1])
                if gendered_candidates[0][1] < 300:
                    return gendered_candidates[0][0]  # type: ignore[no-any-return]

            # Fallback: buscar segunda persona más cercana
            person_candidates_sorted = sorted(person_candidates, key=lambda x: x[3])
            if len(person_candidates_sorted) >= 2 and person_candidates_sorted[1][3] < 200:
                return person_candidates_sorted[1][0]  # type: ignore[no-any-return]

            if person_candidates_sorted:
                return person_candidates_sorted[0][0]  # type: ignore[no-any-return]

        return None

    def _resolve_elliptic_subject(
        self, context, context_start, last_sentence_break, person_candidates
    ) -> str | None:
        """Resuelve sujeto elíptico buscando en la oración anterior."""
        before_sentence_break = context[:last_sentence_break]

        before_break_candidates = []
        for name, start, end, distance in person_candidates:
            if start < (context_start + last_sentence_break):
                dist_from_break = (context_start + last_sentence_break) - end
                name_pos_in_context = start - context_start
                is_object = False

                if name_pos_in_context > 0:
                    prefix = context[max(0, name_pos_in_context - 3): name_pos_in_context]
                    if prefix.strip().endswith("a") or " a " in prefix:
                        is_object = True

                # Verificar patrones de complemento indirecto
                indirect_pattern = re.search(
                    rf"\b(le|les)\s+\w+\s+a\s+{re.escape(name)}\b",
                    before_sentence_break,
                    re.IGNORECASE,
                )
                if indirect_pattern:
                    is_object = True

                object_penalty = 150 if is_object else 0
                adjusted_dist = dist_from_break + object_penalty

                before_break_candidates.append(
                    (name, start, end, dist_from_break, adjusted_dist, is_object)
                )

        if before_break_candidates:
            before_break_candidates.sort(key=lambda x: x[4])
            best = before_break_candidates[0]
            logger.debug(
                f"Sujeto elíptico: seleccionando '{best[0]}' "
                f"(dist={best[3]}, ajustada={best[4]}, es_objeto={best[5]})"
            )
            return best[0]  # type: ignore[no-any-return]

        return None

    def _resolve_entity_from_token(
        self,
        token,
        mention_spans: dict,
        doc,
    ) -> str | None:
        """
        Resuelve un token a un nombre de entidad.

        Intenta:
        1. Buscar en menciones conocidas
        2. Usar el texto del token si es nombre propio
        3. Resolver pronombres a entidad cercana usando menciones conocidas

        Optimizado para precisión sobre velocidad.
        """
        # Si es nombre propio, usar directamente
        if token.pos_ == "PROPN":
            return token.text  # type: ignore[no-any-return]

        # Buscar en menciones conocidas por posición
        for (start, end), name in mention_spans.items():
            if start <= token.idx < end:
                return name  # type: ignore[no-any-return]

        # Si es pronombre, buscar entidad cercana con análisis exhaustivo
        if token.pos_ == "PRON":
            # 1. Buscar nombre propio más cercano ANTES del pronombre
            best_candidate = None
            best_distance = float("inf")

            for _i, prev_token in enumerate(doc):
                if prev_token.i >= token.i:
                    break  # Solo buscar antes del pronombre

                if prev_token.pos_ == "PROPN":
                    distance = token.i - prev_token.i

                    if prev_token.text not in ["Retiro", "Madrid"] and distance < best_distance:
                        is_location = False
                        if prev_token.i > 0:
                            prev_prev = doc[prev_token.i - 1]
                            if prev_prev.text.lower() in ["del", "de", "el", "la"]:
                                is_location = True

                        if not is_location:
                            best_candidate = prev_token.text
                            best_distance = distance

            if best_candidate and best_distance < 50:
                return best_candidate  # type: ignore[no-any-return]

            # 2. Si no encontramos nombre propio, buscar en mention_spans
            sorted_mentions = sorted(mention_spans.items(), key=lambda x: x[0][0], reverse=True)

            person_mentions = []
            for (start, end), name in sorted_mentions:
                if end < token.idx:
                    name_words = name.split()
                    is_likely_person = len(name_words) <= 2 and not any(
                        word.lower() in ["parque", "del", "de", "la", "el", "retiro"]
                        for word in name_words
                    )

                    if is_likely_person:
                        person_mentions.append((start, end, name, token.idx - end))

            if person_mentions:
                person_mentions.sort(key=lambda x: x[3])
                return person_mentions[0][2]  # type: ignore[no-any-return]

        return None

    # Colores que en uso copulativo ("era rubio") se refieren a pelo
    _HAIR_COLOR_ADJECTIVES = frozenset(
        {
            "rubio", "rubia", "rubios", "rubias",
            "moreno", "morena", "morenos", "morenas",
            "castaño", "castaña", "castaños", "castañas",
            "pelirrojo", "pelirroja", "pelirrojos", "pelirrojas",
            "canoso", "canosa", "canosos", "canosas",
        }
    )

    # Adjetivos de altura
    _HEIGHT_ADJECTIVES = frozenset(
        {
            "alto", "alta", "altos", "altas",
            "bajo", "baja", "bajos", "bajas",
        }
    )

    def _infer_category(self, value: str, token, entity_type: str | None = None):
        """Infiere la categoría del atributo basándose en el valor y POS."""
        from .attributes import (
            BUILD_TYPES,
            COLORS,
            PERSONALITY_TRAITS,
            AttributeCategory,
            _is_location_entity,
            _is_object_entity,
        )

        value_lower = value.lower()

        if _is_location_entity(entity_type):
            return AttributeCategory.GEOGRAPHIC

        if _is_object_entity(entity_type):
            # Para objetos, adjetivos suelen ser apariencia/estado material.
            if token and token.pos_ == "ADJ":
                return AttributeCategory.APPEARANCE
            return AttributeCategory.PHYSICAL

        # Físicos
        if value_lower in BUILD_TYPES or value_lower in COLORS:
            return AttributeCategory.PHYSICAL

        # Psicológicos
        if value_lower in PERSONALITY_TRAITS:
            return AttributeCategory.PSYCHOLOGICAL

        # Por defecto, usar PHYSICAL para adjetivos descriptivos
        if token and token.pos_ == "ADJ":
            return AttributeCategory.PHYSICAL

        return AttributeCategory.SOCIAL

    def _infer_key(self, value: str, token=None, entity_type: str | None = None):
        """
        Infiere la clave específica de un atributo extraído por dependency parsing.

        En español, adjetivos copulativos como "era moreno/rubio" se refieren
        a color de pelo. Adjetivos como "era alto" se refieren a altura.
        Adjetivos de constitución como "era delgado" a complexión.

        Args:
            value: Valor del atributo
            token: Token spaCy del atributo (opcional, para contexto)

        Returns:
            AttributeKey más probable
        """
        from .attributes import (
            BUILD_TYPES,
            COLORS,
            PERSONALITY_TRAITS,
            AttributeKey,
            _is_location_entity,
            _is_object_entity,
        )

        value_lower = value.lower()

        if _is_location_entity(entity_type):
            climate_terms = {
                "húmedo", "húmeda", "seco", "seca", "templado", "templada",
                "tropical", "frío", "fría", "cálido", "cálida", "árido", "árida",
                "lluvioso", "lluviosa",
            }
            if value_lower in climate_terms:
                return AttributeKey.CLIMATE

            terrain_terms = {
                "montañoso", "montañosa", "llano", "llana", "costero", "costera",
                "boscoso", "boscosa", "desértico", "desértica", "rocoso", "rocosa",
                "urbano", "urbana", "rural", "fértil",
            }
            if value_lower in terrain_terms:
                return AttributeKey.TERRAIN

            size_terms = {
                "enorme", "gigante", "vasto", "vasta", "amplio", "amplia",
                "grande", "mediano", "mediana", "pequeño", "pequeña",
                "diminuto", "diminuta",
            }
            if value_lower in size_terms:
                return AttributeKey.SIZE

            # Default útil para lugares: mejor LOCATION que OTHER.
            return AttributeKey.LOCATION

        if _is_object_entity(entity_type):
            material_terms = {
                "oro", "plata", "bronce", "hierro", "acero", "cobre", "madera",
                "cristal", "vidrio", "cuero", "hueso", "obsidiana", "piedra",
            }
            if value_lower in material_terms:
                return AttributeKey.MATERIAL

            if value_lower in COLORS:
                return AttributeKey.COLOR

            condition_terms = {
                "roto", "rota", "deteriorado", "deteriorada", "intacto", "intacta",
                "oxidado", "oxidada", "nuevo", "nueva", "viejo", "vieja",
                "destruido", "destruida", "dañado", "dañada", "gastado", "gastada",
            }
            if value_lower in condition_terms:
                return AttributeKey.CONDITION

            # Default útil para objetos: estado/condición.
            return AttributeKey.CONDITION

        # Color de pelo: "era rubio", "era moreno", "era castaño"
        if value_lower in self._HAIR_COLOR_ADJECTIVES:
            return AttributeKey.HAIR_COLOR

        # Altura: "era alto", "era baja"
        if value_lower in self._HEIGHT_ADJECTIVES:
            return AttributeKey.HEIGHT

        # Constitución: "era delgado", "era corpulento"
        if value_lower in BUILD_TYPES and value_lower not in self._HEIGHT_ADJECTIVES:
            return AttributeKey.BUILD

        # Personalidad: "era amable", "era valiente"
        if value_lower in PERSONALITY_TRAITS:
            return AttributeKey.PERSONALITY

        return AttributeKey.OTHER
