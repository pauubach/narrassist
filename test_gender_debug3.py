# -*- coding: utf-8 -*-
"""
Debug completo de la lógica de género.
"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

text = """María era una mujer de ojos azules que vivía en Madrid. Tenía el cabello negro y largo.

Juan la conoció en el parque del Retiro. Él era alto y delgado.

María apareció en la fiesta con sus ojos verdes brillantes. Llevaba un vestido rojo.

Juan la saludó, sorprendido por su cabello rubio y corto."""

position = text.find("su cabello rubio")

mentions = [
    ("María", 0, 5),
    ("Madrid", 49, 55),
    ("Juan", 96, 100),
    ("parque del Retiro", 118, 137),
    ("María", 179, 184),
    ("Juan", 251, 255),
]

# Candidatos
candidates = []
for name, start, end in mentions:
    if end <= position:
        distance = position - end
        if distance < 400:
            candidates.append((name, start, end, distance))

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

print("Person candidates:")
for name, start, end, dist in person_candidates:
    print(f"  {name:20} dist={dist}")

# Aplicar lógica de género
is_feminine = True  # "la" es femenino

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

print("\nGendered candidates (is_feminine=True):")
for name, dist, g_score, adj_dist in gendered_candidates:
    print(f"  {name:20} dist={dist:3}  gender_score={g_score:4}  adj_dist={adj_dist:4}")

gendered_candidates.sort(key=lambda x: x[3])
print(f"\nMejor candidato: {gendered_candidates[0][0]} (adj_dist={gendered_candidates[0][3]})")

if gendered_candidates[0][3] < 300:
    print(f"✓ Seleccionar: {gendered_candidates[0][0]}")
else:
    print(f"✗ adj_dist demasiado alto (>= 300)")
