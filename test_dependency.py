# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from narrative_assistant.nlp.spacy_gpu import load_spacy_model

text = "Juan la conoció en el parque del Retiro. Él era alto y delgado."

nlp = load_spacy_model()
doc = nlp(text)

for sent in doc.sents:
    print(f"\nOración: {sent}")
    for token in sent:
        print(f"  {token.text:15} POS={token.pos_:6} DEP={token.dep_:10} HEAD={token.head.text}")

print("\n\nBuscando 'Él':")
for token in doc:
    if token.text == "Él":
        print(f"Token: {token.text}")
        print(f"POS: {token.pos_}")
        print(f"idx: {token.idx}")
        print(f"i: {token.i}")
