# -*- coding: utf-8 -*-
"""
Test para analizar estructura sintáctica con spaCy.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.spacy_gpu import load_spacy_model

text = "Juan la saludó, sorprendido por su cabello rubio y corto."

nlp = load_spacy_model()
doc = nlp(text)

print("="*80)
print("Análisis de dependencias")
print("="*80)
print(f"\nTexto: {text}\n")

for token in doc:
    print(f"{token.text:15} POS={token.pos_:6} DEP={token.dep_:12} HEAD={token.head.text:12} MORPH={token.morph}")

print("\n" + "="*80)
print("Análisis del pronombre 'la':")
print("="*80)

for token in doc:
    if token.text.lower() == "la":
        print(f"\nToken: {token.text}")
        print(f"  POS: {token.pos_}")
        print(f"  DEP: {token.dep_}")
        print(f"  HEAD: {token.head.text} ({token.head.pos_})")
        print(f"  Morph: {token.morph}")

        # Buscar si el verbo tiene un sujeto
        print(f"\n  Hijos del verbo '{token.head.text}':")
        for child in token.head.children:
            print(f"    - {child.text} ({child.dep_})")

print("\n" + "="*80)
print("Análisis del posesivo 'su':")
print("="*80)

for token in doc:
    if token.text.lower() == "su":
        print(f"\nToken: {token.text}")
        print(f"  POS: {token.pos_}")
        print(f"  DEP: {token.dep_}")
        print(f"  HEAD: {token.head.text} ({token.head.pos_})")
        print(f"  Morph: {token.morph}")
