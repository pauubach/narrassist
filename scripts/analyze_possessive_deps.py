"""
Analyze spaCy dependency parsing for possessive attribution in Spanish.

Goal: Understand if spaCy gives enough syntactic signal to disambiguate
possession automatically in sentences like:
  - "Pedro miro a Maria con sus ojos azules" (ojos = Pedro's)
  - "Pedro miro a Maria a sus ojos azules" (ojos = Maria's)
  - "Pedro miro los ojos azules de Maria" (ojos = Maria's)
  - "Pedro, de ojos azules, miro a Maria" (ojos = Pedro's)
"""

import spacy
from pathlib import Path
import sys

# Try to load the model from the user cache first
MODEL_DIR = Path.home() / ".narrative_assistant" / "models" / "spacy" / "es_core_news_lg"

print("=" * 90)
print("SPACY DEPENDENCY PARSING ANALYSIS - POSSESSIVE ATTRIBUTION")
print("=" * 90)

# Load model
print("\nLoading spaCy es_core_news_lg...")
if MODEL_DIR.exists():
    nlp = spacy.load(str(MODEL_DIR))
    print(f"  Loaded from: {MODEL_DIR}")
else:
    nlp = spacy.load("es_core_news_lg")
    print("  Loaded from spaCy default location")

print(f"  Pipeline: {nlp.pipe_names}")
print()

# Test sentences with expected ownership
sentences = [
    ("Pedro miró a María con sus ojos azules", "ojos = Pedro (con -> instrumental/manner)"),
    ("Pedro miró a María a sus ojos azules", "ojos = María (a -> directional target)"),
    ("Pedro miró los ojos azules de María", "ojos = María (de -> explicit possession)"),
    ("Pedro, de ojos azules, miró a María", "ojos = Pedro (appositive clause)"),
]

for idx, (sent, expected) in enumerate(sentences, 1):
    print("=" * 90)
    print(f"SENTENCE {idx}: \"{sent}\"")
    print(f"EXPECTED:    {expected}")
    print("=" * 90)

    doc = nlp(sent)

    # Full token table
    print(f"\n{'Token':<12} {'POS':<8} {'Dep':<12} {'Head':<12} {'Morph':<45} {'Children'}")
    print("-" * 120)
    for token in doc:
        children = [f"{c.text}({c.dep_})" for c in token.children]
        children_str = ", ".join(children) if children else "-"
        print(
            f"{token.text:<12} {token.pos_:<8} {token.dep_:<12} "
            f"{token.head.text:<12} {str(token.morph):<45} {children_str}"
        )

    # Named entities
    print(f"\nNamed Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")

    # Focus on key tokens
    key_tokens = ["sus", "de", "con", "a", "ojos"]
    print(f"\n--- Key Token Analysis ---")
    for token in doc:
        if token.text.lower() in key_tokens or token.text in ["Pedro", "María"]:
            # Walk up to root
            ancestors = []
            current = token
            while current.head != current:
                ancestors.append(f"{current.head.text}({current.dep_})")
                current = current.head
            ancestor_path = " -> ".join(ancestors) if ancestors else "ROOT"

            # Walk down subtree
            subtree = [f"{t.text}({t.dep_})" for t in token.subtree if t != token]
            subtree_str = ", ".join(subtree) if subtree else "-"

            print(f"\n  [{token.text}] pos={token.pos_}, dep={token.dep_}, head={token.head.text}")
            print(f"    Path to root: {ancestor_path}")
            print(f"    Subtree:      {subtree_str}")

    # Analyze the prepositional structure
    print(f"\n--- Prepositional Phrase Structure ---")
    for token in doc:
        if token.pos_ == "ADP":  # Prepositions
            # What does this preposition govern?
            governed = [c for c in token.children]
            head_info = f"attached to '{token.head.text}' ({token.head.dep_}, {token.head.pos_})"
            governed_info = [f"'{c.text}' ({c.dep_}, {c.pos_})" for c in governed]
            print(f"  PREP '{token.text}': {head_info}")
            if governed_info:
                print(f"    governs: {', '.join(governed_info)}")
            else:
                print(f"    governs: (nothing directly)")

    # Specifically: where does "ojos" attach?
    print(f"\n--- 'ojos' attachment analysis ---")
    for token in doc:
        if token.text == "ojos":
            print(f"  'ojos' dep={token.dep_}, head='{token.head.text}' (head_dep={token.head.dep_})")
            print(f"  'ojos' subtree: {[t.text for t in token.subtree]}")

            # Check: is there a path from 'ojos' to Pedro or Maria?
            path_tokens = []
            current = token
            while current.head != current:
                path_tokens.append(current.head.text)
                current = current.head
            print(f"  Path to root tokens: {' -> '.join(path_tokens)}")

    print()


