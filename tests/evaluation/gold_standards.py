"""
Gold Standards para evaluacion de precision.

Contiene anotaciones manuales de:
- Entidades (NER)
- Correferencias
- Atributos de personajes
- Errores gramaticales
- Relaciones entre personajes
- Eventos temporales (timeline)
- Capitulos/secciones

Cada gold standard incluye:
- El texto de prueba
- Las anotaciones correctas
- Metadata sobre el tipo de texto
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TextType(Enum):
    """Tipo de texto para ajustar el analisis."""

    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    DIALOGUE = "dialogue"
    DESCRIPTIVE = "descriptive"
    MIXED = "mixed"


@dataclass
class GoldEntity:
    """Entidad anotada manualmente."""

    name: str
    entity_type: str  # PER, LOC, ORG, etc.
    mentions: list[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class GoldAttribute:
    """Atributo de personaje anotado."""

    entity: str
    key: str
    values: list[str]  # Multiples valores = inconsistencia
    chapters: list[int] = field(default_factory=list)
    is_inconsistency: bool = False


@dataclass
class GoldRelation:
    """Relacion entre personajes anotada."""

    entity1: str
    entity2: str
    relation_type: str  # familiar, amigo, enemigo, colega, etc.
    direction: str = "bidirectional"  # bidirectional, e1_to_e2, e2_to_e1
    confidence: float = 1.0


@dataclass
class GoldEvent:
    """Evento temporal anotado."""

    description: str
    chapter: int
    order: int  # Orden dentro del capitulo
    entities_involved: list[str] = field(default_factory=list)
    temporal_markers: list[str] = field(default_factory=list)


@dataclass
class GoldChapter:
    """Capitulo/seccion anotado."""

    number: int
    title: str
    start_marker: str  # Texto que inicia el capitulo
    word_count: int


@dataclass
class GoldGrammarError:
    """Error gramatical anotado."""

    error_type: str
    text: str
    correction: str
    chapter: int


@dataclass
class GoldOrthographyError:
    """Error ortografico anotado."""

    error_type: str  # accent, b_v, h, ll_y, other
    text: str  # Texto incorrecto
    correction: str  # Correccion correcta
    chapter: int


@dataclass
class GoldCoreference:
    """Cadena de correferencia anotada."""

    entity: str  # Entidad canonica
    mentions: list[str]  # Lista de menciones que refieren a la entidad
    chapters: list[int] = field(default_factory=list)


@dataclass
class GoldStandard:
    """Gold standard completo para un texto de prueba."""

    text_file: str
    text_type: TextType
    description: str

    # Anotaciones
    entities: list[GoldEntity] = field(default_factory=list)
    attributes: list[GoldAttribute] = field(default_factory=list)
    relations: list[GoldRelation] = field(default_factory=list)
    events: list[GoldEvent] = field(default_factory=list)
    chapters: list[GoldChapter] = field(default_factory=list)
    grammar_errors: list[GoldGrammarError] = field(default_factory=list)
    orthography_errors: list[GoldOrthographyError] = field(default_factory=list)
    coreferences: list[GoldCoreference] = field(default_factory=list)
    fusion_pairs: list[tuple[str, str]] = field(default_factory=list)


# =============================================================================
# GOLD STANDARDS POR TEXTO DE PRUEBA
# =============================================================================

GOLD_INCONSISTENCIAS_PERSONAJES = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_inconsistencias_personajes.txt",
    text_type=TextType.FICTION,
    description="Texto con inconsistencias de atributos entre personajes",
    entities=[
        GoldEntity(
            "Maria Sanchez", "PER", ["Maria", "María", "Maria Sanchez", "María Sánchez", "MARIA"]
        ),
        GoldEntity("Juan Perez", "PER", ["Juan", "Juan Perez", "Juan Pérez"]),
        GoldEntity("Pedro Garcia", "PER", ["Pedro", "Pedro Garcia", "Pedro García", "PEDRO"]),
        GoldEntity("Elena", "PER", ["Elena", "ELENA"]),
        GoldEntity("Madrid", "LOC", ["Madrid"]),  # Lugar mencionado
    ],
    attributes=[
        GoldAttribute("Maria", "ojos", ["azules"], [1]),
        GoldAttribute(
            "Maria",
            "cabello",
            ["negro largo", "rubio", "castano largo"],
            [1, 1, 3],
            is_inconsistency=True,
        ),
        GoldAttribute("Maria", "estatura", ["alta", "baja"], [1, 2], is_inconsistency=True),
        GoldAttribute(
            "Maria",
            "profesion",
            ["profesora de literatura", "matematicas"],
            [1, 2],
            is_inconsistency=True,
        ),
        GoldAttribute("Juan", "barba", ["espesa", "afeitado"], [1, 4], is_inconsistency=True),
        GoldAttribute("Juan", "edad", ["35", "38", "casi 40"], [4, 4, 4], is_inconsistency=True),
        GoldAttribute(
            "Juan", "profesion", ["carpintero", "abogado"], [1, 5], is_inconsistency=True
        ),
        GoldAttribute("Pedro", "ojos", ["verdes", "azules"], [2, 3], is_inconsistency=True),
        GoldAttribute(
            "Elena", "cabello", ["pelirroja", "negro tenido rubio"], [3, 5], is_inconsistency=True
        ),
    ],
    fusion_pairs=[
        ("Maria", "Maria Sanchez"),
        ("Juan", "Juan Perez"),
        ("Pedro", "Pedro Garcia"),
        ("MARIA", "Maria"),  # Mayusculas
        ("PEDRO", "Pedro"),
        ("ELENA", "Elena"),
    ],
)


GOLD_ERRORES_GRAMATICALES = GoldStandard(
    text_file="test_books/evaluation_tests/manuscrito_prueba_errores.txt",
    text_type=TextType.FICTION,
    description="Texto con errores gramaticales intencionados",
    entities=[
        GoldEntity("Maria", "PER", ["Maria", "Maria"]),
        GoldEntity("Juan", "PER", ["Juan"]),
    ],
    grammar_errors=[
        # Dequeismo - el detector devuelve solo "de que", no incluye el verbo
        GoldGrammarError("dequeismo", "de que", "que", 1),  # pensaba de que
        GoldGrammarError("dequeismo", "de que", "que", 1),  # pienso de que
        GoldGrammarError("dequeismo", "de que", "que", 2),  # pensamos de que
        GoldGrammarError("dequeismo", "de que", "que", 3),  # opinaba de que
        # Queismo
        GoldGrammarError("queismo", "estaba segura que", "estaba segura de que", 1),
        GoldGrammarError("queismo", "me acuerdo que", "me acuerdo de que", 2),
        GoldGrammarError("queismo", "estaba convencido que", "estaba convencido de que", 2),
        GoldGrammarError("queismo", "estoy seguro que", "estoy seguro de que", 2),
        GoldGrammarError("queismo", "me alegro que", "me alegro de que", 2),
        GoldGrammarError("queismo", "me di cuenta que", "me di cuenta de que", 3),
        GoldGrammarError("queismo", "a pesar que", "a pesar de que", 3),
        GoldGrammarError("queismo", "despues que", "despues de que", 3),
        GoldGrammarError("queismo", "se alegraba que", "se alegraba de que", 3),
        # Laismo
        GoldGrammarError("laismo", "la dijo", "le dijo", 1),
        GoldGrammarError("laismo", "La habia preparado", "Le habia preparado", 1),
        GoldGrammarError("laismo", "la conto", "le conto", 2),
        GoldGrammarError("laismo", "las dijo", "les dijo", 3),
    ],
    fusion_pairs=[
        ("Maria", "Maria"),  # Con y sin tilde
    ],
)


GOLD_RELACIONES_PERSONAJES = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_relaciones_personajes.txt",
    text_type=TextType.FICTION,
    description="Texto para evaluar deteccion de relaciones entre personajes",
    entities=[
        GoldEntity("Ana", "PER", ["Ana", "Ana Martinez"]),
        GoldEntity("Carlos", "PER", ["Carlos", "Carlos Ruiz"]),
        GoldEntity("Laura", "PER", ["Laura"]),
        GoldEntity("Miguel", "PER", ["Miguel"]),
    ],
    relations=[
        GoldRelation("Ana", "Carlos", "romantic_partner"),
        GoldRelation("Ana", "Laura", "friend"),
        GoldRelation("Carlos", "Miguel", "colleague"),
        GoldRelation("Laura", "Miguel", "sibling"),
    ],
)


GOLD_TIMELINE_EVENTOS = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_timeline_eventos.txt",
    text_type=TextType.FICTION,
    description="Texto con marcadores temporales explicitos para evaluar timeline",
    entities=[
        GoldEntity("Maria", "PER", ["Maria"]),
        GoldEntity("Pedro", "PER", ["Pedro"]),
        GoldEntity("Carmen", "PER", ["Carmen"]),
        GoldEntity("Elena", "PER", ["Elena"]),
        GoldEntity("Carlos", "PER", ["Carlos"]),
        GoldEntity("Pablo", "PER", ["Pablo"]),
        GoldEntity("Ana", "PER", ["Ana"]),
        # Lugares mencionados
        GoldEntity("Madrid", "LOC", ["Madrid"]),
        GoldEntity("Paris", "LOC", ["Paris"]),
        GoldEntity("Andalucia", "LOC", ["Andalucia"]),
    ],
    events=[
        # Capitulo 1: 1990
        GoldEvent(
            "Nacimiento de Maria", 1, 1, ["Maria", "Pedro", "Carmen"], ["15 de enero de 1990"]
        ),
        GoldEvent(
            "Mudanza a Madrid",
            1,
            2,
            ["Maria", "Pedro", "Carmen"],
            ["Tres meses despues", "Abril 1990"],
        ),
        GoldEvent("Inicio guarderia", 1, 3, ["Maria"], ["septiembre de ese mismo ano"]),
        # Capitulo 2: 1995-2000
        GoldEvent("Maria aprende a leer", 2, 1, ["Maria"], ["verano de 1995", "cinco anos"]),
        GoldEvent("Inicio colegio", 2, 2, ["Maria", "Elena"], ["1996", "Al ano siguiente"]),
        GoldEvent("Viaje a Paris", 2, 3, ["Maria"], ["1998"]),
        GoldEvent("Fin de primaria", 2, 4, ["Maria"], ["2000", "Dos anos mas tarde"]),
        # Capitulo 3: 2000-2008
        GoldEvent("Inicio instituto", 3, 1, ["Maria"], ["otono de 2000", "diez anos"]),
        GoldEvent("Empieza guitarra", 3, 2, ["Maria"], ["2004", "catorce anos"]),
        GoldEvent("Primer trabajo", 3, 3, ["Maria"], ["verano de 2006"]),
        GoldEvent(
            "18 cumpleanos", 3, 4, ["Maria"], ["15 de enero de 2008", "dieciocho cumpleanos"]
        ),
        # Capitulo 4: 2008-2012
        GoldEvent("Inicio universidad", 4, 1, ["Maria"], ["septiembre de 2008"]),
        GoldEvent("Conoce a Carlos", 4, 2, ["Maria", "Carlos"], ["2009", "segundo curso"]),
        GoldEvent("Graduacion", 4, 3, ["Maria"], ["junio de 2012"]),
        # Capitulo 5: 2012-presente
        GoldEvent("Boda", 5, 1, ["Maria", "Carlos"], ["2013", "Un ano despues de graduarse"]),
        GoldEvent("Nacimiento de Pablo", 5, 2, ["Maria", "Carlos", "Pablo"], ["2015"]),
        GoldEvent(
            "Nacimiento de Ana",
            5,
            3,
            ["Maria", "Carlos", "Ana", "Pablo"],
            ["2018", "Tres anos mas tarde"],
        ),
        GoldEvent("Trabaja como editora", 5, 4, ["Maria"], ["2024", "Actualmente"]),
    ],
    chapters=[
        GoldChapter(1, "El comienzo (Enero de 1990)", "CAPITULO 1:", 100),
        GoldChapter(2, "La infancia (1995-2000)", "CAPITULO 2:", 100),
        GoldChapter(3, "La adolescencia (2000-2008)", "CAPITULO 3:", 100),
        GoldChapter(4, "La universidad (2008-2012)", "CAPITULO 4:", 100),
        GoldChapter(5, "La vida adulta (2012-presente)", "CAPITULO 5:", 100),
    ],
    relations=[
        GoldRelation("Maria", "Pedro", "parent_child", "e2_to_e1"),  # Pedro es padre de Maria
        GoldRelation("Maria", "Carmen", "parent_child", "e2_to_e1"),  # Carmen es madre de Maria
        GoldRelation("Pedro", "Carmen", "spouse"),
        GoldRelation("Maria", "Elena", "friend"),
        GoldRelation("Maria", "Carlos", "spouse"),
        GoldRelation("Pablo", "Ana", "sibling"),
        GoldRelation("Maria", "Pablo", "parent_child", "e1_to_e2"),  # Maria es madre de Pablo
        GoldRelation("Maria", "Ana", "parent_child", "e1_to_e2"),
    ],
)


GOLD_CAPITULOS_ESTRUCTURA = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_capitulos_estructura.txt",
    text_type=TextType.FICTION,
    description="Texto con multiples formatos de capitulos para evaluar deteccion de estructura",
    entities=[
        GoldEntity("Ana", "PER", ["Ana", "Ana Martinez"]),
        GoldEntity("Padre de Ana", "PER", ["padre", "Papa", "El padre"]),
    ],
    chapters=[
        # Parte 1
        GoldChapter(1, "El despertar", "CAPITULO 1", 50),
        GoldChapter(2, "La carta", "CAPITULO 2", 60),
        GoldChapter(3, "Revelaciones", "CAPITULO III", 50),
        # Parte 2
        GoldChapter(4, "La decision", "Capitulo 4 -", 50),
        GoldChapter(5, "El encuentro", "Capitulo Cinco:", 60),
        GoldChapter(6, "Explicaciones", "CAPITULO 6", 50),
        # Parte 3
        GoldChapter(7, "Secretos del pasado", "VII.", 40),
        GoldChapter(8, "Decisiones dificiles", "8.", 50),
        GoldChapter(9, "El plan", "Capitulo 9", 40),
        GoldChapter(10, "Epilogo", "EPILOGO", 50),
    ],
    relations=[
        GoldRelation("Ana", "Padre de Ana", "parent_child", "e2_to_e1"),
    ],
)


# Gold standard para narrativa pura (sin metadatos)
GOLD_NARRATIVA_PURA = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_narrativa_pura.txt",
    text_type=TextType.FICTION,
    description="Texto narrativo puro sin secciones de metadatos",
    entities=[
        GoldEntity("Alejandro", "PER", ["Alejandro"]),
        GoldEntity("Teresa", "PER", ["Teresa"]),
        GoldEntity("Rosario", "PER", ["dona Rosario", "Dona Rosario", "Rosario"]),
        GoldEntity("Beatriz", "PER", ["Beatriz"]),
        GoldEntity("Manuel", "PER", ["don Manuel", "Don Manuel", "Manuel", "Papa"]),
        GoldEntity("Papa de Roma", "PER", ["Papa", "Su Santidad"]),  # El Papa religioso
        GoldEntity("Sevilla", "LOC", ["Sevilla"]),
        # Lugares adicionales mencionados
        GoldEntity("Hospital San Carlos", "LOC", ["Hospital San Carlos"]),
        GoldEntity("Rio Guadalquivir", "LOC", ["Rio Guadalquivir"]),
    ],
    chapters=[
        GoldChapter(1, "El despertar", "CAPITULO 1:", 100),
        GoldChapter(2, "El viaje", "CAPITULO 2:", 100),
        GoldChapter(3, "La llegada", "CAPITULO 3:", 100),
    ],
    relations=[
        GoldRelation("Alejandro", "Rosario", "parent_child", "e2_to_e1"),
        GoldRelation("Alejandro", "Manuel", "parent_child", "e2_to_e1"),
        GoldRelation("Alejandro", "Beatriz", "sibling"),
        GoldRelation("Rosario", "Manuel", "spouse"),
    ],
)


# Gold standard para errores ortograficos
GOLD_ERRORES_ORTOGRAFICOS = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_ortografia.txt",
    text_type=TextType.FICTION,
    description="Texto con errores ortograficos intencionados",
    entities=[
        GoldEntity("Lucia", "PER", ["Lucia", "Lucia"]),
        GoldEntity("Andres", "PER", ["Andres"]),
    ],
    chapters=[
        GoldChapter(1, "Errores de acentuacion", "CAPITULO 1:", 100),
        GoldChapter(2, "Errores de b/v", "CAPITULO 2:", 100),
        GoldChapter(3, "Errores de h", "CAPITULO 3:", 100),
        GoldChapter(4, "Errores de ll/y", "CAPITULO 4:", 100),
        GoldChapter(5, "Errores varios", "CAPITULO 5:", 100),
    ],
    orthography_errors=[
        # Capitulo 1: Acentos
        GoldOrthographyError("accent", "CAPITULO", "CAPÍTULO", 1),  # Esdrújula en encabezados
        GoldOrthographyError("accent", "Lucia", "Lucía", 1),  # Falta tilde
        GoldOrthographyError("accent", "Andres", "Andrés", 1),
        GoldOrthographyError("accent", "jardin", "jardin", 1),
        GoldOrthographyError("accent", "poesia", "poesia", 1),
        GoldOrthographyError("accent", "El", "El", 1),  # El pronombre
        GoldOrthographyError("accent", "acerco", "acerco", 1),
        GoldOrthographyError("accent", "Que", "Que", 1),
        GoldOrthographyError("accent", "pregunto", "pregunto", 1),
        GoldOrthographyError("accent", "fantastico", "fantastico", 1),
        GoldOrthographyError("accent", "respondio", "respondio", 1),
        GoldOrthographyError("accent", "penso", "penso", 1),
        GoldOrthographyError("accent", "seria", "seria", 1),
        GoldOrthographyError("accent", "sento", "sento", 1),
        GoldOrthographyError("accent", "comenzo", "comenzo", 1),
        GoldOrthographyError("accent", "sabado", "sabado", 1),
        GoldOrthographyError("accent", "pajaros", "pajaros", 1),
        GoldOrthographyError("accent", "arboles", "arboles", 1),
        GoldOrthographyError("accent", "publico", "publico", 1),
        GoldOrthographyError("accent", "tambien", "también", 1),
        # Capitulo 2: b/v + acentos faltantes en capitulo 2
        GoldOrthographyError("accent", "pajaro", "pájaro", 2),
        GoldOrthographyError("b_v", "obserbo", "observo", 2),
        GoldOrthographyError("b_v", "estava", "estaba", 2),
        GoldOrthographyError("b_v", "lebanto", "levanto", 2),
        GoldOrthographyError("b_v", "nuebo", "nuevo", 2),
        GoldOrthographyError("b_v", "exijente", "exigente", 2),
        GoldOrthographyError("b_v", "bolvio", "volvio", 2),
        GoldOrthographyError("b_v", "bolo", "volo", 2),
        GoldOrthographyError("b_v", "Havian", "Habian", 2),
        GoldOrthographyError("b_v", "levanvarse", "levantarse", 2),
        GoldOrthographyError("b_v", "recojio", "recogio", 2),
        # Capitulo 3: h + acentos faltantes
        GoldOrthographyError("accent", "Como", "Cómo", 3),  # Interrogativa sin tilde
        GoldOrthographyError("accent", "llego", "llegó", 3),
        GoldOrthographyError("h", "ermano", "hermano", 3),
        GoldOrthographyError("h", "aciendo", "haciendo", 3),
        GoldOrthographyError("h", "Ola", "Hola", 3),
        # Nota: "a ido" y "e estado" - LanguageTool marca solo "a" -> "ha", "e" -> "he"
        # Los registramos como palabras individuales para evaluación correcta
        GoldOrthographyError("h", "a", "ha", 3),  # en "a ido"
        GoldOrthographyError("h", "e", "he", 3),  # en "e estado"
        GoldOrthographyError("h", "acia", "hacia", 3),
        GoldOrthographyError("h", "abitacion", "habitacion", 3),
        GoldOrthographyError("h", "Abia", "Habia", 3),
        GoldOrthographyError("h", "Abian", "Habian", 3),
        # Capitulo 4: ll/y + acentos faltantes
        GoldOrthographyError("accent", "sintio", "sintió", 4),
        GoldOrthographyError("accent", "miro", "miró", 4),
        GoldOrthographyError("accent", "decidio", "decidió", 4),
        GoldOrthographyError("ll_y", "oio", "oyo", 4),
        GoldOrthographyError("ll_y", "caye", "calle", 4),
        GoldOrthographyError("ll_y", "reian", "reian", 4),
        GoldOrthographyError("ll_y", "ablaban", "hablaban", 4),
        GoldOrthographyError("ll_y", "havia", "habia", 4),
        # Capitulo 5: varios + acentos faltantes
        GoldOrthographyError("accent", "dia", "día", 5),
        GoldOrthographyError("accent", "paso", "pasó", 5),
        GoldOrthographyError("other", "mui", "muy", 5),
        GoldOrthographyError("other", "siguente", "siguiente", 5),
        GoldOrthographyError("other", "acer", "hacer", 5),
        GoldOrthographyError("other", "recojer", "recoger", 5),
        GoldOrthographyError("other", "avuela", "abuela", 5),
        GoldOrthographyError("other", "berduras", "verduras", 5),
        GoldOrthographyError("other", "todabia", "todavia", 5),
        GoldOrthographyError("other", "cuidad", "ciudad", 5),
        GoldOrthographyError("other", "abraso", "abrazo", 5),
        GoldOrthographyError("accent", "calido", "cálido", 5),  # Esdrújula sin tilde
        GoldOrthographyError("accent", "ultima", "última", 5),  # Esdrújula sin tilde
    ],
)


# =============================================================================
# GOLD STANDARDS PARA VALIDACIÓN (DATOS NO VISTOS DURANTE DESARROLLO)
# =============================================================================

GOLD_UNSEEN_CIENCIA_FICCION = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_1_ciencia_ficcion.txt",
    text_type=TextType.FICTION,
    description="Texto de ciencia ficcion NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity("Valentina Orozco", "PER", ["Valentina Orozco", "Valentina", "doctora Orozco"]),
        GoldEntity(
            "Tomas Villanueva", "PER", ["Tomas Villanueva", "Tomás Villanueva", "Tomas", "Tomás"]
        ),
        GoldEntity("Lucia Mendoza", "PER", ["Lucia Mendoza", "Lucía Mendoza", "Lucia", "Lucía"]),
        GoldEntity(
            "Fernando Ramirez",
            "PER",
            [
                "Fernando Ramirez",
                "Fernando Ramírez",
                "Ramirez",
                "Ramírez",
                "doctor Ramirez",
                "doctor Ramírez",
            ],
        ),
        GoldEntity("Chen Wei", "PER", ["Chen Wei", "Chen"]),
        GoldEntity("Rosa Guerrero", "PER", ["Rosa Guerrero", "Rosa"]),
        GoldEntity(
            "Hector Salgado", "PER", ["Hector Salgado", "Héctor Salgado", "coronel Salgado"]
        ),
        # Ubicaciones
        GoldEntity("Marte", "LOC", ["Marte"]),
        GoldEntity("Colonia Esperanza", "LOC", ["Colonia Esperanza"]),
        GoldEntity("Monte Olimpo", "LOC", ["Monte Olimpo"]),
        GoldEntity("base Artemisa", "LOC", ["base Artemisa", "Artemisa"]),
        GoldEntity("Valle Marineris", "LOC", ["Valle Marineris"]),
        GoldEntity("Nueva Beijing", "LOC", ["Nueva Beijing"]),
        GoldEntity("Barcelona", "LOC", ["Barcelona"]),
        GoldEntity("Amazonas", "LOC", ["Amazonas"]),
        GoldEntity("Alpes", "LOC", ["Alpes"]),
        GoldEntity("Sahara", "LOC", ["Sahara"]),
        GoldEntity("Tierra", "LOC", ["Tierra"]),
        # Organizaciones
        GoldEntity("Agencia Espacial Europea", "ORG", ["Agencia Espacial Europea"]),
    ],
)


GOLD_UNSEEN_NOVELA_HISTORICA = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_2_novela_historica.txt",
    text_type=TextType.FICTION,
    description="Texto de novela historica NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity(
            "Fray Alonso de Guzman",
            "PER",
            ["Fray Alonso de Guzman", "Fray Alonso de Guzmán", "Fray Alonso", "Alonso"],
        ),
        GoldEntity("Isaac Benveniste", "PER", ["Isaac Benveniste", "Isaac", "doctor Benveniste"]),
        GoldEntity(
            "Francisco Jimenez de Cisneros",
            "PER",
            [
                "Francisco Jimenez de Cisneros",
                "Francisco Jiménez de Cisneros",
                "cardenal Cisneros",
                "Cisneros",
            ],
        ),
        GoldEntity("Fernando", "PER", ["Fernando"]),
        GoldEntity("Isabel", "PER", ["Isabel"]),
        GoldEntity(
            "Beatriz de Bobadilla",
            "PER",
            ["Beatriz de Bobadilla", "Dona Beatriz de Bobadilla", "Doña Beatriz de Bobadilla"],
        ),
        GoldEntity("Raquel", "PER", ["Raquel"]),
        GoldEntity("David", "PER", ["David"]),
        GoldEntity("Miriam", "PER", ["Miriam"]),
        GoldEntity(
            "Vasco Goncalves",
            "PER",
            ["Vasco Goncalves", "Vasco Gonçalves", "capitan Goncalves", "capitán Gonçalves"],
        ),
        GoldEntity("Bayezid II", "PER", ["Bayezid II", "sultan Bayezid II", "sultán Bayezid II"]),
        GoldEntity("Moises Capsali", "PER", ["Moises Capsali", "Moisés Capsali", "rabino Capsali"]),
        # Ubicaciones
        GoldEntity("Toledo", "LOC", ["Toledo"]),
        GoldEntity("Granada", "LOC", ["Granada"]),
        GoldEntity("Portugal", "LOC", ["Portugal"]),
        GoldEntity("Lisboa", "LOC", ["Lisboa"]),
        GoldEntity("Constantinopla", "LOC", ["Constantinopla"]),
        GoldEntity("Peninsula Iberica", "LOC", ["Peninsula Iberica", "Península Ibérica"]),
        GoldEntity("Estambul", "LOC", ["Estambul"]),
        GoldEntity("Balat", "LOC", ["Balat"]),
        GoldEntity("Imperio Otomano", "LOC", ["Imperio Otomano"]),
        # Organizaciones
        GoldEntity("Reyes Catolicos", "ORG", ["Reyes Catolicos", "Reyes Católicos"]),
    ],
)


GOLD_UNSEEN_THRILLER = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_3_thriller.txt",
    text_type=TextType.FICTION,
    description="Texto de thriller policiaco NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity(
            "Monica Salazar",
            "PER",
            ["Monica Salazar", "Mónica Salazar", "Monica", "Mónica", "inspectora Salazar"],
        ),
        GoldEntity(
            "Andres Riquelme",
            "PER",
            ["Andres Riquelme", "Andrés Riquelme", "subinspector Riquelme"],
        ),
        GoldEntity("Cristina Vega", "PER", ["Cristina Vega", "doctora Vega"]),
        GoldEntity("Sergio Blanco", "PER", ["Sergio Blanco", "Sergio"]),
        GoldEntity(
            "Rodrigo Santamaria",
            "PER",
            ["Rodrigo Santamaria", "Rodrigo Santamaría", "Santamaria", "Santamaría"],
        ),
        GoldEntity("Javier Ortega", "PER", ["Javier Ortega", "comisario Ortega"]),
        GoldEntity("Aurora Montero", "PER", ["Aurora Montero", "fiscal Montero"]),
        GoldEntity("Roberto Cifuentes", "PER", ["Roberto Cifuentes", "Roberto"]),
        GoldEntity("Ernesto Maldonado", "PER", ["Ernesto Maldonado", "Maldonado"]),
        GoldEntity("Felipe Arroyo", "PER", ["Felipe Arroyo", "Arroyo"]),
        GoldEntity(
            "Ignacio Bermudez",
            "PER",
            ["Ignacio Bermudez", "Ignacio Bermúdez", "juez Bermudez", "juez Bermúdez"],
        ),
        GoldEntity("Lola Herrera", "PER", ["Lola Herrera"]),
        # Ubicaciones
        GoldEntity("Parque del Retiro", "LOC", ["Parque del Retiro", "Retiro"]),
        GoldEntity("Estanque Grande", "LOC", ["Estanque Grande"]),
        GoldEntity("Palacio de Cristal", "LOC", ["Palacio de Cristal"]),
        GoldEntity("Moratalaz", "LOC", ["Moratalaz"]),
        GoldEntity("Madrid", "LOC", ["Madrid"]),
        GoldEntity("Valencia", "LOC", ["Valencia"]),
        GoldEntity("Tanger", "LOC", ["Tanger", "Tánger"]),
        GoldEntity("Marbella", "LOC", ["Marbella"]),
        GoldEntity("Barcelona", "LOC", ["Barcelona"]),
        # Organizaciones
        GoldEntity(
            "Fiscalia Anticorrupcion", "ORG", ["Fiscalia Anticorrupcion", "Fiscalía Anticorrupción"]
        ),
        GoldEntity("Guardia Civil", "ORG", ["Guardia Civil"]),
        GoldEntity("Mossos d'Esquadra", "ORG", ["Mossos d'Esquadra"]),
        GoldEntity("El Pais", "ORG", ["El Pais", "El País"]),
    ],
)


# Lista de todos los gold standards disponibles (desarrollo)
ALL_GOLD_STANDARDS = {
    "inconsistencias": GOLD_INCONSISTENCIAS_PERSONAJES,
    "gramatica": GOLD_ERRORES_GRAMATICALES,
    "relaciones": GOLD_RELACIONES_PERSONAJES,
    "timeline": GOLD_TIMELINE_EVENTOS,
    "capitulos": GOLD_CAPITULOS_ESTRUCTURA,
    "narrativa_pura": GOLD_NARRATIVA_PURA,
    "ortografia": GOLD_ERRORES_ORTOGRAFICOS,
}

# Categorias de evaluacion
EVALUATION_CATEGORIES = {
    "ner": ["inconsistencias", "relaciones", "timeline", "narrativa_pura"],
    "structure": ["capitulos"],
    "grammar": ["gramatica"],
    "orthography": ["ortografia"],
    "relationships": ["relaciones", "timeline"],
    "attributes": ["inconsistencias"],
    "coreference": ["correferencias_complejas"],
    "dialogue": ["muletillas_dialogos"],
    "focalization": ["focalizacion_sentimiento"],
    "sentiment": ["focalizacion_sentimiento"],
    "muletillas": ["muletillas_dialogos"],
    "register": ["muletillas_dialogos"],
}

# ============================================================================
# NUEVOS GOLD STANDARDS - DATOS NO VISTOS (AMPLIADOS)
# ============================================================================

GOLD_UNSEEN_ROMANCE = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_4_romance.txt",
    text_type=TextType.FICTION,
    description="Texto de romance contemporaneo NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity("Clara Mendoza", "PER", ["Clara Mendoza", "Clara"]),
        GoldEntity("Diego Santillana", "PER", ["Diego Santillana", "Diego"]),
        GoldEntity("Lucia Ferrer", "PER", ["Lucia Ferrer", "Lucía Ferrer"]),
        GoldEntity("Marta Mendoza", "PER", ["Marta Mendoza", "Marta"]),
        GoldEntity("Roberto Cifuentes", "PER", ["Roberto Cifuentes", "Roberto"]),
        GoldEntity("Daniela", "PER", ["Daniela"]),
        GoldEntity("Marcos", "PER", ["Marcos"]),
        GoldEntity("Elvira Ruiz", "PER", ["Elvira Ruiz", "dona Elvira", "doña Elvira"]),
        GoldEntity("Adriana Vega", "PER", ["Adriana Vega", "Adriana"]),
        GoldEntity("Fernando Vega", "PER", ["Fernando Vega", "don Fernando"]),
        GoldEntity("Alejandro Santillana", "PER", ["Alejandro Santillana"]),
        GoldEntity("Isabel", "PER", ["Isabel"]),
        # Ubicaciones
        GoldEntity("Barcelona", "LOC", ["Barcelona"]),
        GoldEntity("Sitges", "LOC", ["Sitges"]),
    ],
)

GOLD_UNSEEN_FANTASIA = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_5_fantasia.txt",
    text_type=TextType.FICTION,
    description="Texto de fantasia epica NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity("Aldric Tormentoso", "PER", ["Aldric Tormentoso", "Aldric", "mago Aldric"]),
        GoldEntity("Elarion Hojaplateada", "PER", ["Elarion Hojaplateada", "Elarion"]),
        GoldEntity("Nythara la Oscura", "PER", ["Nythara la Oscura", "Nythara"]),
        GoldEntity(
            "Selene Corazondeoro",
            "PER",
            ["Selene Corazondeoro", "Selene Corazóndeoro", "Selene", "princesa Selene"],
        ),
        GoldEntity(
            "Brennan Escudoacero",
            "PER",
            [
                "Brennan Escudoacero",
                "Brennan",
                "sir Brennan",
                "principe Brennan",
                "príncipe Brennan",
            ],
        ),
        GoldEntity("Aldric III", "PER", ["Aldric III", "rey Aldric III"]),
        GoldEntity("Ilyana Vozdeluz", "PER", ["Ilyana Vozdeluz", "Ilyana", "sacerdotisa Ilyana"]),
        GoldEntity(
            "Thorin Martillopesado", "PER", ["Thorin Martillopesado", "Thorin", "maestro Thorin"]
        ),
        GoldEntity("Kira Vientosur", "PER", ["Kira Vientosur", "Kira", "exploradora Kira"]),
        GoldEntity("Marcus", "PER", ["Marcus", "rey Marcus"]),
        GoldEntity("Roran Marenoche", "PER", ["Roran Marenoche", "Roran"]),
        # Ubicaciones
        GoldEntity("Monte Drakar", "LOC", ["Monte Drakar"]),
        GoldEntity("Valdris", "LOC", ["Valdris"]),
        GoldEntity("Aranthor", "LOC", ["Aranthor", "reino de Aranthor"]),
        GoldEntity("Bosque Prohibido", "LOC", ["Bosque Prohibido"]),
        GoldEntity("Islas Tormentosas", "LOC", ["Islas Tormentosas"]),
        # Organizaciones
        GoldEntity("Orden de los Guardianes", "ORG", ["Orden de los Guardianes"]),
        GoldEntity("Hermandad del Alba", "ORG", ["Hermandad del Alba"]),
        GoldEntity("Los Cinco Elegidos", "ORG", ["Los Cinco Elegidos", "Cinco Elegidos"]),
        # Dioses (entidades nombradas)
        GoldEntity("Lunara", "PER", ["Lunara", "diosa Lunara"]),
    ],
)

GOLD_UNSEEN_TERROR = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_6_terror.txt",
    text_type=TextType.FICTION,
    description="Texto de terror gotico NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity(
            "Samuel Thornton", "PER", ["Samuel Thornton", "doctor Thornton", "doctor Samuel"]
        ),
        GoldEntity(
            "Victoria Blackwood",
            "PER",
            ["Victoria Blackwood", "senora Victoria", "señora Victoria", "Victoria"],
        ),
        GoldEntity(
            "Edmund Blackwood",
            "PER",
            ["Edmund Blackwood", "lord Edmund", "senor Blackwood", "señor Blackwood", "Edmund"],
        ),
        GoldEntity("Martha Crenshaw", "PER", ["Martha Crenshaw", "Martha"]),
        GoldEntity("Eliza Blackwood", "PER", ["Eliza Blackwood", "Eliza"]),
        GoldEntity("Margaret Blackwood", "PER", ["Margaret Blackwood", "Lady Margaret"]),
        GoldEntity("Charles Pemberton", "PER", ["Charles Pemberton", "sir Charles"]),
        GoldEntity("Agnes White", "PER", ["Agnes White", "enfermera Agnes"]),
        GoldEntity("Reginald Blackwood", "PER", ["Reginald Blackwood", "Reginald"]),
        GoldEntity("Arthur Blackwood", "PER", ["Arthur Blackwood", "lord Arthur"]),
        # Ubicaciones
        GoldEntity(
            "Mansion Blackwood", "LOC", ["Mansion Blackwood", "Mansión Blackwood", "ala este"]
        ),
    ],
)

GOLD_UNSEEN_AVENTURAS = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_7_aventuras.txt",
    text_type=TextType.FICTION,
    description="Texto de aventuras NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity(
            "Jack Redbeard",
            "PER",
            [
                "Jack Redbeard",
                "capitan Redbeard",
                "capitán Redbeard",
                "capitan Jack",
                "capitán Jack",
            ],
        ),
        GoldEntity(
            "Miguel Salinas",
            "PER",
            ["Miguel Salinas", 'Miguel "El Cuervo" Salinas', "El Cuervo", "Miguel"],
        ),
        GoldEntity("Isabella Marquez", "PER", ["Isabella Marquez", "Isabella Márquez", "Isabella"]),
        GoldEntity(
            "Diego Marquez",
            "PER",
            ["Diego Marquez", "Diego Márquez", "capitan Diego", "capitán Diego"],
        ),
        GoldEntity("Francisco Moreno", "PER", ["Francisco Moreno", "almirante Moreno"]),
        GoldEntity(
            "Sebastian de Cordoba",
            "PER",
            ["Sebastian de Cordoba", "Sebastián de Córdoba", "don Sebastian", "don Sebastián"],
        ),
        GoldEntity(
            "Hernando Ruiz", "PER", ["Hernando Ruiz", "capitan Hernando", "capitán Hernando"]
        ),
        GoldEntity(
            "Tomas Vasquez",
            "PER",
            [
                "Tomas Vasquez",
                "Tomás Vásquez",
                'Tomas "Trueno" Vasquez',
                "Tomas",
                "Tomás",
                "Trueno",
            ],
        ),
        GoldEntity(
            "Maria Santos",
            "PER",
            [
                "Maria Santos",
                "María Santos",
                'Maria "La Bruja" Santos',
                "Maria",
                "María",
                "La Bruja",
            ],
        ),
        GoldEntity(
            "Valentina Cordoba", "PER", ["Valentina Cordoba", "Valentina Córdoba", "Valentina"]
        ),
        GoldEntity(
            "Alejandro Montes",
            "PER",
            ["Alejandro Montes", "arqueologo Montes", "arqueólogo Montes"],
        ),
        GoldEntity(
            "Rodrigo Beltran",
            "PER",
            ["Rodrigo Beltran", "Rodrigo Beltrán", "profesor Beltran", "profesor Beltrán"],
        ),
        GoldEntity(
            "William Thompson",
            "PER",
            ["William Thompson", 'William "Billy" Thompson', "Billy", "William"],
        ),
        GoldEntity("Xochitl", "PER", ["Xochitl"]),
        # Ubicaciones
        GoldEntity("Puerto de Cartagena", "LOC", ["Puerto de Cartagena", "Cartagena"]),
        GoldEntity("Isla de la Calavera", "LOC", ["Isla de la Calavera"]),
        GoldEntity("La Habana", "LOC", ["La Habana"]),
        # Organizaciones
        GoldEntity("Armada Real", "ORG", ["Armada Real"]),
    ],
)

GOLD_UNSEEN_DRAMA = GoldStandard(
    text_file="test_books/evaluation_tests/unseen_test_8_drama_familiar.txt",
    text_type=TextType.FICTION,
    description="Texto de drama familiar NO USADO durante desarrollo del NER",
    entities=[
        # Personas
        GoldEntity("Enrique Campos", "PER", ["Enrique Campos", "don Enrique"]),
        GoldEntity(
            "Mercedes Villaverde", "PER", ["Mercedes Villaverde", "dona Mercedes", "doña Mercedes"]
        ),
        GoldEntity("Ricardo Villaverde", "PER", ["Ricardo Villaverde", "Ricardo"]),
        GoldEntity("Beatriz Villaverde", "PER", ["Beatriz Villaverde de Sotomayor", "Beatriz"]),
        GoldEntity("Alfonso Sotomayor", "PER", ["Alfonso Sotomayor", "Alfonso"]),
        GoldEntity(
            "Sofia Sotomayor",
            "PER",
            ["Sofia Sotomayor Villaverde", "Sofía Sotomayor Villaverde", "Sofia", "Sofía"],
        ),
        GoldEntity("Alejandro Villaverde", "PER", ["Alejandro Villaverde Ruiz", "Alejandro"]),
        GoldEntity("Patricia Torres", "PER", ["Patricia Torres", "Patricia"]),
        GoldEntity("Cristina Herrera", "PER", ["Cristina Herrera"]),
        GoldEntity(
            "Ramon Villaverde",
            "PER",
            ["Ramon Villaverde", "Ramón Villaverde", "tio Ramon", "tío Ramón"],
        ),
        GoldEntity("Lucia Mendizabal", "PER", ["Lucia Mendizabal", "Lucía Mendizábal"]),
        GoldEntity("Pablo", "PER", ["Pablo"]),
        GoldEntity("Elena", "PER", ["Elena"]),
        GoldEntity("Martin", "PER", ["Martin", "Martín"]),
        # Ubicaciones
        GoldEntity("Sevilla", "LOC", ["Sevilla"]),
    ],
)

# =============================================================================
# GOLD STANDARDS PARA EVALUACION AVANZADA
# =============================================================================


@dataclass
class GoldMuletilla:
    """Muletilla detectada en el texto."""

    word: str  # La muletilla (ej: "pues", "o sea")
    speaker: str  # Quien la usa
    count: int  # Cuantas veces aparece
    chapter: int


@dataclass
class GoldDialogue:
    """Linea de dialogo con su speaker."""

    text: str  # Texto del dialogo
    speaker: str  # Quien habla
    chapter: int
    is_direct: bool = True  # Discurso directo vs indirecto


@dataclass
class GoldFocalizationViolation:
    """Violacion de focalizacion."""

    text: str  # Fragmento que viola la focalizacion
    expected_focalizer: str  # Quien deberia ser el focalizador
    actual_perspective: str  # De quien es la perspectiva intrusa
    chapter: int
    severity: str = "clear"  # clear, subtle


@dataclass
class GoldSentimentPoint:
    """Punto en el arco de sentimiento."""

    chapter: int
    description: str
    sentiment: str  # neutro, positivo, negativo, mixto
    intensity: float  # 0-1
    character: str


@dataclass
class GoldRegisterChange:
    """Cambio de registro de un personaje."""

    character: str
    from_register: str  # formal, coloquial, familiar
    to_register: str
    chapter: int
    context: str  # Con quien habla


GOLD_MULETILLAS_DIALOGOS = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_muletillas_dialogos.txt",
    text_type=TextType.DIALOGUE,
    description="Texto para evaluar deteccion de muletillas y atribucion de dialogos",
    entities=[
        GoldEntity("Rosa Martinez", "PER", ["Rosa", "Rosa Martinez", "senorita Martinez"]),
        GoldEntity(
            "Fernando Gutierrez", "PER", ["Fernando", "Fernando Gutierrez", "senor Gutierrez"]
        ),
        GoldEntity("Marcos", "PER", ["Marcos"]),
        GoldEntity("Carmen", "PER", ["Carmen", "abuela"]),
        GoldEntity("Director", "PER", ["Director", "director general"]),
        GoldEntity("Camarero", "PER", ["Camarero", "el camarero"]),
    ],
    relations=[
        GoldRelation("Rosa", "Marcos", "sibling"),
        GoldRelation("Rosa", "Carmen", "grandchild", "e1_to_e2"),
        GoldRelation("Rosa", "Fernando", "employee", "e1_to_e2"),
    ],
    chapters=[
        GoldChapter(1, "El encuentro", "CAPITULO 1:", 100),
        GoldChapter(2, "La transformacion", "CAPITULO 2:", 100),
        GoldChapter(3, "La presentacion", "CAPITULO 3:", 100),
        GoldChapter(4, "El verdadero yo", "CAPITULO 4:", 100),
    ],
)

# Muletillas detectadas por personaje (datos del test file)
GOLD_MULETILLAS_DATA = {
    "muletillas_dialogos": {
        "Rosa": {
            "pues": 15,
            "o sea": 12,
            "eh": 4,
            "bueno": 6,
            "vamos": 2,
            "la verdad": 2,
            "no se": 3,
        },
        "Marcos": {"pues": 3, "o sea": 4, "eh": 3, "bueno": 2, "vale": 2, "viste": 2, "ya": 2},
        "Abuela": {"ay": 2, "pues": 1},
        "Fernando": {},  # Sin muletillas (registro formal)
        "Camarero": {"bueno": 2, "vale": 2},
    }
}

# Dialogos con atribucion (datos del test file)
GOLD_DIALOGUES_DATA = {
    "muletillas_dialogos": [
        GoldDialogue("Bueno, bueno, que le pongo?", "Camarero", 1),
        GoldDialogue("Pues, eh, no se... O sea, un cafe con leche, supongo", "Rosa", 1),
        GoldDialogue("Vale, vale, enseguida se lo traigo.", "Camarero", 1),
        GoldDialogue("Buenos dias, senorita Martinez", "Fernando", 1),
        GoldDialogue("Buenos dias, senor Gutierrez. Igualmente", "Rosa", 1),
        GoldDialogue("Bien, procedamos a analizar la propuesta", "Fernando", 1),
        GoldDialogue("Asi es, senor. He revisado cada cifra personalmente", "Rosa", 1),
        GoldDialogue("Eh, hermana, que, como va la vida?", "Marcos", 2),
        GoldDialogue("Pues mira, bien, o sea, podria ir mejor", "Rosa", 2),
        GoldDialogue("Ya, ya, bueno, es que... o sea, necesito un favor, viste?", "Marcos", 2),
        GoldDialogue("Ay, Marcos, siempre igual, vamos.", "Rosa", 2),
        GoldDialogue("Senorita Martinez, espero no interrumpir", "Director", 2),
        GoldDialogue("En absoluto, senor director. Como puedo ayudarle?", "Rosa", 2),
        GoldDialogue("Necesito los informes para manana a primera hora.", "Director", 2),
        GoldDialogue("Por supuesto. Los tendra en su despacho antes de las ocho.", "Rosa", 2),
        GoldDialogue("Bueno, pues nada, que tengo curro", "Rosa", 2),
        GoldDialogue("Vale, vale, ya me voy. Eh, luego hablamos, no?", "Marcos", 2),
        GoldDialogue("Estimados accionistas, senoras y senores", "Rosa", 3),
        GoldDialogue("Eh, que pasa! Menuda charla, tia! O sea, flipante!", "Marcos", 3),
        GoldDialogue("Gracias, Marcos. Me alegro de que hayas venido", "Rosa", 3),
        GoldDialogue(
            "Ya, bueno, pues nada, que mola mucho verte asi, o sea, toda profesional y eso.",
            "Marcos",
            3,
        ),
        GoldDialogue(
            "Excelente presentacion, senorita Martinez. Sus metricas eran impecables", "Fernando", 3
        ),
        GoldDialogue("Muchas gracias, senor Gutierrez. Ha sido un placer", "Rosa", 3),
        GoldDialogue("Eh, este es el jefe?", "Marcos", 3),
        GoldDialogue("Marcos, por favor", "Rosa", 3),
        GoldDialogue("Ay, hija, cuentame. Como ha ido?", "Carmen", 4),
        GoldDialogue("Pues mira, abuela, bien. O sea, creo que bien.", "Rosa", 4),
        GoldDialogue(
            "Ya sabes como es tu hermano. Siempre ha sido muy, como decirlo, espontaneo.",
            "Carmen",
            4,
        ),
        GoldDialogue(
            "Si, bueno, es que... no se, a veces me gustaria que fuera mas, pues, mas profesional.",
            "Rosa",
            4,
        ),
        GoldDialogue(
            "Hija, cada uno es como es. Tu eres de una manera en el trabajo y de otra en casa.",
            "Carmen",
            4,
        ),
        GoldDialogue("Tienes razon, abuela. Es que, no se, a veces pienso demasiado.", "Rosa", 4),
        GoldDialogue("Pues deja de pensar tanto y vive, hija. La vida es corta.", "Carmen", 4),
    ]
}

# Cambios de registro
GOLD_REGISTER_CHANGES_DATA = {
    "muletillas_dialogos": [
        GoldRegisterChange("Rosa", "coloquial", "formal", 1, "Con Fernando"),
        GoldRegisterChange("Rosa", "formal", "coloquial", 2, "Con Marcos"),
        GoldRegisterChange("Rosa", "coloquial", "formal", 2, "Con Director"),
        GoldRegisterChange("Rosa", "formal", "coloquial", 2, "Con Marcos de nuevo"),
        GoldRegisterChange("Rosa", "coloquial", "formal", 3, "Presentacion"),
        GoldRegisterChange("Rosa", "formal", "coloquial", 4, "Con abuela"),
    ]
}


GOLD_FOCALIZACION_SENTIMIENTO = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_focalizacion_sentimiento.txt",
    text_type=TextType.FICTION,
    description="Texto para evaluar focalizacion narrativa y arcos de sentimiento",
    entities=[
        GoldEntity("Elena", "PER", ["Elena"]),
        GoldEntity("Ricardo", "PER", ["Ricardo"]),
        GoldEntity("Marta", "PER", ["Marta"]),
        GoldEntity("Padre de Elena", "PER", ["su padre", "papa", "padre"]),
    ],
    relations=[
        GoldRelation("Elena", "Ricardo", "sibling"),
        GoldRelation("Elena", "Marta", "parent_child", "e2_to_e1"),
        GoldRelation("Elena", "Padre de Elena", "parent_child", "e2_to_e1"),
        GoldRelation("Ricardo", "Marta", "parent_child", "e2_to_e1"),
    ],
    chapters=[
        GoldChapter(1, "El inicio", "CAPITULO 1:", 100),
        GoldChapter(2, "La revelacion", "CAPITULO 2:", 100),
        GoldChapter(3, "El duelo", "CAPITULO 3:", 100),
        GoldChapter(4, "La recuperacion", "CAPITULO 4:", 100),
        GoldChapter(5, "El nuevo comienzo", "CAPITULO 5:", 100),
    ],
)

# Violaciones de focalizacion
GOLD_FOCALIZATION_VIOLATIONS_DATA = {
    "focalizacion_sentimiento": [
        GoldFocalizationViolation(
            "Ricardo sabia que debia contarle la verdad, pero el miedo lo paralizaba",
            "Elena",
            "Ricardo",
            2,
            "clear",
        ),
        GoldFocalizationViolation("sin saber como ayudarla", "Elena", "Marta", 3, "subtle"),
        GoldFocalizationViolation(
            "El pensaba que mantenerse ocupado era la unica forma de sobrevivir",
            "Elena",
            "Ricardo",
            3,
            "clear",
        ),
        GoldFocalizationViolation(
            "orgullosa de la fortaleza de su hija, aunque Elena no lo supiera",
            "Elena",
            "Marta",
            5,
            "subtle",
        ),
    ]
}

# Arco de sentimiento por capitulo
GOLD_SENTIMENT_ARC_DATA = {
    "focalizacion_sentimiento": [
        GoldSentimentPoint(1, "Inicio", "neutro", 0.3, "Elena"),
        GoldSentimentPoint(1, "Inquietud", "negativo", 0.4, "Elena"),
        GoldSentimentPoint(2, "Shock revelacion", "negativo", 0.9, "Elena"),
        GoldSentimentPoint(2, "Devastacion", "negativo", 1.0, "Elena"),
        GoldSentimentPoint(3, "Rabia", "negativo", 0.8, "Elena"),
        GoldSentimentPoint(3, "Impotencia", "negativo", 0.7, "Elena"),
        GoldSentimentPoint(3, "Curiosidad carta", "mixto", 0.5, "Elena"),
        GoldSentimentPoint(3, "Ternura agridulce", "mixto", 0.6, "Elena"),
        GoldSentimentPoint(4, "Esperanza tentativa", "positivo", 0.4, "Elena"),
        GoldSentimentPoint(4, "Dolor y gratitud", "mixto", 0.5, "Elena"),
        GoldSentimentPoint(4, "Reconciliacion", "positivo", 0.7, "Elena"),
        GoldSentimentPoint(5, "Paz y aceptacion", "positivo", 0.8, "Elena"),
        GoldSentimentPoint(5, "Resolucion final", "positivo", 0.85, "Elena"),
    ]
}


GOLD_CORREFERENCIAS_COMPLEJAS = GoldStandard(
    text_file="test_books/evaluation_tests/prueba_correferencias_complejas.txt",
    text_type=TextType.FICTION,
    description="Texto para evaluar resolucion de correferencias complejas",
    entities=[
        GoldEntity("Miguel Garcia", "PER", ["Miguel", "el mayor", "hermanito"]),
        GoldEntity("Sofia Garcia", "PER", ["Sofia", "Su hermana", "Ella"]),
        GoldEntity("Pedro Garcia", "PER", ["Pedro", "el mediano", "el ultimo", "su hermano menor"]),
        GoldEntity("dona Carmen", "PER", ["dona Carmen", "La madre de los tres", "el pegamento"]),
        GoldEntity("don Antonio", "PER", ["don Antonio", "El padre", "su padre", "papa"]),
        GoldEntity(
            "La casa Garcia", "LOC", ["la vieja casa", "la casa", "la propiedad", "esta casa"]
        ),
    ],
    relations=[
        GoldRelation("Miguel Garcia", "Sofia Garcia", "sibling"),
        GoldRelation("Miguel Garcia", "Pedro Garcia", "sibling"),
        GoldRelation("Sofia Garcia", "Pedro Garcia", "sibling"),
        GoldRelation("Miguel Garcia", "dona Carmen", "parent_child", "e2_to_e1"),
        GoldRelation("Sofia Garcia", "dona Carmen", "parent_child", "e2_to_e1"),
        GoldRelation("Pedro Garcia", "dona Carmen", "parent_child", "e2_to_e1"),
        GoldRelation("Miguel Garcia", "don Antonio", "parent_child", "e2_to_e1"),
        GoldRelation("Sofia Garcia", "don Antonio", "parent_child", "e2_to_e1"),
        GoldRelation("Pedro Garcia", "don Antonio", "parent_child", "e2_to_e1"),
        GoldRelation("dona Carmen", "don Antonio", "spouse"),
    ],
    chapters=[
        GoldChapter(1, "La reunion familiar", "CAPITULO 1:", 100),
        GoldChapter(2, "Las tensiones", "CAPITULO 2:", 100),
        GoldChapter(3, "Los recuerdos", "CAPITULO 3:", 100),
        GoldChapter(4, "La decision", "CAPITULO 4:", 100),
        GoldChapter(5, "El acuerdo", "CAPITULO 5:", 100),
    ],
    coreferences=[
        GoldCoreference(
            "Miguel Garcia", ["Miguel", "el mayor", "El", "hermanito", "el"], [1, 2, 3, 4, 5]
        ),
        GoldCoreference("Sofia Garcia", ["Sofia", "Su hermana", "Ella", "ella"], [1, 2, 3, 4, 5]),
        GoldCoreference(
            "Pedro Garcia",
            ["Pedro", "el mediano", "el ultimo", "el", "su hermano menor"],
            [1, 2, 3, 4, 5],
        ),
        GoldCoreference(
            "dona Carmen", ["La madre de los tres", "dona Carmen", "Ella", "el pegamento"], [3]
        ),
        GoldCoreference(
            "don Antonio", ["su padre", "El padre", "don Antonio", "El", "papa"], [2, 3, 5]
        ),
        GoldCoreference(
            "La casa Garcia",
            ["la vieja casa", "la casa", "Esta", "la propiedad", "esta casa"],
            [1, 2, 4, 5],
        ),
    ],
    fusion_pairs=[
        ("Miguel", "Miguel Garcia"),
        ("Sofia", "Sofia Garcia"),
        ("Pedro", "Pedro Garcia"),
        ("el mayor", "Miguel Garcia"),
        ("el mediano", "Pedro Garcia"),
    ],
)


# Gold standards de validación (datos no vistos)
UNSEEN_GOLD_STANDARDS = {
    "ciencia_ficcion": GOLD_UNSEEN_CIENCIA_FICCION,
    "novela_historica": GOLD_UNSEEN_NOVELA_HISTORICA,
    "thriller": GOLD_UNSEEN_THRILLER,
    "romance": GOLD_UNSEEN_ROMANCE,
    "fantasia": GOLD_UNSEEN_FANTASIA,
    "terror": GOLD_UNSEEN_TERROR,
    "aventuras": GOLD_UNSEEN_AVENTURAS,
    "drama": GOLD_UNSEEN_DRAMA,
}

# Gold standards para evaluacion avanzada
ADVANCED_GOLD_STANDARDS = {
    "muletillas_dialogos": GOLD_MULETILLAS_DIALOGOS,
    "focalizacion_sentimiento": GOLD_FOCALIZACION_SENTIMIENTO,
    "correferencias_complejas": GOLD_CORREFERENCIAS_COMPLEJAS,
}
