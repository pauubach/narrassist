# -*- coding: utf-8 -*-
"""
Test de sugerencias de fusión.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.entities.fusion import get_fusion_service

project_id = 29  # El nuevo proyecto

fusion_service = get_fusion_service()
suggestions = fusion_service.suggest_merges(project_id, max_suggestions=50)

print(f"Sugerencias de fusión para proyecto {project_id}:")
print(f"Total: {len(suggestions)}")

for i, s in enumerate(suggestions, 1):
    print(f"\n{i}. Similarity: {s.similarity:.2f}")
    print(f"   Entity 1: '{s.entity1.canonical_name}' (ID: {s.entity1.id})")
    print(f"   Entity 2: '{s.entity2.canonical_name}' (ID: {s.entity2.id})")
    print(f"   Reason: {s.reason}")
