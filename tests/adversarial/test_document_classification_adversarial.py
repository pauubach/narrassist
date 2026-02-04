"""
Tests adversariales GAN-style para clasificación de tipo de documento.

Estos tests generan casos difíciles diseñados para encontrar debilidades
en el clasificador de documentos. Categorías:

1. Documentos híbridos (memoir + self_help, fiction + essay)
2. Textos cortos/ambiguos (<500 palabras)
3. Falsos positivos (técnico con narrativa, recetas con historia)
4. Edge cases culturales (clásicos con --, traducciones)
5. Límites difusos entre tipos similares
6. CHILDREN por grupo de edad
7. Formatos especiales (DRAMA, GRAPHIC)

Cada caso incluye:
- Texto de prueba
- Tipo esperado
- Nivel de dificultad (easy, medium, hard, adversarial)
- Razón de la dificultad
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pytest

# Importar clasificador cuando esté disponible
# from src.narrative_assistant.parsers.document_classifier import (
#     classify_document,
#     DocumentType,
#     DocumentClassification,
# )


class Difficulty(Enum):
    """Nivel de dificultad del caso de prueba."""

    EASY = "easy"  # Debería clasificar correctamente
    MEDIUM = "medium"  # Puede tener algo de ambigüedad
    HARD = "hard"  # Casos límite difíciles
    ADVERSARIAL = "adversarial"  # Diseñado para engañar


@dataclass
class AdversarialCase:
    """Caso de prueba adversarial."""

    id: str
    text: str
    expected_type: str
    difficulty: Difficulty
    category: str
    reason: str
    alternative_type: Optional[str] = None  # Tipo alternativo aceptable


# =============================================================================
# CATEGORÍA 1: DOCUMENTOS HÍBRIDOS
# =============================================================================

HYBRID_CASES = [
    AdversarialCase(
        id="hybrid_001",
        text="""
        Recuerdo cuando tenía veinte años y mi vida cambió para siempre.
        Aquella mañana de primavera, decidí que era hora de tomar las riendas.

        El primer paso para cambiar tu vida es reconocer dónde estás.
        Debes preguntarte: ¿qué es lo que realmente quieres?

        Mi madre siempre decía que el éxito viene de dentro.
        Ahora sé que tenía razón. Si quieres transformar tu realidad,
        necesitas primero transformar tu mente.
        """,
        expected_type="memoir",
        difficulty=Difficulty.HARD,
        category="hybrid",
        reason="Mezcla memoir (primera persona pasado) con self_help (consejos directos)",
        alternative_type="self_help",
    ),
    AdversarialCase(
        id="hybrid_002",
        text="""
        El concepto de felicidad ha sido debatido por filósofos durante siglos.
        Aristóteles la definía como eudaimonia, una vida virtuosa.

        María se levantó aquella mañana sintiendo un vacío inexplicable.
        Miró por la ventana y pensó en todo lo que había perdido.

        Sin embargo, como argumenta Seligman (2011), la felicidad auténtica
        se construye mediante fortalezas personales, no circunstancias.
        """,
        expected_type="essay",
        difficulty=Difficulty.HARD,
        category="hybrid",
        reason="Mezcla ensayo (argumentación, citas) con ficción (personaje María)",
        alternative_type="fiction",
    ),
    AdversarialCase(
        id="hybrid_003",
        text="""
        Nací en un pequeño pueblo de Andalucía en 1985.
        Mi infancia transcurrió entre olivos y el aroma del pan recién hecho.

        Los estudios demuestran que las experiencias infantiles moldean
        nuestra personalidad adulta. Según los investigadores de Harvard,
        el 80% de nuestra autoestima se forma antes de los siete años.

        Recuerdo que mi abuela siempre me decía que yo era especial.
        """,
        expected_type="memoir",
        difficulty=Difficulty.HARD,
        category="hybrid",
        reason="Mezcla memoir con divulgación científica",
        alternative_type="divulgation",
    ),
    AdversarialCase(
        id="hybrid_004",
        text="""
        Steve Jobs nació en San Francisco en 1955, hijo adoptivo de
        Paul y Clara Jobs. Desde niño mostró interés por la electrónica.

        Si quieres ser innovador como Jobs, debes seguir estos pasos:
        1. Simplifica todo lo que hagas
        2. Enfócate en la experiencia del usuario
        3. No tengas miedo de fracasar

        Jobs falleció en 2011, pero su legado perdura en cada iPhone.
        """,
        expected_type="biography",
        difficulty=Difficulty.HARD,
        category="hybrid",
        reason="Mezcla biografía con self_help (consejos prácticos)",
        alternative_type="self_help",
    ),
]


# =============================================================================
# CATEGORÍA 2: TEXTOS CORTOS/AMBIGUOS
# =============================================================================

SHORT_AMBIGUOUS_CASES = [
    AdversarialCase(
        id="short_001",
        text="""
        El viento soplaba fuerte aquella noche.
        Las hojas caían sin cesar.
        """,
        expected_type="fiction",
        difficulty=Difficulty.ADVERSARIAL,
        category="short_ambiguous",
        reason="Solo 15 palabras, podría ser inicio de cualquier tipo narrativo",
        alternative_type="memoir",
    ),
    AdversarialCase(
        id="short_002",
        text="""
        Para ser feliz, primero debes conocerte a ti mismo.
        """,
        expected_type="self_help",
        difficulty=Difficulty.ADVERSARIAL,
        category="short_ambiguous",
        reason="Una sola oración, podría ser epígrafe o cita",
    ),
    AdversarialCase(
        id="short_003",
        text="""
        Los científicos descubrieron ayer una nueva especie de bacteria
        que podría revolucionar el tratamiento del cáncer.
        """,
        expected_type="divulgation",
        difficulty=Difficulty.MEDIUM,
        category="short_ambiguous",
        reason="Corto pero con indicadores claros de divulgación",
    ),
    AdversarialCase(
        id="short_004",
        text="""
        Prólogo

        Este libro nació de una necesidad. La necesidad de contar
        lo que nadie se atreve a decir. Espero que estas páginas
        te acompañen en tu viaje.
        """,
        expected_type="unknown",
        difficulty=Difficulty.ADVERSARIAL,
        category="short_ambiguous",
        reason="Prólogo sin contexto, podría preceder cualquier tipo de libro",
    ),
]


# =============================================================================
# CATEGORÍA 3: FALSOS POSITIVOS
# =============================================================================

FALSE_POSITIVE_CASES = [
    AdversarialCase(
        id="fp_001",
        text="""
        Capítulo 3: Configuración del Sistema

        Había una vez un servidor llamado "prometheus-01" que vivía
        en el data center norte. Cada mañana, prometheus despertaba
        y comprobaba sus métricas con alegría.

        Para configurar el servicio, ejecute:
        $ sudo systemctl start prometheus

        Prometheus pensó: "Hoy será un gran día de monitorización".
        """,
        expected_type="technical",
        difficulty=Difficulty.ADVERSARIAL,
        category="false_positive",
        reason="Manual técnico con estilo narrativo/personificado",
        alternative_type="fiction",
    ),
    AdversarialCase(
        id="fp_002",
        text="""
        Mi abuela siempre hacía esta receta en Navidad.
        Recuerdo el olor de la cocina, el calor del horno,
        y sus manos arrugadas amasando con amor.

        Ingredientes:
        - 500g de harina
        - 200g de azúcar
        - 3 huevos

        Paso 1: Mezcle la harina con el azúcar.
        Paso 2: Añada los huevos uno a uno.
        """,
        expected_type="practical",
        difficulty=Difficulty.HARD,
        category="false_positive",
        reason="Recetario con introducción tipo memoir",
        alternative_type="memoir",
    ),
    AdversarialCase(
        id="fp_003",
        text="""
        El análisis narratológico de Don Quijote revela estructuras
        complejas de metaficción. Cervantes utiliza el recurso del
        manuscrito encontrado para crear distancia irónica.

        —Yo sé quién soy —respondió don Quijote—, y sé que puedo ser
        no solo los que he dicho, sino todos los Doce Pares de Francia.

        Esta cita ejemplifica la autoconsciencia del personaje.
        """,
        expected_type="essay",
        difficulty=Difficulty.HARD,
        category="false_positive",
        reason="Paper académico sobre literatura con citas de ficción",
        alternative_type="fiction",
    ),
]


# =============================================================================
# CATEGORÍA 4: EDGE CASES CULTURALES
# =============================================================================

CULTURAL_EDGE_CASES = [
    AdversarialCase(
        id="cultural_001",
        text="""
        --¡Mia tú, que viene el tren! --gritó Bismarck desde lo alto.
        --¿Será posible? --respondió Celedonio entre airado y temeroso.
        --No, es un carca, ¿no oyes el manteo?

        La heroica ciudad dormía la siesta bajo el sol de agosto.
        El viento sur, caliente y perezoso, mecía las ramas de los olmos.
        """,
        expected_type="fiction",
        difficulty=Difficulty.MEDIUM,
        category="cultural_edge",
        reason="Estilo clásico español con -- en lugar de raya (La Regenta)",
    ),
    AdversarialCase(
        id="cultural_002",
        text="""
        En un lugar de la Mancha, de cuyo nombre no quiero acordarme,
        no ha mucho tiempo que vivía un hidalgo de los de lanza en
        astillero, adarga antigua, rocín flaco y galgo corredor.
        """,
        expected_type="fiction",
        difficulty=Difficulty.EASY,
        category="cultural_edge",
        reason="Clásico español reconocible (Don Quijote)",
    ),
    AdversarialCase(
        id="cultural_003",
        text="""
        Che, vos sabés que ayer me crucé con el Tano en la esquina.
        --¿El Tano de la verdulería? --preguntó María.
        --Ese mismo, boluda. Y me contó cada cosa...
        """,
        expected_type="fiction",
        difficulty=Difficulty.MEDIUM,
        category="cultural_edge",
        reason="Español rioplatense con voseo y lunfardo",
    ),
    AdversarialCase(
        id="cultural_004",
        text="""
        She looked at him with those piercing blue eyes.
        "I never thought it would end like this," she whispered.

        Él la miró sin comprender. El inglés nunca había sido su fuerte,
        pero entendió perfectamente el dolor en su voz.
        """,
        expected_type="fiction",
        difficulty=Difficulty.HARD,
        category="cultural_edge",
        reason="Texto bilingüe inglés-español",
    ),
]


# =============================================================================
# CATEGORÍA 5: LÍMITES DIFUSOS ENTRE TIPOS SIMILARES
# =============================================================================

FUZZY_BOUNDARY_CASES = [
    AdversarialCase(
        id="fuzzy_001",
        text="""
        Mi padre nació en 1942 en un pequeño pueblo de Galicia.
        Según me contaron mis tíos, era un hombre de pocas palabras
        pero gran corazón. Falleció cuando yo tenía solo diez años.

        En su diario, que encontré años después, escribió:
        "No sé si mis hijos entenderán algún día por qué hice lo que hice."
        """,
        expected_type="memoir",
        difficulty=Difficulty.HARD,
        category="fuzzy_boundary",
        reason="Podría ser memoir (yo) o biografía (padre como sujeto)",
        alternative_type="biography",
    ),
    AdversarialCase(
        id="fuzzy_002",
        text="""
        Los estudios demuestran que meditar 10 minutos al día
        reduce significativamente los niveles de cortisol.

        Prueba este ejercicio: siéntate cómodamente, cierra los ojos,
        y enfócate en tu respiración durante cinco minutos.

        Según investigadores de la Universidad de Stanford,
        esta práctica activa la corteza prefrontal.
        """,
        expected_type="self_help",
        difficulty=Difficulty.HARD,
        category="fuzzy_boundary",
        reason="Mezcla divulgación (estudios) con self_help (ejercicios)",
        alternative_type="divulgation",
    ),
    AdversarialCase(
        id="fuzzy_003",
        text="""
        JUAN: (Entrando por la derecha) ¿Está María?
        PEDRO: Salió hace un momento. (Pausa) ¿Querías algo?
        JUAN: Nada importante. Solo... hablar.

        (Silencio incómodo. Pedro se levanta y mira por la ventana.)

        PEDRO: El tiempo está cambiando.
        """,
        expected_type="drama",
        difficulty=Difficulty.EASY,
        category="fuzzy_boundary",
        reason="Formato dramático claro pero podría confundirse con guion",
    ),
]


# =============================================================================
# CATEGORÍA 6: CHILDREN POR GRUPO DE EDAD
# =============================================================================

CHILDREN_AGE_CASES = [
    AdversarialCase(
        id="children_001",
        text="""
        ¡Miau! ¡Miau!
        El gatito está aquí.
        ¿Dónde está mamá?
        ¡Aquí está mamá!
        """,
        expected_type="children",
        difficulty=Difficulty.EASY,
        category="children_age",
        reason="Board book (0-3 años): vocabulario mínimo, frases muy cortas",
    ),
    AdversarialCase(
        id="children_002",
        text="""
        Había una vez un osito muy pequeñito que vivía en el bosque.
        Un día, el osito salió a pasear. ¡Pum! ¡Pum! ¡Pum!
        ¿Qué era ese ruido? El osito miró y miró.
        ¡Era un conejito saltando!
        """,
        expected_type="children",
        difficulty=Difficulty.EASY,
        category="children_age",
        reason="Picture book (3-5 años): diminutivos, onomatopeyas, repeticiones",
    ),
    AdversarialCase(
        id="children_003",
        text="""
        Capítulo 1: El misterio del parque

        Lucas y Sara eran los mejores amigos del colegio.
        Un día, encontraron un mapa misterioso en el parque.

        —¿Qué crees que significa? —preguntó Sara.
        —No sé, pero vamos a averiguarlo —respondió Lucas.

        Y así comenzó su aventura.
        """,
        expected_type="children",
        difficulty=Difficulty.MEDIUM,
        category="children_age",
        reason="Middle grade (8-12 años): estructura de capítulos, diálogos, aventura",
    ),
    AdversarialCase(
        id="children_004",
        text="""
        A veces me pregunto quién soy realmente.
        En el instituto todos parecen tener las cosas claras.
        Todos excepto yo.

        Mi mejor amiga dice que soy demasiado sensible,
        pero ¿es malo sentir las cosas con intensidad?

        Esta noche hay fiesta en casa de Marcos.
        No sé si debería ir.
        """,
        expected_type="children",
        difficulty=Difficulty.HARD,
        category="children_age",
        reason="Young Adult (12+): introspección, temas adolescentes, identidad",
        alternative_type="fiction",
    ),
]


# =============================================================================
# CATEGORÍA 7: FORMATOS ESPECIALES (DRAMA, GRAPHIC)
# =============================================================================

SPECIAL_FORMAT_CASES = [
    AdversarialCase(
        id="special_001",
        text="""
        INT. APARTAMENTO DE MARÍA - NOCHE

        María entra y enciende la luz. El apartamento está vacío.

        MARÍA
        (susurrando)
        ¿Hola? ¿Hay alguien?

        Silencio. María avanza lentamente.

        CORTE A:

        INT. COCINA - CONTINUO

        Un grifo gotea. PLOP. PLOP. PLOP.
        """,
        expected_type="drama",
        difficulty=Difficulty.EASY,
        category="special_format",
        reason="Formato de guion cinematográfico con sluglines",
    ),
    AdversarialCase(
        id="special_002",
        text="""
        ACTO PRIMERO
        ESCENA I

        (Interior de una casa modesta. DOÑA ROSITA borda junto a la ventana.
        Entra EL AMA precipitadamente.)

        AMA: ¡Señorita, señorita!
        DOÑA ROSITA: ¿Qué ocurre? ¿Por qué esos gritos?
        AMA: (Jadeando) Es que... es que ha llegado una carta.
        """,
        expected_type="drama",
        difficulty=Difficulty.EASY,
        category="special_format",
        reason="Formato de teatro clásico con acotaciones",
    ),
    AdversarialCase(
        id="special_003",
        text="""
        [Viñeta 1: Plano general de la ciudad]

        NARRADOR: Era una noche oscura en Metrópolis.

        [Viñeta 2: Close-up del héroe]

        HÉROE: ¡Es hora de actuar!

        ¡WHOOOOSH!

        [Viñeta 3: El héroe vuela sobre los edificios]

        ¡CRASH! ¡BOOM! ¡POW!
        """,
        expected_type="graphic",
        difficulty=Difficulty.MEDIUM,
        category="special_format",
        reason="Formato de cómic con viñetas y onomatopeyas",
    ),
]


# =============================================================================
# COLECCIÓN COMPLETA DE CASOS
# =============================================================================

ALL_ADVERSARIAL_CASES = (
    HYBRID_CASES
    + SHORT_AMBIGUOUS_CASES
    + FALSE_POSITIVE_CASES
    + CULTURAL_EDGE_CASES
    + FUZZY_BOUNDARY_CASES
    + CHILDREN_AGE_CASES
    + SPECIAL_FORMAT_CASES
)


# =============================================================================
# FIXTURES Y TESTS
# =============================================================================


@pytest.fixture
def classifier():
    """Fixture que proporciona el clasificador de documentos."""
    # Placeholder - importar clasificador real cuando esté disponible
    # from src.narrative_assistant.parsers.document_classifier import DocumentClassifier
    # return DocumentClassifier()
    pytest.skip("Clasificador no implementado aún")


class TestDocumentClassificationAdversarial:
    """Tests adversariales para clasificación de documentos."""

    @pytest.mark.parametrize("case", ALL_ADVERSARIAL_CASES, ids=lambda c: c.id)
    def test_adversarial_case(self, classifier, case: AdversarialCase):
        """Test parametrizado para cada caso adversarial."""
        result = classifier.classify(case.text)

        # Verificar que clasifica correctamente o con tipo alternativo
        acceptable_types = [case.expected_type]
        if case.alternative_type:
            acceptable_types.append(case.alternative_type)

        assert result.document_type.value in acceptable_types, (
            f"Caso {case.id} ({case.category}, {case.difficulty.value}):\n"
            f"Esperado: {acceptable_types}\n"
            f"Obtenido: {result.document_type.value}\n"
            f"Razón de dificultad: {case.reason}\n"
            f"Confianza: {result.confidence:.2%}"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in ALL_ADVERSARIAL_CASES if c.difficulty == Difficulty.EASY],
        ids=lambda c: c.id,
    )
    def test_easy_cases_high_confidence(self, classifier, case: AdversarialCase):
        """Los casos fáciles deberían tener alta confianza."""
        result = classifier.classify(case.text)

        assert result.confidence >= 0.6, (
            f"Caso fácil {case.id} debería tener confianza >= 60%\n"
            f"Obtenido: {result.confidence:.2%}"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in ALL_ADVERSARIAL_CASES if c.difficulty == Difficulty.ADVERSARIAL],
        ids=lambda c: c.id,
    )
    def test_adversarial_cases_tracked(self, classifier, case: AdversarialCase):
        """
        Los casos adversariales pueden fallar, pero debemos trackearlos.

        Este test registra el comportamiento actual sin fallar,
        para identificar áreas de mejora.
        """
        result = classifier.classify(case.text)

        # Registrar resultado para análisis
        print(f"\n[ADVERSARIAL] {case.id}:")
        print(f"  Esperado: {case.expected_type}")
        print(f"  Obtenido: {result.document_type.value}")
        print(f"  Confianza: {result.confidence:.2%}")
        print(f"  Razón: {case.reason}")

        # No falla, solo registra


class TestDocumentClassificationByCategory:
    """Tests agrupados por categoría."""

    @pytest.mark.parametrize("case", HYBRID_CASES, ids=lambda c: c.id)
    def test_hybrid_documents(self, classifier, case: AdversarialCase):
        """Tests para documentos híbridos."""
        result = classifier.classify(case.text)

        acceptable = [case.expected_type]
        if case.alternative_type:
            acceptable.append(case.alternative_type)

        assert result.document_type.value in acceptable

    @pytest.mark.parametrize("case", CHILDREN_AGE_CASES, ids=lambda c: c.id)
    def test_children_age_groups(self, classifier, case: AdversarialCase):
        """Tests para literatura infantil por grupo de edad."""
        result = classifier.classify(case.text)

        # Primero verificar que se detecta como CHILDREN
        assert result.document_type.value == "children", (
            f"Caso {case.id} debería clasificarse como children"
        )

        # TODO: Verificar grupo de edad específico cuando esté implementado
        # assert result.age_group == expected_age_group

    @pytest.mark.parametrize("case", SPECIAL_FORMAT_CASES, ids=lambda c: c.id)
    def test_special_formats(self, classifier, case: AdversarialCase):
        """Tests para formatos especiales (drama, graphic)."""
        result = classifier.classify(case.text)

        assert result.document_type.value == case.expected_type


class TestClassifierRobustness:
    """Tests de robustez del clasificador."""

    def test_empty_text(self, classifier):
        """El clasificador debe manejar texto vacío."""
        result = classifier.classify("")
        assert result.document_type.value == "unknown"

    def test_very_short_text(self, classifier):
        """El clasificador debe manejar texto muy corto."""
        result = classifier.classify("Hola mundo.")
        assert result.document_type.value == "unknown"
        assert result.confidence < 0.5

    def test_repeated_patterns(self, classifier):
        """El clasificador no debe dejarse engañar por patrones repetidos."""
        # Texto que repite un patrón de self-help artificialmente
        spam_text = "Debes ser feliz. " * 100
        result = classifier.classify(spam_text)

        # La confianza no debería ser artificialmente alta
        # por repetición del mismo patrón
        assert result.confidence < 0.9

    def test_mixed_language(self, classifier):
        """El clasificador debe manejar texto con mezcla de idiomas."""
        text = """
        This is a test. Esto es una prueba.
        We need to verify comportamiento mixto.
        """
        result = classifier.classify(text)
        # No debe crashear, aunque la clasificación sea incierta
        assert result is not None


# =============================================================================
# UTILIDADES PARA ANÁLISIS
# =============================================================================


def analyze_adversarial_results(classifier, cases=ALL_ADVERSARIAL_CASES):
    """
    Analiza resultados de casos adversariales para identificar patrones de fallo.

    Retorna estadísticas por categoría y dificultad.
    """
    results = {
        "by_category": {},
        "by_difficulty": {},
        "failures": [],
    }

    for case in cases:
        result = classifier.classify(case.text)

        acceptable = [case.expected_type]
        if case.alternative_type:
            acceptable.append(case.alternative_type)

        is_correct = result.document_type.value in acceptable

        # Por categoría
        if case.category not in results["by_category"]:
            results["by_category"][case.category] = {"correct": 0, "total": 0}
        results["by_category"][case.category]["total"] += 1
        if is_correct:
            results["by_category"][case.category]["correct"] += 1

        # Por dificultad
        diff_key = case.difficulty.value
        if diff_key not in results["by_difficulty"]:
            results["by_difficulty"][diff_key] = {"correct": 0, "total": 0}
        results["by_difficulty"][diff_key]["total"] += 1
        if is_correct:
            results["by_difficulty"][diff_key]["correct"] += 1

        # Registrar fallos
        if not is_correct:
            results["failures"].append(
                {
                    "id": case.id,
                    "expected": case.expected_type,
                    "got": result.document_type.value,
                    "confidence": result.confidence,
                    "reason": case.reason,
                }
            )

    return results


if __name__ == "__main__":
    # Ejecutar análisis cuando se corra directamente
    print("Ejecutando análisis de casos adversariales...")
    print(f"Total de casos: {len(ALL_ADVERSARIAL_CASES)}")
    print("\nPor categoría:")
    for category in set(c.category for c in ALL_ADVERSARIAL_CASES):
        count = len([c for c in ALL_ADVERSARIAL_CASES if c.category == category])
        print(f"  {category}: {count}")
    print("\nPor dificultad:")
    for diff in Difficulty:
        count = len([c for c in ALL_ADVERSARIAL_CASES if c.difficulty == diff])
        print(f"  {diff.value}: {count}")
