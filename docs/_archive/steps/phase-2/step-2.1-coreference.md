# STEP 2.1: Correferencia Básica

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 1.3 |

---

## Descripción

Resolver correferencias (quién es "él", "ella", "el doctor") usando Coreferee con heurísticas adicionales de género y número.

---

## Advertencias

⚠️ **ADVERTENCIA CRÍTICA**:

- F1 esperado: **~45-55%** (NO 65% como se creía inicialmente)
- Pro-drop hace **~40-50% de sujetos INVISIBLES**
- La **FUSIÓN MANUAL** (STEP 2.2) es **OBLIGATORIA**, no opcional

---

## Inputs

- Entidades NER extraídas
- Texto completo

---

## Outputs

- `src/narrative_assistant/nlp/coref.py`
- Cadenas de correferencia por entidad
- Heurísticas adicionales de género/número

---

## Implementación

```python
import spacy
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

@dataclass
class CoreferenceChain:
    """Una cadena de menciones que refieren a la misma entidad."""
    mentions: List[Tuple[int, int, str]]  # (start, end, text)
    main_mention: str  # La mención más informativa

class CoreferenceResolver:
    def __init__(self):
        self.nlp = spacy.load("es_core_news_lg")
        self.nlp.add_pipe('coreferee')

    def resolve(self, text: str) -> List[CoreferenceChain]:
        """Resuelve correferencias en el texto."""
        doc = self.nlp(text)
        chains = []

        if doc._.coref_chains:
            for chain in doc._.coref_chains:
                mentions = []
                for mention in chain:
                    token = doc[mention.root_index]
                    # Obtener el span completo de la mención
                    start = token.idx
                    end = token.idx + len(token.text)
                    mentions.append((start, end, token.text))

                if mentions:
                    # La mención principal es la más larga (nombre completo)
                    main = max(mentions, key=lambda m: len(m[2]))[2]
                    chains.append(CoreferenceChain(
                        mentions=mentions,
                        main_mention=main
                    ))

        return chains

    def merge_with_entities(
        self,
        entities: List['ExtractedEntity'],
        chains: List[CoreferenceChain]
    ) -> Dict[str, List['ExtractedEntity']]:
        """Agrupa entidades por cadena de correferencia."""
        # Mapear cada mención a su cadena
        mention_to_chain: Dict[str, int] = {}
        for i, chain in enumerate(chains):
            for _, _, text in chain.mentions:
                mention_to_chain[text.lower()] = i

        # Agrupar entidades
        grouped: Dict[int, List] = {}
        ungrouped: List = []

        for entity in entities:
            chain_id = mention_to_chain.get(entity.text.lower())
            if chain_id is not None:
                if chain_id not in grouped:
                    grouped[chain_id] = []
                grouped[chain_id].append(entity)
            else:
                ungrouped.append(entity)

        return {
            'grouped': grouped,
            'ungrouped': ungrouped
        }
```

---

## Criterio de DONE

```python
from narrative_assistant.nlp import CoreferenceResolver

resolver = CoreferenceResolver()
chains = resolver.resolve("Juan llegó tarde. Él estaba cansado.")

# "Juan" y "Él" deberían estar en la misma cadena
# PERO: esperar ~50% de errores
print(f"Cadenas encontradas: {len(chains)}")
for chain in chains:
    print(f"  - {chain.main_mention}: {[m[2] for m in chain.mentions]}")
```

---

## Siguiente

[STEP 2.2: Fusión de Entidades](./step-2.2-entity-fusion.md)