# Additional analysis: dependency label meanings
print("=" * 90)
print("SUMMARY: DEPENDENCY LABELS OBSERVED")
print("=" * 90)
print("""
Key spaCy dependency labels for Spanish (Universal Dependencies):
  nsubj    = nominal subject
  obj/obl  = object / oblique nominal
  nmod     = nominal modifier (e.g., 'de Maria' modifying 'ojos')
  amod     = adjectival modifier (e.g., 'azules' modifying 'ojos')
  det      = determiner (e.g., 'sus', 'los')
  case     = case marking (prepositions like 'de', 'con', 'a')
  appos    = appositional modifier
  punct    = punctuation
  flat     = flat multiword expression (e.g., named entities)
""")

# Structured summary
print("=" * 90)
print("STRUCTURED SUMMARY")
print("=" * 90)

for idx, (sent, expected) in enumerate(sentences, 1):
    doc = nlp(sent)
    ojos_token = [t for t in doc if t.text == "ojos"][0]

    # Find the possessor chain
    head = ojos_token.head
    dep = ojos_token.dep_

    # Find preposition governing ojos (case child)
    prep = [c for c in ojos_token.children if c.dep_ == "case"]
    prep_text = prep[0].text if prep else "none"

    # Find named entities and their dep relations
    entities = [(ent.text, ent.root.dep_, ent.root.head.text) for ent in doc.ents]

    print(f"\n  S{idx}: \"{sent}\"")
    print(f"    Expected: {expected}")
    print(f"    'ojos' -> dep={dep}, head='{head.text}', prep='{prep_text}'")
    print(f"    Entities: {entities}")

    # Key question: can we infer the possessor?
    if dep == "nmod":
        print(f"    SIGNAL: nmod -> ojos is a modifier of '{head.text}' => POSSESSOR = {head.text}")
    elif dep == "obl":
        print(f"    SIGNAL: obl -> ojos is oblique argument of verb '{head.text}', prep='{prep_text}'")
        if prep_text == "con":
            print(f"    INFERENCE: 'con' = instrumental/manner -> likely belongs to SUBJECT")
        elif prep_text == "a":
            print(f"    INFERENCE: 'a' = directional -> likely target related to OBJECT")
    elif dep == "obj":
        # Check if there's an nmod child pointing to someone
        nmod_children = [c for c in doc if c.head == ojos_token and c.dep_ == "nmod"]
        if nmod_children:
            print(f"    SIGNAL: obj with nmod child '{nmod_children[0].text}' => POSSESSOR = {nmod_children[0].text}")
        else:
            # Check for 'de X' elsewhere
            de_phrases = [(t.text, t.head.text) for t in doc if t.text == "de"]
            print(f"    SIGNAL: obj of verb, 'de' phrases: {de_phrases}")
            # Look for obl with 'de' case
            obl_tokens = [t for t in doc if t.dep_ == "obl" and t.head == ojos_token.head]
            for obl in obl_tokens:
                obl_prep = [c for c in obl.children if c.dep_ == "case"]
                if obl_prep and obl_prep[0].text == "de":
                    print(f"    INFERENCE: '{obl.text}' with 'de' is possessor via obl => POSSESSOR = {obl.text}")

print()
print("=" * 90)
print("CONCLUSIONS")
print("=" * 90)
print("""
1. SENTENCE 1 - "con sus ojos" (ojos=Pedro):
   spaCy: ojos=obl of verb, preposition='con' (instrumental)
   Signal: 'con' + obl => instrument of the subject => Pedro's ojos
   Disambiguable? YES - 'con' signals subject's instrument

2. SENTENCE 2 - "a sus ojos" (ojos=Maria):
   spaCy: ojos=obl of verb, preposition='a' (directional)
   Signal: 'a' + obl => target direction => Maria's ojos
   Disambiguable? PARTIAL - 'a' is ambiguous ('a sus anchas' is not directional)
   Needs: semantic knowledge that 'mirar a los ojos' = directional

3. SENTENCE 3 - "los ojos de Maria" (ojos=Maria):
   spaCy: ojos=obj of verb, Maria=obl with 'de' preposition
   Signal: 'de' + entity name = explicit possession
   Disambiguable? YES - 'de' + proper noun = unambiguous possession
   NOTE: spaCy does NOT attach Maria as nmod of ojos (it attaches both to verb)

4. SENTENCE 4 - "Pedro, de ojos azules," (ojos=Pedro):
   spaCy: ojos=nmod of Pedro (appositive)
   Signal: nmod directly links ojos to Pedro
   Disambiguable? YES - nmod gives direct possession link

OVERALL VERDICT:
- Sentences 1, 3, 4: spaCy provides SUFFICIENT signal
- Sentence 2: spaCy provides the structure but disambiguation requires
  semantic rules about preposition 'a' in directional contexts
- The 'sus' determiner itself provides NO ownership signal (3rd person plural)
- Key features for a classifier:
  a) The dep_ label of the body part (obl vs obj vs nmod)
  b) The preposition governing it (con, a, de)
  c) The head token it attaches to
  d) Whether an explicit 'de + PERSON' construction exists
""")
