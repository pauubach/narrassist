"""
Motor de inferencia de expectativas usando IA (LLM local).

Infiere comportamientos esperados/prohibidos y consecuencias
para relaciones entre entidades basándose en el contexto narrativo.
"""

import json
import logging

from .models import (
    EntityContext,
    EntityRelationship,
    InferredExpectations,
    RelationType,
)

logger = logging.getLogger(__name__)


class ExpectationInferenceEngine:
    """
    Motor de inferencia de expectativas usando IA.

    Puede usar:
    - LLM local (Ollama) para inferencia offline
    - Reglas como fallback si LLM no está disponible
    """

    def __init__(
        self,
        llm_client=None,
        use_llm: bool = True,
        model_name: str = "llama3.2",
    ):
        """
        Inicializa el motor de inferencia.

        Args:
            llm_client: Cliente LLM opcional (de narrative_assistant.llm)
            use_llm: Si usar LLM para inferencia
            model_name: Nombre del modelo a usar
        """
        self.llm_client = llm_client
        self.use_llm = use_llm and llm_client is not None
        self.model_name = model_name

        # Cargar cliente LLM si no se proporcionó
        if self.use_llm and self.llm_client is None:
            try:
                from ..llm import get_llm_client

                self.llm_client = get_llm_client()
                self.use_llm = self.llm_client is not None
            except Exception as e:
                logger.warning(f"No se pudo cargar cliente LLM: {e}")
                self.use_llm = False

    def infer_expectations(
        self,
        source_entity: EntityContext,
        target_entity: EntityContext,
        relationship: EntityRelationship,
    ) -> InferredExpectations:
        """
        Infiere expectativas de comportamiento para una relación.

        Args:
            source_entity: Contexto de la entidad origen
            target_entity: Contexto de la entidad destino
            relationship: Relación entre las entidades

        Returns:
            Expectativas inferidas
        """
        if self.use_llm and self.llm_client:
            try:
                return self._infer_with_llm(
                    source_entity,
                    target_entity,
                    relationship,
                )
            except Exception as e:
                logger.warning(f"Error en inferencia LLM: {e}, usando reglas")

        # Fallback a reglas
        return self._infer_with_rules(relationship)

    def _infer_with_llm(
        self,
        source: EntityContext,
        target: EntityContext,
        relationship: EntityRelationship,
    ) -> InferredExpectations:
        """Infiere expectativas usando LLM local."""
        prompt = self._build_prompt(source, target, relationship)

        response = self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
            temperature=0.3,
            max_tokens=500,
        )

        return self._parse_response(response.text)

    def _build_prompt(
        self,
        source: EntityContext,
        target: EntityContext,
        relationship: EntityRelationship,
    ) -> str:
        """Construye el prompt para inferencia."""
        # Formatear contexto de entidades
        source_context = self._format_entity_context(source)
        target_context = self._format_entity_context(target)

        return f"""Eres un experto en análisis narrativo. Analiza la siguiente relación entre personajes y genera expectativas de comportamiento.

CONTEXTO DE {source.entity_name.upper()}:
{source_context}

CONTEXTO DE {target.entity_name.upper()}:
{target_context}

RELACIÓN: {source.entity_name} [{relationship.relation_type.value}] {target.entity_name}
- Intensidad: {relationship.intensity:.1f}
- Bidireccional: {"Sí" if relationship.bidirectional else "No"}
- Evidencia: {relationship.evidence_texts[0] if relationship.evidence_texts else "N/A"}

INSTRUCCIONES:
Basándote en el contexto narrativo, responde:
1. ¿Qué comportamientos serían ESPERABLES de {source.entity_name} cuando se encuentra con/cerca de {target.entity_name}?
2. ¿Qué comportamientos serían CONTRADICTORIOS con esta relación?
3. ¿Debería haber consecuencias específicas de interacciones entre ellos?

IMPORTANTE: Responde SOLO en formato JSON válido:
{{
  "expected_behaviors": ["comportamiento1", "comportamiento2", "comportamiento3"],
  "forbidden_behaviors": ["comportamiento_prohibido1", "comportamiento_prohibido2"],
  "expected_consequences": ["consecuencia1"],
  "reasoning": "Breve explicación de por qué estos comportamientos son esperados/prohibidos"
}}

Responde directamente con el JSON, sin texto adicional."""

    def _format_entity_context(self, entity: EntityContext) -> str:
        """Formatea el contexto de una entidad para el prompt."""
        parts = []

        if entity.entity_type:
            parts.append(f"- Tipo: {entity.entity_type}")

        if entity.personality_traits:
            parts.append(f"- Rasgos: {', '.join(entity.personality_traits[:5])}")

        if entity.backstory_facts:
            parts.append(f"- Historia: {'; '.join(entity.backstory_facts[:3])}")

        if entity.mentions_summary:
            parts.append(f"- Resumen: {entity.mentions_summary[:200]}")

        if not parts:
            parts.append("- Sin información adicional")

        return "\n".join(parts)

    def _parse_response(self, response_text: str) -> InferredExpectations:
        """Parsea la respuesta del LLM."""
        try:
            # Intentar extraer JSON de la respuesta
            # Buscar el primer { y último }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)

                return InferredExpectations(
                    expected_behaviors=data.get("expected_behaviors", []),
                    forbidden_behaviors=data.get("forbidden_behaviors", []),
                    expected_consequences=data.get("expected_consequences", []),
                    confidence=0.75,
                    reasoning=data.get("reasoning", ""),
                    inference_source="local_llm",
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Error parseando respuesta LLM: {e}")

        # Si no se puede parsear, retornar expectativas vacías con baja confianza
        return InferredExpectations(
            expected_behaviors=[],
            forbidden_behaviors=[],
            expected_consequences=[],
            confidence=0.3,
            reasoning="No se pudo parsear la respuesta del LLM",
            inference_source="local_llm",
        )

    def _infer_with_rules(
        self,
        relationship: EntityRelationship,
    ) -> InferredExpectations:
        """Infiere expectativas usando reglas predefinidas."""
        expected = []
        forbidden = []
        consequences = []

        rt = relationship.relation_type

        # Reglas por tipo de relación
        rules = {
            RelationType.FRIEND: {
                "expected": ["ayuda", "apoya", "defiende", "comparte", "confía"],
                "forbidden": ["traiciona", "ataca sin razón", "ignora en peligro"],
                "consequences": [],
            },
            RelationType.ENEMY: {
                "expected": ["evita", "confronta", "desconfía", "critica"],
                "forbidden": ["ayuda desinteresadamente", "confía", "defiende"],
                "consequences": ["conflicto", "tensión"],
            },
            RelationType.LOVER: {
                "expected": ["protege", "apoya", "busca", "sacrifica por"],
                "forbidden": ["traiciona", "abandona sin explicación"],
                "consequences": [],
            },
            RelationType.FEARS: {
                "expected": ["evita", "huye", "tiembla", "palidece"],
                "forbidden": ["se acerca tranquilamente", "abraza", "disfruta"],
                "consequences": ["ansiedad", "parálisis", "pesadillas"],
            },
            RelationType.HATES: {
                "expected": ["evita", "insulta", "desprecia"],
                "forbidden": ["ayuda", "abraza", "besa"],
                "consequences": [],
            },
            RelationType.PARENT: {
                "expected": ["protege", "cuida", "aconseja", "preocupa"],
                "forbidden": ["abandona sin razón", "ignora peligro de hijo"],
                "consequences": [],
            },
            RelationType.MENTOR: {
                "expected": ["enseña", "guía", "corrige", "apoya"],
                "forbidden": ["abandona", "sabotea", "engaña"],
                "consequences": [],
            },
            RelationType.RIVAL: {
                "expected": ["compite", "desafía", "observa"],
                "forbidden": ["ayuda a ganar", "renuncia sin lucha"],
                "consequences": ["competencia"],
            },
            RelationType.AVOIDS: {
                "expected": ["rodea", "no menciona", "cambia de tema"],
                "forbidden": ["visita voluntariamente", "disfruta"],
                "consequences": [],
            },
            RelationType.CURSED_BY: {
                "expected": ["sufre", "busca liberarse"],
                "forbidden": [],
                "consequences": ["desgracia", "mala suerte", "dolor"],
            },
            RelationType.OWNS: {
                "expected": ["protege", "usa", "cuida"],
                "forbidden": ["destruye sin razón", "regala sin motivo"],
                "consequences": [],
            },
            RelationType.TRUSTS: {
                "expected": ["confía secretos", "sigue consejos", "defiende"],
                "forbidden": ["desconfía abiertamente", "traiciona"],
                "consequences": [],
            },
            RelationType.DISTRUSTS: {
                "expected": ["verifica", "duda", "mantiene distancia"],
                "forbidden": ["confía ciegamente", "comparte secretos"],
                "consequences": [],
            },
        }

        if rt in rules:
            expected = rules[rt]["expected"]
            forbidden = rules[rt]["forbidden"]
            consequences = rules[rt]["consequences"]

        # Ajustar por intensidad
        if relationship.intensity < 0.3:
            # Relación débil: reducir expectativas
            expected = expected[:2] if expected else []
            forbidden = forbidden[:1] if forbidden else []

        return InferredExpectations(
            expected_behaviors=expected,
            forbidden_behaviors=forbidden,
            expected_consequences=consequences,
            confidence=0.6,
            reasoning=f"Expectativas basadas en reglas para relación tipo {rt.value}",
            inference_source="rule_based",
        )

    def enrich_relationship(
        self,
        relationship: EntityRelationship,
        source_context: EntityContext | None = None,
        target_context: EntityContext | None = None,
    ) -> EntityRelationship:
        """
        Enriquece una relación con expectativas inferidas.

        Args:
            relationship: Relación a enriquecer
            source_context: Contexto opcional de la entidad origen
            target_context: Contexto opcional de la entidad destino

        Returns:
            Relación con expectativas añadidas
        """
        # Si ya tiene expectativas con alta confianza, no re-inferir
        if relationship.expectations and relationship.expectations.confidence >= 0.7:
            return relationship

        # Crear contextos básicos si no se proporcionaron
        if source_context is None:
            source_context = EntityContext(
                entity_id=relationship.source_entity_id,
                entity_name=relationship.source_entity_name,
            )

        if target_context is None:
            target_context = EntityContext(
                entity_id=relationship.target_entity_id,
                entity_name=relationship.target_entity_name,
            )

        # Inferir expectativas
        expectations = self.infer_expectations(
            source_context,
            target_context,
            relationship,
        )

        relationship.expectations = expectations
        return relationship


def get_expectation_inference_engine(
    use_llm: bool = True,
) -> ExpectationInferenceEngine:
    """
    Obtiene una instancia del motor de inferencia.

    Args:
        use_llm: Si intentar usar LLM

    Returns:
        Motor de inferencia configurado
    """
    return ExpectationInferenceEngine(use_llm=use_llm)
