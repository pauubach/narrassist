"""
Mixin de votación ponderada para extracción de atributos.

Combina resultados de múltiples métodos (LLM, embeddings, patterns,
dependency) mediante votación ponderada con deduplicación CESP
y resolución de conflictos.

Extraído de attributes.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AttributeVotingMixin:
    """
    Mixin con métodos de votación y post-procesamiento.

    Proporciona:
    - Votación ponderada multi-método
    - Deduplicación CESP (Cascading Extraction with Syntactic Priority)
    - Resolución de conflictos (un valor por entidad+key)

    Requiere que la clase que hereda tenga:
    - self.min_confidence (float)
    """

    def _vote_attributes(
        self,
        extractions: dict[str, list],
    ) -> list:
        """
        Combina atributos de múltiples métodos usando votación ponderada (weighted voting).

        Fórmula de confianza final:
        - Un método: conf_final = conf_original * (0.8 + method_weight * 0.5)
          - LLM (0.40): factor = 1.0 -> mantiene confianza
          - Patterns (0.15): factor = 0.875 -> reduce ligeramente
        - Múltiples métodos: conf_final = conf_promedio_ponderado + bonus_consenso
          - Promedio ponderado por peso de cada método
          - Bonus por consenso (más métodos = más confianza)

        Esto permite:
        - Aceptar atributos de un solo método si tienen confianza alta
        - Dar prioridad a atributos detectados por múltiples métodos
        - No filtrar arbitrariamente atributos válidos
        """
        from .attributes import METHOD_WEIGHTS, ExtractedAttribute

        # Agrupar atributos por (entidad, key, value_normalizado)
        grouped: dict[tuple, list[tuple[str, ExtractedAttribute]]] = {}

        for method, attrs in extractions.items():
            for attr in attrs:
                # Filtrar atributos sin entidad o valor
                if not attr.entity_name or not attr.value:
                    logger.debug(f"Atributo ignorado (sin entidad/valor): {attr}")
                    continue

                # Filtrar valores que son estados emocionales (no atributos físicos)
                emotional_states = {
                    "sorprendido",
                    "confundido",
                    "extrañado",
                    "asustado",
                    "feliz",
                    "triste",
                    "enfadado",
                    "nervioso",
                    "preocupado",
                    "emocionado",
                }
                if attr.value.lower() in emotional_states:
                    logger.debug(f"Atributo ignorado (estado emocional): {attr.value}")
                    continue

                # Filtrar entidades inválidas (pronombres, adverbios, colores, etc.)
                # Incluir versiones con y sin tilde para ser robusto
                invalid_entities = {
                    "también",
                    "tambien",
                    "este",
                    "esta",
                    "esto",
                    "ese",
                    "esa",
                    "eso",
                    "aquel",
                    "aquella",
                    "aquello",
                    "él",
                    "el",
                    "ella",
                    "ellos",
                    "ellas",
                    "uno",
                    "una",
                    "algo",
                    "alguien",
                    "nadie",
                    "nada",
                    "todo",
                    "todos",
                    "todas",
                    "otro",
                    "otra",
                    "otros",
                    "otras",
                    "mismo",
                    "misma",
                    "mismos",
                    "mismas",
                    "ambos",
                    "ambas",
                    "varios",
                    "varias",
                    "quien",
                    "quién",
                    "cual",
                    "cuál",
                    "cuales",
                    "cuáles",
                    # Colores y adjetivos que no son entidades
                    "negro",
                    "rubio",
                    "castaño",
                    "moreno",
                    "blanco",
                    "gris",
                    "canoso",
                    "alto",
                    "bajo",
                    "largo",
                    "corto",
                    "azules",
                    "verdes",
                    "marrones",
                }
                if attr.entity_name.lower() in invalid_entities:
                    logger.debug(f"Atributo ignorado (entidad inválida): {attr.entity_name}")
                    continue

                # Normalizar para comparación
                # Usar solo entity + key para agrupar valores similares
                key = (
                    attr.entity_name.lower(),
                    attr.key,
                    attr.value.lower().strip(),
                )
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append((method, attr))

        # Votar y generar atributos finales
        final_attributes: list[ExtractedAttribute] = []
        num_active_methods = len(extractions)

        # Normalizar pesos basándose en métodos ACTIVOS (que están en extractions)
        # Esto evita que los pesos entrenados para LLM penalicen otros métodos
        # cuando LLM no está habilitado.
        # Floor mínimo de 0.10 por método: evita que pesos entrenados sobreajustados
        # marginalicen métodos regex/dependency que detectan atributos fiablemente.
        MIN_METHOD_WEIGHT = 0.10
        active_methods = set(extractions.keys())
        active_weights = {
            m: max(MIN_METHOD_WEIGHT, METHOD_WEIGHTS.get(m, 0.15))
            for m in active_methods
        }
        total_active_weight = sum(active_weights.values())

        if total_active_weight > 0:
            normalized_weights = {m: w / total_active_weight for m, w in active_weights.items()}
        else:
            normalized_weights = {m: 1.0 / len(active_methods) for m in active_methods}

        logger.debug(
            f"Pesos normalizados para métodos activos {active_methods}: {normalized_weights}"
        )

        for _group_key, method_attrs in grouped.items():
            methods_with_attrs = list(method_attrs)
            unique_methods = {m for m, _ in methods_with_attrs}
            num_votes = len(unique_methods)

            if num_votes == 1:
                # Solo un método detectó este atributo
                method, attr = methods_with_attrs[0]
                # Usar peso normalizado para métodos activos
                method_weight = normalized_weights.get(method, 0.25)

                # Factor de escala: con pesos normalizados, un método único tiene peso ~0.5
                # si hay 2 métodos activos, o ~0.25 si hay 4 métodos activos.
                # Queremos ser más permisivos cuando solo hay pocos métodos activos.
                # Si hay N métodos activos, peso normalizado es ~1/N.
                # Factor de escala: 0.85 + weight * 0.15 para ser más permisivo
                scale_factor = 0.85 + (method_weight * 0.15)
                new_confidence = attr.confidence * scale_factor
                best_attr = attr

            else:
                # Múltiples métodos coinciden - weighted average + consensus bonus
                total_weight = 0.0
                weighted_conf_sum = 0.0
                best_attr = None
                best_conf = 0.0

                for method, attr in methods_with_attrs:
                    # Usar peso normalizado para métodos activos
                    weight = normalized_weights.get(method, 0.25)
                    total_weight += weight
                    weighted_conf_sum += attr.confidence * weight

                    if attr.confidence > best_conf:
                        best_conf = attr.confidence
                        best_attr = attr

                # Promedio ponderado
                avg_weighted_conf = weighted_conf_sum / total_weight if total_weight > 0 else 0.5

                # Bonus por consenso: más métodos = más confianza
                # 2 métodos: +0.05, 3 métodos: +0.10, 4 métodos: +0.15
                consensus_bonus = min(0.15, (num_votes - 1) * 0.05)

                new_confidence = min(1.0, avg_weighted_conf + consensus_bonus)

            new_confidence = min(1.0, max(0.0, new_confidence))

            # Solo incluir si supera umbral mínimo
            if new_confidence >= self.min_confidence and best_attr is not None:  # type: ignore[attr-defined]
                final_attr = ExtractedAttribute(
                    entity_name=best_attr.entity_name,
                    category=best_attr.category,
                    key=best_attr.key,
                    value=best_attr.value,
                    source_text=best_attr.source_text,
                    start_char=best_attr.start_char,
                    end_char=best_attr.end_char,
                    confidence=new_confidence,
                    is_negated=best_attr.is_negated,
                    is_metaphor=best_attr.is_metaphor,
                    chapter_id=best_attr.chapter_id,
                    assignment_source=best_attr.assignment_source,  # CESP: preservar fuente
                    sentence_idx=best_attr.sentence_idx,  # CESP: preservar índice
                )
                final_attributes.append(final_attr)

                logger.debug(
                    f"Atributo votado: {best_attr.entity_name}.{best_attr.key.value}="
                    f"{best_attr.value} (métodos: {unique_methods}, votos: {num_votes}/{num_active_methods}, "
                    f"conf: {best_attr.confidence:.2f} -> {new_confidence:.2f})"
                )

        return final_attributes

    def _deduplicate(self, attributes: list) -> list:
        """
        Elimina atributos duplicados usando CESP (Cascading Extraction with Syntactic Priority).

        CLAVE: Si el mismo atributo (tipo+valor+oración) está asignado a múltiples
        entidades, conservar SOLO el que tiene mayor prioridad de fuente de asignación.

        Prioridad de fuentes:
        1. GENITIVE ("de Pedro") - máxima prioridad
        2. EXPLICIT_SUBJECT (nsubj) - sujeto sintáctico
        3. LLM - comprensión semántica
        4. IMPLICIT_SUBJECT - sujeto tácito
        5. EMBEDDINGS - similitud semántica
        6. PROXIMITY - menor prioridad (causa de falsos positivos)

        Esto elimina falsos positivos como:
        - "ojos azules de Pedro" asignado a Juan por proximidad
        """
        from .attributes import AssignmentSource

        # PASO 1: Agrupar por (tipo, valor, oración) SIN considerar entidad
        # Esto detecta duplicados donde el mismo atributo fue asignado a múltiples entidades
        attr_groups: dict[tuple, list] = defaultdict(list)

        for attr in attributes:
            # Clave: (key, value_normalizado, sentence_idx o start_char//500)
            # Usamos start_char//500 como aproximación de oración si no hay sentence_idx
            sentence_key = attr.sentence_idx if attr.sentence_idx > 0 else (attr.start_char // 500)
            key = (attr.key, attr.value.lower().strip(), sentence_key)
            attr_groups[key].append(attr)

        # PASO 2: Para cada grupo, seleccionar el mejor por prioridad de fuente
        deduplicated: list = []

        # Prioridad de fuentes de asignación (mayor número = mayor prioridad)
        source_priority = {
            AssignmentSource.GENITIVE: 100,
            AssignmentSource.EXPLICIT_SUBJECT: 90,
            AssignmentSource.LLM: 80,
            AssignmentSource.IMPLICIT_SUBJECT: 50,
            AssignmentSource.EMBEDDINGS: 40,
            AssignmentSource.PROXIMITY: 10,
            None: 5,  # Sin fuente especificada
        }

        for key, group in attr_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Múltiples candidatos para el mismo atributo
                # Ordenar por: (prioridad_fuente, confianza)
                sorted_group = sorted(
                    group,
                    key=lambda a: (source_priority.get(a.assignment_source, 5), a.confidence),
                    reverse=True,
                )

                best = sorted_group[0]

                # Log si eliminamos falsos positivos
                eliminated = [
                    a for a in sorted_group[1:] if a.entity_name.lower() != best.entity_name.lower()
                ]
                for elim in eliminated:
                    logger.info(
                        f"[CESP] Eliminando falso positivo: {elim.key.value}='{elim.value}' "
                        f"asignado a '{elim.entity_name}' por {elim.assignment_source or 'desconocido'}. "
                        f"Correcto: '{best.entity_name}' por {best.assignment_source or 'mayor confianza'}"
                    )

                deduplicated.append(best)

        logger.debug(f"Deduplicación CESP: {len(attributes)} -> {len(deduplicated)} atributos")
        return deduplicated

    def _resolve_conflicts(self, attributes: list) -> list:
        """
        Resuelve conflictos donde una entidad tiene múltiples valores para el mismo atributo.

        Por ejemplo, si Juan tiene eye_color=verdes, eye_color=azules, eye_color=marrones,
        solo mantiene el de mayor confianza.

        Args:
            attributes: Lista de atributos (posiblemente con conflictos)

        Returns:
            Lista de atributos sin conflictos (un valor por entidad+key)
        """
        from .attributes import AttributeCategory, AttributeKey

        # Atributos que pueden tener múltiples valores legítimos
        MULTI_VALUE_KEYS = {
            AttributeKey.PERSONALITY,  # Puede tener múltiples rasgos
            AttributeKey.FEAR,  # Puede tener múltiples miedos
            AttributeKey.DESIRE,  # Puede tener múltiples deseos
            AttributeKey.DISTINCTIVE_FEATURE,  # Puede tener múltiples rasgos distintivos
            AttributeKey.RELATIONSHIP,  # Múltiples relaciones
            AttributeKey.OTHER,  # Categoría genérica
        }

        # Agrupar por (entidad, key) - sin el valor
        grouped: dict[tuple, list] = {}
        for attr in attributes:
            group_key = (attr.entity_name.lower(), attr.key)
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(attr)

        resolved: list = []

        for (entity, key), attrs in grouped.items():
            if len(attrs) == 1:
                # Sin conflicto
                resolved.append(attrs[0])
            elif key in MULTI_VALUE_KEYS:
                # Atributo que puede tener múltiples valores
                resolved.extend(attrs)
            elif attrs[0].category == AttributeCategory.PHYSICAL:
                # Atributo físico con valores distintos → posible inconsistencia
                # Preservar TODOS los valores para que attribute_consistency los detecte
                # (aplica a eye_color, hair_color, facial_hair, height, build, skin, etc.)
                unique_values = {a.value.lower().strip() for a in attrs}
                if len(unique_values) > 1:
                    logger.info(
                        f"Posible inconsistencia física para {entity}.{key.value}: "
                        f"valores distintos detectados: {[a.value for a in attrs]}"
                    )
                resolved.extend(attrs)
            else:
                # Conflicto: múltiples valores para atributo que debería ser único
                # Mantener solo el de mayor confianza
                best = max(attrs, key=lambda a: a.confidence)
                conflict_values = [a.value for a in attrs if a.value != best.value]
                if conflict_values:
                    logger.warning(
                        f"Conflicto de atributos para {entity}.{key.value}: "
                        f"manteniendo '{best.value}' (conf={best.confidence:.2f}), "
                        f"descartando: {conflict_values}"
                    )
                resolved.append(best)

        logger.debug(f"Resolución de conflictos: {len(attributes)} -> {len(resolved)} atributos")
        return resolved
