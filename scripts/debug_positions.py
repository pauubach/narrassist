# -*- coding: utf-8 -*-
"""Script para verificar posiciones de entidades en el texto."""

FULL_TEXT = """Capítulo 1: El Despertar

María Sánchez se despertó temprano aquella mañana de martes. Sus ojos azules brillaban con la luz del amanecer que entraba por la ventana. Tenía el cabello largo y negro, recogido en una trenza. Era una mujer alta, de aproximadamente treinta años.

Juan Pérez, su vecino, tocó a la puerta. Él era un hombre bajo y fornido, con barba espesa y ojos marrones. Trabajaba como carpintero en el centro de Madrid.

Capítulo 2: La Revelación

María apareció en la cafetería del barrio. Sus ojos verdes llamaron la atención de todos los presentes. Llevaba el cabello corto y rubio, completamente diferente a como la recordaban.

Juan entró poco después. Era un hombre muy alto, delgado como un junco. Sus ojos azules miraban con curiosidad a María.
"""

import re

# Buscar todas las menciones de entidades
entities_to_find = ["María Sánchez", "María", "Juan Pérez", "Juan", "Madrid"]

print("TEXTO COMPLETO:")
print("-" * 60)
# Print with position markers every 50 chars
for i in range(0, len(FULL_TEXT), 50):
    chunk = FULL_TEXT[i:i+50]
    print(f"[{i:4d}] {repr(chunk)}")
print("-" * 60)

print("\nPOSICIONES DE ENTIDADES:")
for entity in entities_to_find:
    for match in re.finditer(re.escape(entity), FULL_TEXT):
        print(f"  {entity!r}: start={match.start()}, end={match.end()}")
        # Show context
        start_ctx = max(0, match.start() - 20)
        end_ctx = min(len(FULL_TEXT), match.end() + 20)
        context = FULL_TEXT[start_ctx:end_ctx]
        print(f"    Context: ...{context!r}...")

# Find key sentences
print("\nPOSICIONES CLAVE:")
patterns = [
    "Llevaba el cabello corto",
    "Sus ojos azules brillaban",
    "Sus ojos verdes llamaron",
    "Sus ojos azules miraban",
]
for pattern in patterns:
    match = re.search(re.escape(pattern), FULL_TEXT)
    if match:
        print(f"  '{pattern}': position {match.start()}")
