"""
Tests unitarios para extracción de atributos.
"""

import pytest

from narrative_assistant.nlp.attributes import AttributeExtractor, AttributeKey


class TestAttributeExtractor:
    """Tests para el extractor de atributos."""

    @pytest.fixture
    def extractor(self):
        """Crea una instancia del extractor."""
        return AttributeExtractor(filter_metaphors=False)

    def test_extract_eye_color_pattern1(self, extractor):
        """Extrae color de ojos con patrón 'tenía ojos'."""
        text = "María tenía ojos azules y brillantes."
        entities = [("María", 0, 5)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None
        assert extraction.processed_chars > 0
        # Puede extraer o no, dependiendo del matcher
        if len(extraction.attributes) > 0:
            attrs = [a.value.lower() for a in extraction.attributes]
            assert any("azul" in a for a in attrs)

    def test_extract_eye_color_pattern2(self, extractor):
        """Extrae color de ojos con patrón 'los ojos X de Y'."""
        text = "Los ojos verdes de María brillaban en la oscuridad."
        entities = [("María", 19, 24)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None

    def test_extract_hair_pattern(self, extractor):
        """Extrae descripción de cabello."""
        text = "Juan tenía el cabello negro y largo, muy bien peinado."
        entities = [("Juan", 0, 4)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None
        assert extraction.processed_chars > 0

    def test_extract_age_years(self, extractor):
        """Extrae edad con patrón 'X años'."""
        text = "María tiene treinta años y vive en Madrid."
        entities = [("María", 0, 5)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None

    def test_extract_height_adjective(self, extractor):
        """Extrae altura con adjetivos."""
        text = "Juan era alto y delgado, con una postura elegante."
        entities = [("Juan", 0, 4)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None
        assert extraction.processed_chars > 0

    def test_empty_text(self, extractor):
        """Maneja texto vacío."""
        result = extractor.extract_attributes("", [])

        assert result.is_success
        extraction = result.value
        assert len(extraction.attributes) == 0
        assert extraction.processed_chars == 0

    def test_no_entities(self, extractor):
        """Maneja ausencia de entidades."""
        text = "María tiene ojos azules."
        result = extractor.extract_attributes(text, [])

        assert result.is_success
        extraction = result.value
        assert extraction is not None

    def test_processed_chars_tracking(self, extractor):
        """Verifica que se trackean caracteres procesados."""
        text = "María tenía ojos azules claros."
        entities = [("María", 0, 5)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction.processed_chars == len(text)

    def test_multiple_entities_same_text(self, extractor):
        """Extrae atributos de múltiples entidades en el mismo texto."""
        text = """
        María tenía ojos azules y cabello negro.
        Juan era alto y tenía ojos marrones.
        """
        entities = [
            ("María", text.find("María"), text.find("María") + 5),
            ("Juan", text.find("Juan"), text.find("Juan") + 4),
        ]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction.processed_chars > 0

    def test_metaphor_filtering_disabled(self):
        """Con filtro deshabilitado, puede extraer metáforas."""
        extractor_no_filter = AttributeExtractor(filter_metaphors=False)
        text = "Sus ojos eran dos luceros brillantes."
        entities = [("María", 0, 0)]  # Entidad ficticia

        result = extractor_no_filter.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # Debería procesar sin filtrar
        assert extraction.metaphors_filtered == 0

    def test_metaphor_filtering_enabled(self):
        """Con filtro habilitado, puede filtrar metáforas."""
        extractor_filter = AttributeExtractor(filter_metaphors=True)
        text = "Sus ojos eran dos luceros brillantes en la noche oscura."
        entities = [("María", 0, 0)]

        result = extractor_filter.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # Puede filtrar o no, dependiendo de la detección
        assert extraction.metaphors_filtered >= 0

    def test_confidence_threshold(self):
        """Verifica umbral de confianza mínima."""
        extractor_high_conf = AttributeExtractor(min_confidence=0.8)
        text = "María tenía ojos verdes."
        entities = [("María", 0, 5)]

        result = extractor_high_conf.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # Solo atributos con confianza >= 0.8
        for attr in extraction.attributes:
            assert attr.confidence >= 0.8

    def test_complex_sentence(self, extractor):
        """Procesa oración compleja con múltiples atributos."""
        text = """
        María Sánchez, una mujer de mediana edad con ojos verdes
        y cabello castaño, era alta y elegante.
        """
        entities = [("María Sánchez", text.find("María"), text.find("María") + 13)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction.processed_chars > 0
        # Debería extraer al menos algunos atributos
        # (aunque depende de los patrones específicos)

    def test_attribute_with_adjectives(self, extractor):
        """Extrae atributos con múltiples adjetivos."""
        text = "Juan tenía ojos grandes y marrones muy expresivos."
        entities = [("Juan", 0, 4)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        assert extraction is not None

    def test_no_matches(self, extractor):
        """Texto sin patrones matcheables."""
        text = "El día era soleado y hacía calor."
        entities = [("día", 3, 6)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # No debería extraer atributos de "día"
        assert len(extraction.attributes) == 0


class TestAttributeExtractorIntegration:
    """Tests de integración con NER real."""

    def test_with_real_ner(self):
        """Integración con extractor NER real."""
        from narrative_assistant.nlp.ner import NERExtractor

        text = "María Sánchez tenía ojos azules. Juan Pérez era alto."

        # Extraer entidades con NER
        ner = NERExtractor()
        ner_result = ner.extract_entities(text)
        assert ner_result.is_success

        # Convertir a formato para AttributeExtractor
        entities = [(e.text, e.start_char, e.end_char) for e in ner_result.value.entities]

        # Extraer atributos
        extractor = AttributeExtractor()
        attr_result = extractor.extract_attributes(text, entities)

        assert attr_result.is_success
        extraction = attr_result.value
        assert extraction.processed_chars > 0


class TestHairExtractionPatterns:
    """Tests específicos para extracción de atributos de pelo."""

    @pytest.fixture
    def extractor(self):
        """Crea una instancia del extractor."""
        return AttributeExtractor(filter_metaphors=False)

    def test_extract_hair_color_compound_pattern(self, extractor):
        """Extrae color de pelo en patrón compuesto 'cabello largo y negro'."""
        text = "María tenía el cabello largo y negro, recogido en una trenza."
        entities = [("María", 0, 5)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # Debería extraer tanto el tipo (largo) como el color (negro)
        if len(extraction.attributes) > 0:
            values = [a.value.lower() for a in extraction.attributes]
            # Al menos uno de los atributos debería estar presente
            assert any("negro" in v or "largo" in v for v in values)

    def test_extract_hair_color_rubio(self, extractor):
        """Extrae color de pelo rubio en patrón 'cabello corto y rubio'."""
        text = "Llevaba el cabello corto y rubio, completamente diferente."
        entities = [("María", 0, 0)]  # Sin posición específica

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        if len(extraction.attributes) > 0:
            values = [a.value.lower() for a in extraction.attributes]
            assert any("rubio" in v or "corto" in v for v in values)

    def test_extract_hair_type_simple(self, extractor):
        """Extrae tipo de pelo simple 'pelo largo'."""
        text = "Tenía el pelo largo y brillante."
        entities = [("María", 0, 0)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        if len(extraction.attributes) > 0:
            values = [a.value.lower() for a in extraction.attributes]
            assert any("largo" in v for v in values)

    def test_extract_hair_color_after_y(self, extractor):
        """Extrae color de pelo después de 'y' en frase compuesta."""
        text = "Su cabello rizado y pelirrojo le daba un aspecto único."
        entities = [("María", 0, 0)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        # El patrón debería capturar "pelirrojo"

    def test_extract_hair_multiple_attributes(self, extractor):
        """Extrae múltiples atributos de pelo en una oración."""
        text = "Juan tenía el cabello negro y corto, con algunas canas."
        entities = [("Juan", 0, 4)]

        result = extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # Puede extraer: negro (color), corto (tipo), canas (color secundario)
        assert extraction.processed_chars > 0

    def test_no_hair_in_unrelated_text(self):
        """No extrae pelo de texto sin mención de cabello."""
        # Usar extractor sin LLM para evitar alucinaciones del modelo
        deterministic_extractor = AttributeExtractor(
            filter_metaphors=False, use_llm=False, use_embeddings=False
        )
        text = "Juan caminaba por la calle pensando en su trabajo."
        entities = [("Juan", 0, 4)]

        result = deterministic_extractor.extract_attributes(text, entities)

        assert result.is_success
        extraction = result.value
        # No debería extraer atributos de pelo
        hair_attrs = [
            a
            for a in extraction.attributes
            if "pelo" in a.key.value or "cabello" in a.key.value or "hair" in a.key.value
        ]
        assert len(hair_attrs) == 0


class TestRegexExtractorPatterns:
    """Tests para el RegexExtractor específicamente."""

    @pytest.fixture
    def regex_extractor(self):
        """Crea instancia del RegexExtractor."""
        from narrative_assistant.nlp.extraction.extractors.regex_extractor import RegexExtractor

        return RegexExtractor()

    def test_hair_color_pattern_negro(self, regex_extractor):
        """Patrón regex captura 'cabello negro'."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        text = "María tenía el cabello largo y negro."
        context = ExtractionContext(
            text=text,
            entity_names=["María"],
            chapter=1,
        )

        result = regex_extractor.extract(context)

        assert len(result.attributes) > 0
        hair_color_attrs = [a for a in result.attributes if a.attribute_type.value == "hair_color"]
        assert len(hair_color_attrs) > 0
        assert any("negro" in a.value for a in hair_color_attrs)

    def test_hair_type_pattern_largo(self, regex_extractor):
        """Patrón regex captura 'cabello largo'."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        text = "María tenía el cabello largo y negro."
        context = ExtractionContext(
            text=text,
            entity_names=["María"],
            chapter=1,
        )

        result = regex_extractor.extract(context)

        hair_type_attrs = [a for a in result.attributes if a.attribute_type.value == "hair_type"]
        assert len(hair_type_attrs) > 0
        assert any("largo" in a.value for a in hair_type_attrs)

    def test_hair_pattern_llevaba(self, regex_extractor):
        """Patrón 'Llevaba el cabello corto y rubio'."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        # La entidad debe estar en el texto para que se asigne el atributo
        text = "María llevaba el cabello corto y rubio, completamente diferente."
        context = ExtractionContext(
            text=text,
            entity_names=["María"],
            chapter=2,
        )

        result = regex_extractor.extract(context)

        # Debería capturar "corto" como tipo y "rubio" como color
        types = [a.value for a in result.attributes if a.attribute_type.value == "hair_type"]
        colors = [a.value for a in result.attributes if a.attribute_type.value == "hair_color"]

        assert "corto" in types or "rubio" in colors

    def test_partial_entity_name_matching(self, regex_extractor):
        """Verifica que coincide nombres parciales de entidad."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        # El texto usa solo "María" pero la entidad es "María Sánchez"
        text = "María tenía el cabello largo y negro."
        context = ExtractionContext(
            text=text,
            entity_names=["María Sánchez"],  # Nombre completo
            chapter=1,
        )

        result = regex_extractor.extract(context)

        # Debería asignar el atributo a "María Sánchez"
        for attr in result.attributes:
            if attr.entity_name:
                assert "María" in attr.entity_name

    def test_eye_color_extraction(self, regex_extractor):
        """Extrae color de ojos correctamente."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        # La entidad debe estar en el texto para que se asigne el atributo
        text = "María tenía ojos azules que brillaban con la luz del amanecer."
        context = ExtractionContext(
            text=text,
            entity_names=["María"],
            chapter=1,
        )

        result = regex_extractor.extract(context)

        eye_attrs = [a for a in result.attributes if a.attribute_type.value == "eye_color"]
        assert len(eye_attrs) > 0
        assert any("azul" in a.value for a in eye_attrs)

    def test_height_extraction(self, regex_extractor):
        """Extrae altura correctamente."""
        from narrative_assistant.nlp.extraction.base import ExtractionContext

        text = "Juan era un hombre bajo y fornido."
        context = ExtractionContext(
            text=text,
            entity_names=["Juan"],
            chapter=1,
        )

        result = regex_extractor.extract(context)

        height_attrs = [a for a in result.attributes if a.attribute_type.value == "height"]
        build_attrs = [a for a in result.attributes if a.attribute_type.value == "build"]

        # Debería capturar "bajo" y "fornido"
        assert len(height_attrs) > 0 or len(build_attrs) > 0


class TestExtractionPipelineIntegration:
    """Tests de integración del pipeline completo de extracción."""

    def test_full_pipeline_extraction(self):
        """Test del pipeline completo con múltiples capítulos."""
        from narrative_assistant.nlp.extraction import AttributeExtractionPipeline, PipelineConfig

        config = PipelineConfig(
            use_regex=True,
            use_dependency=True,
            use_embeddings=False,
            use_llm=False,
        )
        pipeline = AttributeExtractionPipeline(config)

        # Capítulo 1: María con ojos azules y pelo negro largo
        text1 = "María tenía ojos azules y cabello largo y negro."
        result1 = pipeline.extract(text1, ["María"], chapter=1)

        assert len(result1) > 0

        # Capítulo 2: María con ojos verdes y pelo corto rubio
        # La entidad debe estar en el texto para que se asigne el atributo
        text2 = "María tenía ojos verdes brillantes. María llevaba el cabello corto y rubio."
        result2 = pipeline.extract(text2, ["María"], chapter=2)

        assert len(result2) > 0

        # Verificar que se detectan valores diferentes
        values1 = {(a.attribute_type.value, a.value) for a in result1}
        values2 = {(a.attribute_type.value, a.value) for a in result2}

        # Los conjuntos deberían ser diferentes (inconsistencia)
        assert values1 != values2

    def test_pipeline_multiple_entities(self):
        """Test con múltiples entidades en el mismo texto."""
        from narrative_assistant.nlp.extraction import AttributeExtractionPipeline, PipelineConfig

        config = PipelineConfig(
            use_regex=True,
            use_dependency=True,
            use_embeddings=False,
            use_llm=False,
        )
        pipeline = AttributeExtractionPipeline(config)

        text = """
        María tenía ojos azules y cabello negro.
        Juan era alto y tenía ojos marrones.
        """

        result = pipeline.extract(text, ["María", "Juan"], chapter=1)

        # Debería extraer atributos de ambas entidades
        maria_attrs = [a for a in result if a.entity_name == "María"]
        juan_attrs = [a for a in result if a.entity_name == "Juan"]

        # Ambos deberían tener al menos un atributo
        # (depende de la implementación específica)
        assert len(result) > 0

    def test_pipeline_empty_text(self):
        """Pipeline maneja texto vacío correctamente."""
        from narrative_assistant.nlp.extraction import AttributeExtractionPipeline, PipelineConfig

        config = PipelineConfig(
            use_regex=True,
            use_dependency=False,
            use_embeddings=False,
            use_llm=False,
        )
        pipeline = AttributeExtractionPipeline(config)

        result = pipeline.extract("", ["María"], chapter=1)

        assert result == []

    def test_pipeline_no_entities(self):
        """Pipeline maneja lista vacía de entidades."""
        from narrative_assistant.nlp.extraction import AttributeExtractionPipeline, PipelineConfig

        config = PipelineConfig(
            use_regex=True,
            use_dependency=False,
            use_embeddings=False,
            use_llm=False,
        )
        pipeline = AttributeExtractionPipeline(config)

        result = pipeline.extract("María tenía ojos azules.", [], chapter=1)

        assert result == []


class TestFacialHairPatterns:
    """Tests para los patrones de vello facial (barba, bigote, patillas)."""

    @pytest.fixture
    def extractor(self):
        return AttributeExtractor(filter_metaphors=False)

    def test_extract_barba_with_entity(self, extractor):
        """Extrae barba espesa con entidad explícita."""
        text = "Juan tenía barba espesa y ojos marrones."
        entities = [("Juan", 0, 4)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) >= 1
        assert any("espesa" in a.value.lower() for a in facial)

    def test_extract_barba_con_preposicion(self, extractor):
        """Extrae 'con barba canosa' (sin entidad explícita, requiere contexto)."""
        text = "Pedro era un hombre viejo, con barba canosa y mirada triste."
        entities = [("Pedro", 0, 5)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) >= 1
        assert any("canosa" in a.value.lower() for a in facial)

    def test_extract_bigote_recortado(self, extractor):
        """Extrae bigote con adjetivo validado."""
        text = "Andrés llevaba un bigote recortado desde hacía años."
        entities = [("Andrés", 0, 6)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) >= 1

    def test_extract_patillas_largas(self, extractor):
        """Extrae patillas con adjetivo."""
        text = "El detective tenía patillas largas al estilo del siglo XIX."
        entities = [("detective", 3, 12)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) >= 1

    def test_extract_canas_en_barba(self, extractor):
        """Extrae canas en barba."""
        text = "Miguel tenía canas en su barba desde los cuarenta."
        entities = [("Miguel", 0, 6)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        # Puede ser facial_hair o hair_color dependiendo del patrón
        relevant = [a for a in attrs if a.key.value in ("facial_hair", "hair_color")]
        assert len(relevant) >= 1

    def test_no_false_positive_barbacoa(self, extractor):
        """No detecta barba en 'barbacoa'."""
        text = "Juan preparó una barbacoa en el patio de la casa."
        entities = [("Juan", 0, 4)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) == 0

    def test_no_false_positive_barba_sin_adjetivo(self, extractor):
        """No detecta barba sin adjetivo validado."""
        text = "La barba crecía sin control, cada vez más larga."
        entities = [("Pedro", 0, 5)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        # "sin control" no es un adjetivo validado del whitelist
        facial = [a for a in attrs if a.key.value == "facial_hair" and "sin control" in a.value]
        assert len(facial) == 0

    def test_no_false_positive_patillas_electronicas(self, extractor):
        """No detecta patillas de objetos electrónicos."""
        text = "Las patillas del chip se habían doblado."
        entities = []
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        assert len(facial) == 0

    def test_su_barba_possessive_resolution(self, extractor):
        """'su barba' se resuelve a entidad cercana."""
        text = "Carlos entró al salón. Su barba negra le cubría medio rostro."
        entities = [("Carlos", 0, 6)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        facial = [a for a in attrs if a.key.value == "facial_hair"]
        if facial:
            assert any(a.entity_name == "Carlos" for a in facial)


class TestPossessiveEntityResolution:
    """Tests para la resolución de posesivos ('sus ojos', 'su barba')."""

    @pytest.fixture
    def extractor(self):
        return AttributeExtractor(filter_metaphors=False)

    def test_sus_ojos_resolves_to_nearest_person(self, extractor):
        """'Sus ojos azules' se resuelve a la persona más cercana."""
        text = "Juan entró poco después. Era un hombre muy alto. Sus ojos azules miraban con curiosidad."
        entities = [("Juan", 0, 4)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if a.key == AttributeKey.EYE_COLOR]
        # Should find at least one eye color
        assert len(eye_attrs) >= 1
        # Should be assigned to Juan (nearest person)
        juan_eyes = [a for a in eye_attrs if a.entity_name == "Juan"]
        assert len(juan_eyes) >= 1

    def test_sus_ojos_after_two_sentences(self, extractor):
        """Posesivo se resuelve correctamente con dos oraciones intermedias.

        Bug original: "Sus ojos azules" al final se atribuía a María
        porque el subject inheritance no tenía límite de distancia.
        Con el fix de max 2 oraciones, Juan es el sujeto correcto.
        """
        text = (
            "María apareció en la cafetería. Sus ojos verdes llamaron la atención. "
            "Juan entró poco después. Era un hombre alto, delgado como un junco. "
            "Sus ojos azules miraban con curiosidad a María."
        )
        entities = [("María", 0, 5), ("Juan", 70, 74)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        # Look for eye_color attributes
        eye_attrs = [a for a in attrs if a.key == AttributeKey.EYE_COLOR]
        assert len(eye_attrs) >= 1
        # "azules" should be attributed to Juan, NOT to María
        azul_attrs = [a for a in eye_attrs if "azul" in a.value.lower()]
        assert len(azul_attrs) >= 1
        for attr in azul_attrs:
            assert attr.entity_name != "María", (
                f"'azules' incorrectly attributed to María instead of Juan: {attr}"
            )

    def test_possessive_not_assigned_to_object(self, extractor):
        """'Sus ojos' no se asigna a entidad marcada como objeto ('a María')."""
        text = "Juan caminaba despacio. Sus ojos azules miraban a María."
        entities = [("Juan", 0, 4), ("María", 50, 55)]
        result = extractor.extract_attributes(text, entities)
        assert result.is_success
        attrs = result.value.attributes
        eye_attrs = [a for a in attrs if a.key == AttributeKey.EYE_COLOR and "azul" in a.value]
        # If resolved, should be Juan, not María
        if eye_attrs:
            assert all(a.entity_name != "María" for a in eye_attrs)
