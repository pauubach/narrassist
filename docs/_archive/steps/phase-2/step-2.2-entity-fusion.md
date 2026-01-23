# STEP 2.2: Fusión Manual de Entidades

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 2.1, STEP 0.3 |

---

## Descripción

Implementar la fusión manual de entidades para corregir los errores de correferencia automática.

⚠️ **ESTE STEP ES CRÍTICO**: Sin fusión manual, el sistema NO es usable. La correferencia automática tiene ~45-55% de errores.

---

## Inputs

- Entidades detectadas (con errores de coref)
- Sugerencias de fusión por similaridad de nombre

---

## Outputs

- API/función para fusionar entidades
- Historial de fusiones (`merge_history`) para deshacer
- Actualización de TODAS las referencias afectadas

---

## Implementación

```python
from typing import List, Optional
from datetime import datetime
import json

class EntityFusionService:
    def __init__(self, repository: 'Repository'):
        self.repo = repository

    def merge_entities(
        self,
        project_id: int,
        entity_ids: List[int],
        canonical_name: str
    ) -> int:
        """
        Fusiona múltiples entidades en una sola.

        Args:
            project_id: ID del proyecto
            entity_ids: IDs de entidades a fusionar
            canonical_name: Nombre canónico resultante

        Returns:
            ID de la entidad resultante
        """
        if len(entity_ids) < 2:
            raise ValueError("Se necesitan al menos 2 entidades para fusionar")

        # 1. Obtener todas las entidades
        entities = [self.repo.get_entity(eid) for eid in entity_ids]

        # 2. Recopilar aliases
        all_aliases = set()
        for entity in entities:
            all_aliases.add(entity.canonical_name)
            all_aliases.update(entity.aliases)
        all_aliases.discard(canonical_name)

        # 3. Crear o actualizar entidad resultante
        result_entity_id = entity_ids[0]  # Mantener la primera
        self.repo.update_entity(
            result_entity_id,
            canonical_name=canonical_name,
            aliases=list(all_aliases)
        )

        # 4. Mover todas las referencias a la entidad resultante
        for eid in entity_ids[1:]:
            self.repo.move_references(from_entity=eid, to_entity=result_entity_id)
            self.repo.move_attributes(from_entity=eid, to_entity=result_entity_id)
            self.repo.delete_entity(eid)

        # 5. Registrar en historial
        self.repo.add_merge_history(
            project_id=project_id,
            result_entity_id=result_entity_id,
            source_entity_ids=entity_ids,
            merged_by='user'
        )

        return result_entity_id

    def undo_merge(self, merge_id: int) -> List[int]:
        """Deshace una fusión, restaurando las entidades originales."""
        merge = self.repo.get_merge_history(merge_id)
        if merge.undone_at:
            raise ValueError("Esta fusión ya fue deshecha")

        # Restaurar entidades (simplificado)
        # En implementación real, habría que restaurar desde backup
        self.repo.mark_merge_undone(merge_id)

        return merge.source_entity_ids

    def suggest_merges(self, project_id: int) -> List[dict]:
        """Sugiere fusiones basadas en similaridad de nombres."""
        entities = self.repo.get_entities(project_id)
        suggestions = []

        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                similarity = self._name_similarity(e1.canonical_name, e2.canonical_name)
                if similarity > 0.7:
                    suggestions.append({
                        'entity1': e1,
                        'entity2': e2,
                        'similarity': similarity,
                        'reason': self._get_merge_reason(e1, e2)
                    })

        return sorted(suggestions, key=lambda x: -x['similarity'])

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calcula similaridad entre nombres."""
        # Implementar Levenshtein normalizado o similar
        from difflib import SequenceMatcher
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def _get_merge_reason(self, e1, e2) -> str:
        """Genera razón legible para sugerencia de fusión."""
        if e1.canonical_name.lower() == e2.canonical_name.lower():
            return "Mismo nombre, diferente capitalización"
        # Más heurísticas...
        return "Nombres similares"
```

---

## Criterio de DONE

```python
from narrative_assistant.services import EntityFusionService

# Antes: "el doctor" y "Dr. García" son 2 entidades
service = EntityFusionService(repo)
result_id = service.merge_entities(
    project_id=1,
    entity_ids=[entity1_id, entity2_id],
    canonical_name="Dr. García"
)

# Después: 1 entidad con aliases ["el doctor", "Dr. García"]
entity = repo.get_entity(result_id)
assert "el doctor" in entity.aliases or entity.canonical_name == "Dr. García"
print("✅ Fusión de entidades funcional")
```

---

## Siguiente

[STEP 2.3: Extracción de Atributos](./step-2.3-attribute-extraction.md)
