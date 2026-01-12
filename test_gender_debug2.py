# -*- coding: utf-8 -*-
"""
Debug actualizado con context_forward.
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
context_start = max(0, position - 400)
context = text[context_start:position]
context_forward = text[position:position + 20]

immediate_context = context[-50:] if len(context) > 50 else context

print(f"Posición: {position}")
print(f"\nContexto inmediato:")
print(f"'{immediate_context}'")
print(f"\nContexto forward (+20 chars):")
print(f"'{context_forward}'")

# Buscar con context_forward
combined = immediate_context + " " + context_forward
print(f"\nCombinado (immediate + forward):")
print(f"'{combined}'")

has_possessive = bool(re.search(r'\b(su|sus)\b', combined, re.IGNORECASE))
has_object_pronoun = bool(re.search(r'\b(la|lo|le)\b', immediate_context, re.IGNORECASE))

print(f"\nhas_possessive: {has_possessive}")
print(f"has_object_pronoun: {has_object_pronoun}")

if has_possessive and has_object_pronoun:
    # Buscar el patrón "la/lo ... su/sus"
    obj_match = re.search(r'\b(la|lo)\b.*?\b(su|sus)\b', combined, re.IGNORECASE | re.DOTALL)
    if obj_match:
        print(f"\nMatch encontrado: '{obj_match.group()}'")
        obj_pronoun = obj_match.group(1).lower()
        print(f"Pronombre objeto: {obj_pronoun}")
        print(f"Es femenino: {obj_pronoun == 'la'}")
    else:
        print("\nNO se encontró el patrón 'la/lo ... su/sus'")
