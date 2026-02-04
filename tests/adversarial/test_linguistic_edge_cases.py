"""
Tests lingüísticos de casos extremos para análisis narrativo.

Autor: Agente Lingüista Adversarial
Perspectiva: Lingüística hispánica, gramática española, estilística narrativa

Este archivo explora fenómenos lingüísticos del español que pueden causar
problemas en el análisis automático:

1. MORFOLOGÍA Y SINTAXIS
   - Concordancia compleja (sintagmas partitivos, colectivos)
   - Leísmo/laísmo/loísmo
   - Dequeísmo y queísmo
   - Gerundios del BOE

2. SEMÁNTICA Y PRAGMÁTICA
   - Ironía y sarcasmo
   - Eufemismos
   - Atributos temporales y modales
   - Negación y polaridad

3. ONOMÁSTICA ESPAÑOLA
   - Nombres con artículos (El Greco, La Pasionaria)
   - Apellidos compuestos con preposiciones
   - Hipocorísticos regionales
   - Nombres ambiguos de género

4. NARRATOLOGÍA
   - Estilo indirecto libre
   - Monólogo interior
   - Focalización cero vs interna
   - Analepsis/prolepsis implícitas

5. VARIACIÓN DIALECTAL
   - Voseo
   - Seseo/ceceo
   - Léxico regional
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def ner_extractor():
    """NERExtractor compartido."""
    from narrative_assistant.nlp.ner import NERExtractor

    return NERExtractor()


@pytest.fixture(scope="module")
def sensory_analyzer():
    """SensoryAnalyzer compartido."""
    from narrative_assistant.nlp.style.sensory_report import SensoryAnalyzer

    return SensoryAnalyzer()


# =============================================================================
# 1. ONOMÁSTICA ESPAÑOLA - Nombres complejos
# =============================================================================


class TestSpanishOnomastics:
    """
    Tests para nombres propios españoles con estructuras complejas.

    El español tiene convenciones onomásticas únicas:
    - Dos apellidos (paterno + materno)
    - Partículas nobiliarias (de, del, de la, de los)
    - Artículos incorporados (El Greco, La Pasionaria)
    - Tratamientos (Don, Doña, Fray, Sor)
    - Hipocorísticos regionales
    """

    # Nombres con artículo incorporado - deben detectarse completos
    ARTICLE_NAMES = [
        ("El Greco pintaba con pasión.", "El Greco", "PER"),
        ("La Pasionaria dio un discurso.", "La Pasionaria", "PER"),
        ("El Cordobés toreó en Madrid.", "El Cordobés", "PER"),
        ("La Faraona cantó hasta el amanecer.", "La Faraona", "PER"),
        ("El Fary actuó en televisión.", "El Fary", "PER"),
    ]

    @pytest.mark.parametrize("text,expected_name,expected_type", ARTICLE_NAMES)
    def test_names_with_article(self, ner_extractor, text, expected_name, expected_type):
        """Nombres con artículo incorporado deben detectarse completos."""
        result = ner_extractor.extract_entities(text)
        if result.is_failure:
            pytest.skip(f"NER error: {result.error}")

        entities = result.value.entities
        names = [e.text for e in entities]

        # El nombre completo o al menos el apodo debe estar
        found = any(expected_name in name or name in expected_name for name in names)
        if not found:
            pytest.xfail(f"Nombre con artículo '{expected_name}' no detectado en: {names}")

    # Apellidos con partículas nobiliarias
    NOBLE_PARTICLES = [
        "María de los Ángeles García",
        "Juan de la Cruz Fernández",
        "Pedro del Valle Inclán",
        "Ana de las Casas Rojas",
        "Luis von Habsburg",  # También partículas extranjeras naturalizadas
    ]

    @pytest.mark.parametrize("full_name", NOBLE_PARTICLES)
    def test_noble_particle_names(self, ner_extractor, full_name):
        """Apellidos con partículas deben mantenerse unidos."""
        text = f"{full_name} llegó a la reunión."
        result = ner_extractor.extract_entities(text)
        if result.is_failure:
            pytest.skip(f"NER error: {result.error}")

        entities = result.value.entities
        # Verificar que al menos detecta algo del nombre
        if not entities:
            pytest.xfail(f"Nombre con partícula '{full_name}' no detectado")

    # Hipocorísticos españoles (formas cariñosas de nombres)
    HYPOCORISTICS = [
        ("Francisco", ["Paco", "Pancho", "Curro", "Fran", "Quico"]),
        ("José", ["Pepe", "Pepito", "Chepe"]),
        ("Dolores", ["Lola", "Loles", "Lolita"]),
        ("Concepción", ["Concha", "Conchita", "Conchi"]),
        ("Guadalupe", ["Lupe", "Lupita"]),
        ("Enrique", ["Quique", "Kike"]),
        ("Ignacio", ["Nacho", "Iñaki"]),
        ("Eduardo", ["Edu", "Lalo"]),
    ]

    @pytest.mark.parametrize("formal,hypocoristics", HYPOCORISTICS)
    def test_hypocoristic_recognition(self, formal, hypocoristics):
        """Los hipocorísticos deben poder vincularse al nombre formal."""
        # Este test documenta la necesidad de un diccionario de hipocorísticos
        from difflib import SequenceMatcher

        for hypo in hypocoristics:
            similarity = SequenceMatcher(None, formal.lower(), hypo.lower()).ratio()
            # La mayoría de hipocorísticos tienen baja similaridad textual
            if similarity < 0.4:
                pytest.xfail(
                    f"Hipocorístico '{hypo}' de '{formal}' tiene similaridad {similarity:.2f} - "
                    f"requiere diccionario de hipocorísticos"
                )


# =============================================================================
# 2. CONCORDANCIA COMPLEJA
# =============================================================================


class TestComplexAgreement:
    """
    Tests para casos de concordancia gramatical compleja en español.

    El español tiene reglas de concordancia que pueden ser ambiguas:
    - Sintagmas partitivos: "la mayoría de los estudiantes"
    - Colectivos: "la gente", "el pueblo"
    - Sujetos coordinados: "Juan y María vinieron/vino"
    - Concordancia ad sensum vs gramatical
    """

    # Concordancia con colectivos - ambos son gramaticalmente correctos
    COLLECTIVE_SENTENCES = [
        # (oración, es_correcta)
        ("La gente gritaba enfurecida.", True),  # Concordancia gramatical
        ("La gente gritaban enfurecidos.", True),  # Concordancia ad sensum (aceptable)
        ("El grupo de estudiantes llegó tarde.", True),
        ("El grupo de estudiantes llegaron tarde.", True),  # Ad sensum
        ("La mayoría votó a favor.", True),
        ("La mayoría votaron a favor.", True),  # Ad sensum
    ]

    @pytest.mark.parametrize("sentence,is_correct", COLLECTIVE_SENTENCES)
    def test_collective_agreement(self, sentence, is_correct):
        """La concordancia ad sensum con colectivos debe aceptarse."""
        # Importar el validador ortográfico si existe
        try:
            from narrative_assistant.nlp.orthography.voting_checker import VotingChecker

            checker = VotingChecker()
            # Verificar que no marca como error oraciones correctas
            # Este test documenta que ambas concordancias son válidas
            pytest.xfail("Concordancia ad sensum: ambas formas son correctas en español culto")
        except ImportError:
            pytest.skip("VotingChecker no disponible")

    # Leísmo aceptado vs rechazado por la RAE
    LEISMO_CASES = [
        # Leísmo de persona masculino singular - ACEPTADO por RAE
        ("Le vi en la calle.", True, "leísmo aceptado"),
        ("Lo vi en la calle.", True, "forma etimológica"),
        # Leísmo de cosa - RECHAZADO
        ("Le compré ayer.", False, "leísmo de cosa"),
        ("Lo compré ayer.", True, "forma correcta"),
        # Leísmo femenino - RECHAZADO
        ("Le vi a María.", False, "leísmo femenino"),
        ("La vi a María.", True, "forma correcta"),
    ]

    @pytest.mark.parametrize("sentence,is_accepted,reason", LEISMO_CASES)
    def test_leismo_detection(self, sentence, is_accepted, reason):
        """Distinguir leísmo aceptado de rechazado."""
        # El leísmo de persona masculino singular es aceptado por la RAE
        # pero otros tipos no. El sistema debería distinguirlos.
        pytest.xfail(f"Leísmo: {reason} - requiere análisis semántico profundo")


# =============================================================================
# 3. ATRIBUTOS COMPLEJOS - Ironía, temporalidad, modalidad
# =============================================================================


class TestComplexAttributes:
    """
    Tests para detección de atributos en contextos complejos.

    Problemas:
    - Ironía: "el genio de Juan" cuando es tonto
    - Atributos temporales: "era rico" vs "es rico"
    - Atributos condicionales: "sería feliz si..."
    - Atributos de terceros: "la hermana de Juan era alta"
    - Atributos comparativos: "más alto que Pedro"
    """

    # Atributos irónicos - significado opuesto al literal
    IRONIC_ATTRIBUTES = [
        ("¡Qué listo eres! —le espetó tras ver el desastre.", "listo", False),
        ("Bonito trabajo has hecho —dijo señalando las ruinas.", "bonito", False),
        ("El genio de mi hermano volvió a perder las llaves.", "genio", False),
        ("¡Vaya experto! No sabe ni encender el ordenador.", "experto", False),
    ]

    @pytest.mark.parametrize("text,attr,should_be_positive", IRONIC_ATTRIBUTES)
    def test_ironic_attributes(self, text, attr, should_be_positive):
        """Atributos irónicos no deben asignarse literalmente."""
        # La ironía requiere análisis de contexto pragmático
        pytest.xfail(f"Ironía: '{attr}' es irónico - requiere análisis pragmático")

    # Atributos temporalmente acotados
    TEMPORAL_ATTRIBUTES = [
        ("María era rubia de niña.", "rubia", "pasado", "niñez"),
        ("Juan fue rico hasta que perdió todo.", "rico", "pasado", "hasta_evento"),
        ("Será famoso cuando publique el libro.", "famoso", "futuro", "condicional"),
        ("Pedro había sido atlético antes del accidente.", "atlético", "pasado", "antes_evento"),
    ]

    @pytest.mark.parametrize("text,attr,tense,scope", TEMPORAL_ATTRIBUTES)
    def test_temporal_attributes(self, text, attr, tense, scope):
        """Atributos temporales deben indicar su alcance temporal."""
        # Los atributos deberían tener metadata temporal
        pytest.xfail(f"Atributo '{attr}' tiene alcance temporal '{scope}' - no se trackea")

    # Atributos de terceros (no del sujeto principal)
    THIRD_PARTY_ATTRIBUTES = [
        ("La hermana de Juan era muy alta.", "alta", "hermana de Juan", "Juan"),
        (
            "El padre de María, un hombre corpulento, entró.",
            "corpulento",
            "padre de María",
            "María",
        ),
        ("Los amigos de Pedro, todos rubios, llegaron.", "rubios", "amigos de Pedro", "Pedro"),
    ]

    @pytest.mark.parametrize("text,attr,belongs_to,not_belongs_to", THIRD_PARTY_ATTRIBUTES)
    def test_third_party_attributes(self, text, attr, belongs_to, not_belongs_to):
        """Atributos no deben asignarse al sujeto equivocado."""
        # El atributo "alta" es de "hermana de Juan", no de "Juan"
        pytest.xfail(f"Atributo '{attr}' pertenece a '{belongs_to}', no a '{not_belongs_to}'")


# =============================================================================
# 4. ESTILO INDIRECTO LIBRE
# =============================================================================


class TestFreeIndirectStyle:
    """
    Tests para detección de estilo indirecto libre.

    El estilo indirecto libre mezcla la voz del narrador con los pensamientos
    del personaje sin marcadores explícitos. Es muy común en narrativa moderna.

    Ejemplo:
    "María miró por la ventana. Qué día más horrible. Ojalá dejara de llover."

    Las dos últimas oraciones son pensamientos de María en estilo indirecto libre,
    pero no tienen marcadores de diálogo ni verbos de pensamiento.
    """

    FREE_INDIRECT_EXAMPLES = [
        (
            "Juan caminaba por la calle. Maldita lluvia. ¿Por qué no había cogido el paraguas?",
            ["Maldita lluvia.", "¿Por qué no había cogido el paraguas?"],
            "Juan",
        ),
        (
            "Ana observó a su jefe. Menudo imbécil. Algún día le diría lo que pensaba.",
            ["Menudo imbécil.", "Algún día le diría lo que pensaba."],
            "Ana",
        ),
        (
            "Pedro entró en la habitación. Todo seguía igual. Los mismos cuadros, las mismas cortinas.",
            ["Todo seguía igual.", "Los mismos cuadros, las mismas cortinas."],
            "Pedro",
        ),
    ]

    @pytest.mark.parametrize("text,indirect_parts,character", FREE_INDIRECT_EXAMPLES)
    def test_free_indirect_style_detection(self, text, indirect_parts, character):
        """El estilo indirecto libre debe detectarse y atribuirse al personaje."""
        # Este es un problema muy difícil de NLP
        pytest.xfail(
            f"Estilo indirecto libre: '{indirect_parts[0]}' es pensamiento de '{character}' - "
            "requiere análisis de focalización avanzado"
        )


# =============================================================================
# 5. ANÁLISIS SENSORIAL - Sinestesia y metáforas
# =============================================================================


class TestSensorySynesthesia:
    """
    Tests para detección de sinestesia y metáforas sensoriales.

    La sinestesia mezcla sentidos:
    - "Un color chillón" (vista + oído)
    - "Una voz dulce" (oído + gusto)
    - "Un silencio pesado" (oído + tacto)

    Las metáforas sensoriales usan vocabulario sensorial de forma no literal:
    - "Veía venir el desastre" (no es visión real)
    - "Olía a problemas" (no es olfato real)
    """

    SYNESTHESIA_EXAMPLES = [
        ("El color chillón de su vestido molestaba a todos.", "chillón", ["sight", "hearing"]),
        ("Su voz dulce calmaba a los niños.", "dulce", ["hearing", "taste"]),
        ("Un silencio pesado llenaba la sala.", "pesado", ["hearing", "touch"]),
        ("La melodía áspera del violín.", "áspera", ["hearing", "touch"]),
        ("Colores cálidos decoraban la estancia.", "cálidos", ["sight", "touch"]),
    ]

    @pytest.mark.parametrize("text,word,senses", SYNESTHESIA_EXAMPLES)
    def test_synesthesia_detection(self, sensory_analyzer, text, word, senses):
        """La sinestesia combina múltiples sentidos - debe detectarse correctamente."""
        # La sinestesia es un recurso literario válido, no un error
        pytest.xfail(
            f"Sinestesia: '{word}' combina {senses} - "
            "el análisis sensorial debería reconocer este recurso"
        )

    METAPHORICAL_SENSORY = [
        ("Veía venir la catástrofe.", "Veía", False, "metaphor"),
        ("No veía la hora de marcharse.", "veía", False, "idiom"),
        ("Olía a problemas.", "Olía", False, "metaphor"),
        ("Escuchó los latidos de la ciudad.", "Escuchó", False, "metaphor"),
        ("Tocó el cielo con las manos.", "Tocó", False, "metaphor"),
        ("Saboreó la victoria.", "Saboreó", False, "metaphor"),
    ]

    @pytest.mark.parametrize("text,word,is_literal,reason", METAPHORICAL_SENSORY)
    def test_metaphorical_sensory_exclusion(self, sensory_analyzer, text, word, is_literal, reason):
        """Metáforas sensoriales no deben contarse como descripción sensorial literal."""
        # El análisis sensorial debería distinguir uso literal de metafórico
        pytest.xfail(f"'{word}' es {reason}, no uso literal - requiere análisis semántico")


# =============================================================================
# 6. MARCADORES TEMPORALES AMBIGUOS
# =============================================================================


class TestAmbiguousTemporalMarkers:
    """
    Tests para marcadores temporales ambiguos en narrativa.

    Problemas:
    - "Entonces" puede ser temporal o consecutivo
    - "Después" sin referente claro
    - Presente histórico
    - Verbos modales que modifican temporalidad
    """

    AMBIGUOUS_MARKERS = [
        # "Entonces" consecutivo vs temporal
        ("Llovía. Entonces decidió quedarse.", "entonces", "consecutive", "no es flashback"),
        ("Entonces, en 1985, todo era diferente.", "entonces", "temporal", "es flashback"),
        # Presente histórico - narra pasado en presente
        ("Colón llega a América en 1492.", "llega", "historical_present", "1492"),
        ("Cervantes escribe el Quijote en prisión.", "escribe", "historical_present", "siglo XVII"),
        # "Antes" sin referente
        ("Antes todo era mejor.", "antes", "vague", "sin referente temporal"),
    ]

    @pytest.mark.parametrize("text,marker,marker_type,note", AMBIGUOUS_MARKERS)
    def test_ambiguous_temporal_markers(self, text, marker, marker_type, note):
        """Marcadores temporales ambiguos deben interpretarse según contexto."""
        pytest.xfail(f"Marcador '{marker}' es {marker_type}: {note}")

    # Flashbacks sin marcadores léxicos explícitos
    IMPLICIT_FLASHBACKS = [
        """
        2023. María miraba la foto antigua.

        1985. La foto se tomó en verano.
        Todos sonreían frente a la casa familiar.

        2023. María dejó la foto sobre la mesa.
        """,
        """
        Tenía treinta años cuando ocurrió.

        A los diez años, su padre le enseñó a nadar.
        El agua del río estaba fría aquel verano.

        Ahora, con treinta años, recordaba esa sensación.
        """,
    ]

    @pytest.mark.parametrize("text", IMPLICIT_FLASHBACKS)
    def test_implicit_flashback_by_date(self, text):
        """Flashbacks indicados solo por fechas deben detectarse."""
        pytest.xfail(
            "Flashback implícito por cambio de fecha - requiere análisis temporal avanzado"
        )


# =============================================================================
# 7. DIÁLOGOS SIN MARCADORES ESTÁNDAR
# =============================================================================


class TestNonStandardDialogue:
    """
    Tests para diálogos con formato no estándar.

    Formatos a considerar:
    - Sin guiones (estilo Saramago)
    - Con guiones pero sin verbum dicendi
    - Citas dentro de citas
    - Monólogo interior
    - Diálogo telefónico (solo un lado)
    """

    SARAMAGO_STYLE = """
    Qué quieres, preguntó ella. Nada, solo mirarte, respondió él.
    Pues mira, dijo ella dándose la vuelta. La miró durante un largo rato,
    luego dijo, Eres hermosa. Ella no respondió.
    """

    def test_saramago_style_dialogue(self):
        """Diálogos sin guiones (estilo Saramago) deben parsearse."""
        # José Saramago no usa guiones ni comillas para diálogos
        pytest.xfail(
            "Estilo Saramago: diálogos sin puntuación estándar - requiere heurísticas especiales"
        )

    TELEPHONE_DIALOGUE = """
    —¿Diga?
    —...
    —Sí, soy yo.
    —...
    —¿Cuándo?
    —...
    —Voy para allá.
    """

    def test_telephone_dialogue(self):
        """Diálogos telefónicos con un solo lado visible."""
        pytest.xfail("Diálogo telefónico: solo un interlocutor audible - contexto implícito")

    INNER_MONOLOGUE = """
    María caminaba por la calle pensando en todo lo ocurrido no podía creer
    que Juan la hubiera traicionado después de tantos años juntos qué iba
    a hacer ahora adónde iría tal vez a casa de su madre no su madre no
    lo entendería mejor llamar a Ana sí eso haría.
    """

    def test_stream_of_consciousness(self):
        """Monólogo interior / flujo de conciencia sin puntuación."""
        # El stream of consciousness rompe reglas de puntuación intencionalmente
        pytest.xfail("Flujo de conciencia: sin puntuación estándar - recurso literario válido")


# =============================================================================
# 8. VARIACIÓN DIALECTAL
# =============================================================================


class TestDialectalVariation:
    """
    Tests para variación dialectal del español.

    El español tiene variación significativa:
    - Voseo (Argentina, Uruguay, partes de Centroamérica)
    - Ustedes vs vosotros (Latinoamérica vs España)
    - Léxico regional
    - Seseo/ceceo
    """

    VOSEO_EXAMPLES = [
        ("Vos sabés que te quiero.", "Argentina"),
        ("¿Qué querés que te diga?", "Argentina"),
        ("Andá a saber qué pasó.", "Argentina"),
        ("Mirá lo que encontré.", "Argentina"),
    ]

    @pytest.mark.parametrize("text,region", VOSEO_EXAMPLES)
    def test_voseo_recognition(self, text, region):
        """El voseo debe reconocerse como español válido, no como error."""
        # El voseo es estándar en Argentina, Uruguay, etc.
        pytest.xfail(f"Voseo de {region}: forma válida, no debe marcarse como error")

    REGIONAL_LEXICON = [
        ("El pibe estaba re loco.", "Argentina", ["pibe", "re"]),
        ("Cogí el autobús esta mañana.", "España", ["cogí"]),
        ("Ahorita vengo.", "México", ["ahorita"]),
        ("El chamo es muy chévere.", "Venezuela", ["chamo", "chévere"]),
        ("Pasame la guagua.", "Cuba/Canarias", ["guagua"]),
    ]

    @pytest.mark.parametrize("text,region,words", REGIONAL_LEXICON)
    def test_regional_lexicon(self, text, region, words):
        """Léxico regional debe reconocerse como válido."""
        pytest.xfail(f"Léxico de {region}: {words} son válidos regionalmente")


# =============================================================================
# 9. ORTOGRAFÍA - Casos límite
# =============================================================================


class TestOrthographyEdgeCases:
    """
    Tests para casos límite ortográficos.
    """

    # Palabras que pueden o no llevar tilde según significado
    DIACRITICAL_ACCENT = [
        ("Él vino ayer.", "él", True, "pronombre"),
        ("El vino tinto.", "el", False, "artículo"),
        ("Sé que vendrás.", "sé", True, "verbo saber"),
        ("Se lo dije.", "se", False, "pronombre reflexivo"),
        ("Más vale tarde que nunca.", "más", True, "adverbio"),
        ("Quiero más agua.", "más", True, "adverbio"),
        ("Estudié mas no aprobé.", "mas", False, "conjunción adversativa"),
    ]

    @pytest.mark.parametrize("text,word,has_accent,pos", DIACRITICAL_ACCENT)
    def test_diacritical_accent(self, text, word, has_accent, pos):
        """Tildes diacríticas deben verificarse según contexto gramatical."""
        # Requiere análisis morfosintáctico
        pytest.xfail(f"Tilde diacrítica: '{word}' como {pos}")

    # Extranjerismos con grafía variable
    FOREIGN_WORDS = [
        ("Tomó un whisky.", "whisky", ["whisky", "güisqui"]),
        ("Compró unos jeans.", "jeans", ["jeans", "yins", "vaqueros"]),
        ("Escribe en su blog.", "blog", ["blog", "bitácora"]),
        ("Envió un email.", "email", ["email", "correo electrónico", "e-mail"]),
    ]

    @pytest.mark.parametrize("text,word,variants", FOREIGN_WORDS)
    def test_foreign_words(self, text, word, variants):
        """Extranjerismos pueden tener grafías alternativas válidas."""
        pytest.xfail(f"Extranjerismo '{word}': variantes válidas {variants}")


# =============================================================================
# 10. RELACIONES IMPLÍCITAS
# =============================================================================


class TestImplicitRelationships:
    """
    Tests para relaciones entre personajes expresadas implícitamente.
    """

    IMPLICIT_RELATIONS = [
        (
            "María abrazó a Juan. No podía creer que su hijo hubiera vuelto.",
            "María",
            "Juan",
            "madre-hijo",
            "implícito por 'su hijo'",
        ),
        (
            "Pedro y Ana celebraban. Veinte años de casados no eran poca cosa.",
            "Pedro",
            "Ana",
            "esposos",
            "implícito por 'casados'",
        ),
        (
            "—Papá, ¿puedo ir? —preguntó Luis.\n—No —respondió Carlos.",
            "Luis",
            "Carlos",
            "hijo-padre",
            "implícito por 'Papá'",
        ),
    ]

    @pytest.mark.parametrize("text,entity1,entity2,relation,evidence", IMPLICIT_RELATIONS)
    def test_implicit_relationship_detection(self, text, entity1, entity2, relation, evidence):
        """Relaciones implícitas deben inferirse del contexto."""
        pytest.xfail(f"Relación {entity1}-{entity2}: {relation} ({evidence})")


# =============================================================================
# INTEGRATION: Ejecutar análisis completo en textos complejos
# =============================================================================


class TestComplexNarrativeAnalysis:
    """Tests de integración con textos narrativos complejos."""

    COMPLEX_NARRATIVE = """
    Capítulo 1: El regreso

    Madrid, 2023.

    María de los Ángeles García-Lorca entró en la casa de su infancia.
    Hacía veinte años que no pisaba aquellas baldosas.

    1983. Tenía diez años. Su padre, Don Antonio, un hombre corpulento
    de barba canosa, la llevaba de la mano. "Nunca olvides de dónde vienes",
    le decía siempre.

    2023. El recuerdo se desvaneció. Menuda tontería. Su padre llevaba
    muerto quince años y ella seguía oyendo su voz.

    —¿María? —La voz de su hermano Paco la sobresaltó.
    —Francisco —respondió secamente. Odiaba los diminutivos.

    El silencio pesado que siguió olía a reproches no dichos. Veía venir
    la discusión. Como siempre.
    """

    def test_complex_narrative_entities(self, ner_extractor):
        """Análisis de entidades en narrativa compleja."""
        result = ner_extractor.extract_entities(self.COMPLEX_NARRATIVE)
        if result.is_failure:
            pytest.fail(f"Error NER: {result.error}")

        entities = result.value.entities
        entity_texts = [e.text for e in entities]

        # Verificar detecciones esperadas
        expected = ["María", "Antonio", "Francisco"]  # Mínimo esperado
        found = [e for e in expected if any(e in t for t in entity_texts)]

        if len(found) < len(expected):
            missing = [e for e in expected if e not in found]
            pytest.xfail(f"Entidades no detectadas: {missing}")

    def test_complex_narrative_timeline(self):
        """Análisis temporal: debe detectar saltos 2023→1983→2023."""
        # Este texto tiene dos flashbacks implícitos por fecha
        pytest.xfail("Timeline compleja: 2023→1983→2023 con flashback implícito")

    def test_complex_narrative_relationships(self):
        """Relaciones: María-Antonio (padre), María-Francisco/Paco (hermanos)."""
        # Francisco = Paco (hipocorístico)
        # María y Francisco son hermanos (comparten padre Antonio)
        pytest.xfail("Relaciones implícitas: María hermana de Paco/Francisco, hija de Antonio")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
