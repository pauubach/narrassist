"""
Inferencia de género multi-tier para nombres propios españoles.

Cascada de 3 niveles (de mayor a menor fiabilidad):
  Tier 1: spaCy morph (Gender=Fem/Masc) — si doc disponible
  Tier 2: Gazetteer de nombres conocidos — ~80 nombres consolidados
  Tier 3: Heurística por sufijo (-a → fem, -o → masc) — fallback

Módulo compartido (DRY): usado por coref_gender, scope_resolver,
attr_entity_resolution y pro_drop_scorer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier 2: Gazetteer de nombres (superconjunto consolidado de 3 módulos)
# ---------------------------------------------------------------------------

# Nombres femeninos comunes en español (INE top 100 + literarios + hispanoamérica)
FEMININE_NAMES: frozenset[str] = frozenset({
    # Top INE España
    "maría", "maria", "carmen", "ana", "laura", "marta", "elena",
    "sara", "paula", "lucía", "lucia", "sofía", "sofia", "isabel",
    "rosa", "pilar", "teresa", "julia", "clara", "alicia", "beatriz",
    "andrea", "cristina", "diana", "eva", "irene", "lorena", "nuria",
    "olga", "patricia", "raquel", "silvia", "susana", "verónica",
    "veronica", "virginia", "inés", "ines", "claudia", "alba",
    "mónica", "monica", "blanca", "cecilia",
    # Ampliación INE + frecuentes
    "margarita", "mercedes", "dolores", "josefa", "francisca",
    "catalina", "manuela", "antonia", "concepción", "encarnación",
    "amparo", "emilia", "aurora", "victoria", "esperanza",
    "magdalena", "remedios", "milagros", "inmaculada",
    "ángela", "angela", "rocío", "rocio", "lourdes", "yolanda",
    "natalia", "rebeca", "miriam", "sonia", "sandra",
    "leticia", "lara", "carla", "noelia", "esther", "ester",
    "helena", "valentina", "martina", "carlota", "jimena",
    "adriana", "nerea", "ainhoa", "aitana", "abril",
    "marina", "alma", "daniela", "valeria", "alejandra",
    # Hispanoamérica
    "fernanda", "camila", "luciana", "florencia", "constanza",
    "isidora", "macarena", "josefina", "paloma", "piedad",
    # Literarias clásicas
    "celestina", "bernarda", "dorotea", "dulcinea", "melibea",
    # Ingleses / internacionales frecuentes en narrativa
    "mary", "sarah", "jane", "elizabeth", "alice", "margaret",
    "emily", "charlotte", "emma", "olivia", "sophia", "hannah",
    "catherine", "katherine", "anne", "helen", "lucy", "grace",
    "rose", "rachel", "rebecca", "claire",
    # Franceses
    "marie", "jeanne", "sophie", "colette", "marguerite",
    # Italianos
    "giulia", "francesca", "chiara",
    # Alemanes
    "greta", "hanna", "lena", "elsa",
    # Portugueses
    "joana", "mariana", "carolina",
    # Catalanes / Vascos / Gallegos
    "meritxell", "montserrat", "neus", "gemma", "mireia",
    "iria", "uxía", "uxia", "ainara", "leire", "itziar",
    # Árabes frecuentes en narrativa
    "fátima", "fatima", "aisha", "leila", "nadia", "soraya",
    "amina", "yasmin", "zahra", "layla", "hanan",
    # Diminutivos femeninos frecuentes
    "mari", "lola", "pili", "conchi", "maite", "merche",
    "pepa", "loli", "cuca", "paca", "nena", "tere",
    "tina", "bea", "cris", "ele",
})

# Nombres masculinos comunes en español (INE top 100 + literarios + hispanoamérica)
MASCULINE_NAMES: frozenset[str] = frozenset({
    # Top INE España
    "juan", "pedro", "carlos", "miguel", "josé", "jose", "antonio",
    "manuel", "francisco", "david", "jorge", "pablo", "andrés",
    "andres", "luis", "javier", "sergio", "fernando", "alejandro",
    "alberto", "daniel", "diego", "enrique", "felipe", "gabriel",
    "héctor", "hector", "ignacio", "jaime", "mario", "rafael",
    "ramón", "ramon", "roberto", "víctor", "victor", "ricardo",
    "gonzalo", "rodrigo", "marcos", "santiago",
    # Ampliación INE + frecuentes
    "jesús", "jesus", "ángel", "tomás", "tomas", "emilio",
    "alfonso", "agustín", "agustin", "adrián", "adrian",
    "arturo", "borja", "álvaro", "alvaro", "iván", "ivan",
    "martín", "martin", "nicolás", "nicolas", "óscar", "oscar",
    "raúl", "raul", "rubén", "ruben", "salvador",
    "sebastián", "sebastian", "simón", "simon",
    "hugo", "mateo", "lucas", "leo", "bruno", "álex", "alex",
    "izan", "eric", "marc", "pol", "pau", "arnau", "iker",
    "aitor", "unai", "asier", "mikel", "gorka",
    # Hispanoamérica
    "matías", "matias", "joaquín", "joaquin",
    "facundo", "bautista", "benito", "ernesto", "germán", "german",
    # Literarios clásicos
    "sancho", "alonso", "lázaro", "lazaro", "quijote",
    # Ingleses / internacionales frecuentes en narrativa
    "john", "james", "william", "charles", "thomas", "edward",
    "henry", "george", "robert", "richard", "michael", "peter",
    "paul", "mark", "andrew", "stephen", "jack", "oliver",
    "harry", "sam", "ben", "adam", "noah", "max",
    # Franceses
    "jean", "pierre", "louis", "jacques", "françois", "francois",
    # Italianos
    "giovanni", "giuseppe", "marco", "luca", "matteo", "lorenzo",
    # Alemanes
    "hans", "karl", "otto", "fritz", "heinrich",
    # Portugueses
    "joão", "joao", "paulo", "tiago",
    # Rusos (frecuentes en literatura)
    "dimitri", "nikolai", "sergei", "boris", "vladimir",
    # Catalanes / Vascos / Gallegos
    "jordi", "oriol", "biel", "sergi",
    "eneko",
    "brais", "xoel", "xoán", "xoan",
    # Árabes frecuentes en narrativa
    "mohammed", "mohamed", "ahmed", "ali", "omar", "hassan",
    "youssef", "karim", "said", "mustafa", "rashid", "tariq",
    # Diminutivos masculinos frecuentes
    "pepe", "paco", "manolo", "kiko", "nico", "dani",
    "juanito", "carlitos", "miguelito", "toño", "nacho",
    "quique", "rafa", "fran", "santi", "ale",
    "chema", "lolo", "tito", "chule", "xule",
})

# Nombres ambiguos (no se puede determinar solo por el nombre)
AMBIGUOUS_NAMES: frozenset[str] = frozenset({
    "cruz", "trinidad", "guadalupe", "consuelo", "rosario",
    "ariel", "alexis", "dominique", "camille", "pat",
    "eden", "noel", "paris", "francis",
})


def infer_gender_from_name(name: str, doc=None) -> str | None:
    """
    Infiere género de un nombre propio español con cascada multi-tier.

    Tier 1: spaCy morph (si doc disponible) — busca el token del nombre
    Tier 2: Gazetteer de nombres conocidos (~80 nombres)
    Tier 3: Heurística por sufijo (-a/-o)

    Args:
        name: Nombre propio (puede ser compuesto: "María García")
        doc: Documento spaCy (opcional, para Tier 1)

    Returns:
        "Fem", "Masc", o None si no se puede determinar.
    """
    if not name:
        return None

    first = name.lower().split()[0]
    if not first:
        return None

    # Nombres ambiguos → siempre None
    if first in AMBIGUOUS_NAMES:
        return None

    # --- Tier 1: spaCy morph (más fiable) ---
    if doc is not None:
        gender = _infer_gender_from_doc(name, doc)
        if gender is not None:
            return gender

    # --- Tier 2: Gazetteer ---
    if first in FEMININE_NAMES:
        return "Fem"
    if first in MASCULINE_NAMES:
        return "Masc"

    # --- Tier 3: Heurística por sufijo ---
    if first.endswith("a") and len(first) > 2 and first not in MASCULINE_NAMES:
        return "Fem"
    if first.endswith("o") and len(first) > 2 and first not in FEMININE_NAMES:
        return "Masc"

    return None


def _infer_gender_from_doc(name: str, doc) -> str | None:
    """Tier 1: Busca el nombre en el doc spaCy y extrae Gender del morph."""
    name_lower = name.lower()
    first_lower = name_lower.split()[0] if name_lower else ""

    for ent in doc.ents:
        ent_first = ent.text.lower().split()[0] if ent.text else ""
        if ent_first == first_lower or ent.text.lower() == name_lower:
            # Extraer morph del primer token de la entidad
            token = ent.root if hasattr(ent, "root") else doc[ent.start]
            morph_str = str(token.morph)
            if "Gender=Fem" in morph_str:
                return "Fem"
            if "Gender=Masc" in morph_str:
                return "Masc"

    # Buscar por coincidencia de token individual
    for token in doc:
        if token.text.lower() == first_lower and token.pos_ == "PROPN":
            morph_str = str(token.morph)
            if "Gender=Fem" in morph_str:
                return "Fem"
            if "Gender=Masc" in morph_str:
                return "Masc"

    return None
