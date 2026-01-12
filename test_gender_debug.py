# -*- coding: utf-8 -*-
"""
Debug para entender por qué "su cabello rubio" se asocia con Juan y no María.
"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Simular el contexto que ve _find_nearest_entity
text = """María era una mujer de ojos azules que vivía en Madrid. Tenía el cabello negro y largo.

Juan la conoció en el parque del Retiro. Él era alto y delgado.

María apareció en la fiesta con sus ojos verdes brillantes. Llevaba un vestido rojo.

Juan la saludó, sorprendido por su cabello rubio y corto."""

# Posición de "su cabello rubio" (aproximadamente)
position = text.find("su cabello rubio")
print(f"Posición de 'su cabello rubio': {position}")

# Menciones antes de esa posición
mentions = [
    ("María", 0, 5),
    ("Madrid", 49, 55),
    ("Juan", 96, 100),
    ("parque del Retiro", 118, 137),
    ("María", 179, 184),
    ("Juan", 251, 255),
]

# Contexto (400 chars antes)
context_start = max(0, position - 400)
context = text[context_start:position]

print(f"\nContexto (desde {context_start} hasta {position}):")
print("="*80)
print(context)
print("="*80)

# Buscar candidatos
candidates = []
for name, start, end in mentions:
    if end <= position:
        distance = position - end
        if distance < 400:
            candidates.append((name, start, end, distance))

print(f"\nCandidatos (entidades antes de posición {position}):")
for name, start, end, dist in candidates:
    print(f"  {name:20} posición {start:3}-{end:3}  distancia: {dist}")

# Filtrar personas
person_candidates = []
for name, start, end, distance in candidates:
    name_words = name.split()
    is_likely_person = (
        len(name_words) <= 2 and
        not any(word.lower() in ['parque', 'del', 'de', 'la', 'el', 'retiro', 'madrid'] for word in name_words) and
        name[0].isupper()
    )
    if is_likely_person:
        person_candidates.append((name, start, end, distance))

print(f"\nCandidatos tipo PERSON:")
for name, start, end, dist in person_candidates:
    print(f"  {name:20} distancia: {dist}")

# Buscar "la... su"
immediate_context = context[-50:] if len(context) > 50 else context
print(f"\nContexto inmediato (últimos 50 chars):")
print(f"'{immediate_context}'")

has_possessive = bool(re.search(r'\b(su|sus)\b', immediate_context, re.IGNORECASE))
has_object_pronoun = bool(re.search(r'\b(la|lo|le)\b', immediate_context, re.IGNORECASE))

print(f"\nhas_possessive: {has_possessive}")
print(f"has_object_pronoun: {has_object_pronoun}")

if has_possessive and has_object_pronoun:
    obj_match = re.search(r'\b(la|lo)\b.*?\b(su|sus)\b', immediate_context, re.IGNORECASE | re.DOTALL)
    if obj_match:
        print(f"\nMatch 'la/lo... su/sus': {obj_match.group()}")
        obj_pronoun = obj_match.group(1).lower()
        print(f"Pronombre objeto: {obj_pronoun}")
        is_feminine = (obj_pronoun == "la")
        print(f"Es femenino: {is_feminine}")

        # Aplicar lógica de género
        gendered_candidates = []
        for name, start, end, distance in person_candidates:
            name_lower = name.lower()
            gender_score = 0

            if is_feminine:
                if name_lower.endswith('a') or name_lower in ['maría']:
                    gender_score = -50
            else:
                if name_lower.endswith('o') or name_lower in ['juan']:
                    gender_score = -50

            # Penalizar no coincidencia
            if is_feminine and not name_lower.endswith('a'):
                gender_score = 100
            if not is_feminine and not name_lower.endswith('o'):
                gender_score = 100

            adjusted_distance = distance + gender_score
            gendered_candidates.append((name, distance, gender_score, adjusted_distance))

        print(f"\nCandidatos con score de género:")
        for name, dist, gender_score, adj_dist in gendered_candidates:
            print(f"  {name:20} dist={dist:3}  gender_score={gender_score:4}  adj_dist={adj_dist:4}")

        gendered_candidates.sort(key=lambda x: x[3])
        print(f"\nMejor candidato: {gendered_candidates[0][0]} (adj_dist={gendered_candidates[0][3]})")
