"""
Extractor basado en análisis de dependencias de spaCy.

Este extractor analiza la estructura gramatical del texto
para extraer atributos sin depender de patrones literales.

Ventajas sobre regex:
- Más generalizable a diferentes estilos de escritura
- Entiende relaciones gramaticales
- Mejor manejo de oraciones complejas
"""

import logging
from typing import Any

from ...title_preprocessor import preprocess_text_for_spacy
from ..base import (
    AttributeType,
    BaseExtractor,
    ExtractedAttribute,
    ExtractionContext,
    ExtractionMethod,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


# Vocabularios para clasificación semántica
PHYSICAL_DESCRIPTORS = {
    "eye_color": {
        "azul",
        "azules",
        "verde",
        "verdes",
        "marrón",
        "marrones",
        "negro",
        "negros",
        "gris",
        "grises",
        "avellana",
        "miel",
        "castaño",
        "castaños",
        "ámbar",
        "violeta",
        "violetas",
    },
    "hair_color": {
        "negro",
        "rubio",
        "castaño",
        "pelirrojo",
        "canoso",
        "blanco",
        "moreno",
        "gris",
        "rojizo",
        "dorado",
        "oscuro",
        "claro",
        "platino",
        "cobrizo",
        "azabache",
    },
    "hair_type": {
        "largo",
        "corto",
        "liso",
        "rizado",
        "ondulado",
        "recogido",
        "suelto",
        "trenzado",
        "rapado",
        "calvo",
        "espeso",
        "fino",
    },
    "height": {
        "alto",
        "alta",
        "bajo",
        "baja",
        "muy alto",
        "muy alta",
        "bajito",
        "bajita",
        "gigante",
        "enano",
        "enana",
    },
    "build": {
        "delgado",
        "delgada",
        "gordo",
        "gorda",
        "fornido",
        "fornida",
        "esbelto",
        "esbelta",
        "robusto",
        "robusta",
        "musculoso",
        "musculosa",
        "atlético",
        "atlética",
        "corpulento",
        "corpulenta",
        "flaco",
        "flaca",
    },
    "age": {
        "joven",
        "viejo",
        "vieja",
        "anciano",
        "anciana",
        "niño",
        "niña",
        "adolescente",
        "adulto",
        "adulta",
        "mayor",
    },
    "skin": {
        "pálido",
        "pálida",
        "moreno",
        "morena",
        "bronceado",
        "bronceada",
        "claro",
        "clara",
        "oscuro",
        "oscura",
        "pecoso",
        "pecosa",
        "escamosa",
        "escamoso",  # Para fantasy/sci-fi
    },
}

# Mapeo de parte del cuerpo a tipo de atributo
BODY_PARTS_TO_ATTR = {
    "ojos": AttributeType.EYE_COLOR,
    "ojo": AttributeType.EYE_COLOR,
    "cabello": AttributeType.HAIR_COLOR,
    "pelo": AttributeType.HAIR_COLOR,
    "melena": AttributeType.HAIR_COLOR,
    "piel": AttributeType.SKIN,
    "rostro": AttributeType.SKIN,
    "barba": AttributeType.HAIR_COLOR,
    "bigote": AttributeType.HAIR_COLOR,
}

# Partes del cuerpo que pueden tener tipo (largo/corto)
BODY_PARTS_WITH_TYPE = {
    "cabello": AttributeType.HAIR_TYPE,
    "pelo": AttributeType.HAIR_TYPE,
    "melena": AttributeType.HAIR_TYPE,
    "barba": AttributeType.HAIR_TYPE,
}

# Verbos que introducen descripciones
DESCRIPTION_VERBS = {"ser", "estar", "tener", "llevar", "parecer", "lucir"}


class DependencyExtractor(BaseExtractor):
    """
    Extractor de atributos usando análisis de dependencias de spaCy.

    Analiza la estructura gramatical para detectar:
    - Estructuras copulativas: "María era alta"
    - Estructuras posesivas: "María tenía ojos azules"
    - Modificadores: "los ojos verdes de María"
    - Posesivos pronominales: "sus ojos brillaban"

    Example:
        >>> extractor = DependencyExtractor()
        >>> context = ExtractionContext(
        ...     text="María era alta y tenía los ojos azules.",
        ...     entity_names=["María"]
        ... )
        >>> result = extractor.extract(context)
        >>> for attr in result.attributes:
        ...     print(f"{attr.entity_name}: {attr.attribute_type.value} = {attr.value}")
    """

    def __init__(self):
        """Inicializa el extractor."""
        self._nlp = None

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            from ...spacy_gpu import load_spacy_model

            self._nlp = load_spacy_model()
        return self._nlp

    @property
    def method(self) -> ExtractionMethod:
        return ExtractionMethod.DEPENDENCY

    @property
    def supported_attributes(self) -> set[AttributeType]:
        return {
            AttributeType.EYE_COLOR,
            AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE,
            AttributeType.HEIGHT,
            AttributeType.BUILD,
            AttributeType.AGE,
            AttributeType.SKIN,
            AttributeType.DISTINCTIVE_FEATURE,
        }

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Dependency parsing funciona bien para la mayoría de textos.
        """
        word_count = len(context.text.split())

        # Bueno para textos de tamaño medio
        if 20 <= word_count <= 500:
            return 0.8

        # Menos eficiente para textos muy cortos o muy largos
        if word_count < 20:
            return 0.6
        if word_count > 500:
            return 0.7

        return 0.75

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos usando análisis de dependencias.

        MEJORA: Preprocesa el texto para eliminar títulos de capítulos
        que confunden el análisis sintáctico de spaCy.
        """
        attributes = []
        errors = []

        try:
            # Usar doc pre-procesado si existe, sino procesar
            if context.doc is not None:
                doc = context.doc
            else:
                # Preprocesar texto para eliminar títulos que confunden spaCy
                clean_text = preprocess_text_for_spacy(context.text)
                doc = self.nlp(clean_text)

            # Normalizar nombres de entidades
            entity_names_lower = {name.lower() for name in context.entity_names}

            # Estrategia 1: Estructuras copulativas (ser/estar + ADJ)
            attributes.extend(self._extract_copulative(doc, entity_names_lower, context.chapter))

            # Estrategia 2: Estructuras posesivas (tener + NOUN + ADJ)
            attributes.extend(self._extract_possession(doc, entity_names_lower, context.chapter))

            # Estrategia 3: "ADJ de ENTIDAD" (los ojos verdes de María)
            attributes.extend(self._extract_adjective_of(doc, entity_names_lower, context.chapter))

            # Estrategia 4: Posesivos pronominales (sus ojos azules)
            attributes.extend(self._extract_possessive(doc, entity_names_lower, context.chapter))

            # Estrategia 5: Enumeraciones de adjetivos
            attributes.extend(self._extract_enumerations(doc, entity_names_lower, context.chapter))

            # Estrategia 6: Patrones preposicionales (con ojos marrones)
            attributes.extend(self._extract_prepositional(doc, entity_names_lower, context.chapter))

            # Estrategia 7: Fragmentos nominales (Cabello negro y largo, ojos azules)
            attributes.extend(
                self._extract_noun_fragments(doc, entity_names_lower, context.chapter)
            )

            # Separar atributos compuestos
            attributes = self._separate_compound_attributes(attributes)

            # Deduplicar
            attributes = self._deduplicate(attributes)

            logger.debug(f"DependencyExtractor found {len(attributes)} attributes")

        except Exception as e:
            errors.append(f"Error in dependency extraction: {str(e)}")
            logger.exception("Error in dependency extraction")

        return self._create_result(attributes, errors)

    def _extract_copulative(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras copulativas.

        MEJORA: Usa tracking de sujeto por oración para manejar casos
        con sujeto tácito como: "María entró. Era alta." -> María.height = alta

        Patrones:
        - "María era alta" -> María.height = alta
        - "Juan era un hombre bajo" -> Juan.height = bajo
        - "Ella parecía joven" -> (entidad previa).age = joven
        """
        attributes = []

        # Mapear cada oración a su sujeto
        sentence_subjects: dict[int, str | None] = {}
        last_subject = None

        for sent in doc.sents:
            subject = self._find_sentence_subject(sent, entity_names)
            if subject:
                last_subject = subject
            sentence_subjects[sent.start] = last_subject

        # Ahora buscar verbos copulativos en cada oración
        for sent in doc.sents:
            sent_subject = sentence_subjects.get(sent.start)

            for token in sent:
                # Buscar verbos copulativos
                if token.lemma_ not in {"ser", "estar", "parecer"} or token.pos_ not in {
                    "AUX",
                    "VERB",
                }:
                    continue

                # Buscar sujeto explícito primero
                explicit_subject = self._find_subject(token)
                entity_name = None

                if explicit_subject:
                    subject_text = explicit_subject.text.lower()
                    if subject_text in entity_names:
                        entity_name = explicit_subject.text
                    elif explicit_subject.pos_ == "PRON":
                        # Resolver pronombre a última entidad
                        entity_name = self._resolve_pronoun(doc, explicit_subject, entity_names)
                    else:
                        # Buscar coincidencia parcial
                        for name in entity_names:
                            if subject_text in name or name in subject_text:
                                entity_name = name
                                break

                # Si no hay sujeto explícito o pronombre, usar el sujeto de la oración
                if not entity_name:
                    entity_name = sent_subject

                if not entity_name:
                    continue

                # Buscar atributo predicativo (adjetivo)
                for child in token.head.children if token.dep_ == "cop" else token.children:
                    if child.pos_ == "ADJ":
                        # Extraer este adjetivo y cualquier anidado (coordinados O modificadores)
                        # "alto, delgado" -> delgado puede ser conj o amod de alto
                        for adj_token in [child] + [
                            gc
                            for gc in child.children
                            if gc.dep_ in {"conj", "amod"} and gc.pos_ == "ADJ"
                        ]:
                            attr_type = self._classify_attribute(adj_token.text)
                            if attr_type:
                                attributes.append(
                                    self._create_attribute(
                                        entity_name=entity_name,
                                        attr_type=attr_type,
                                        value=adj_token.text.lower(),
                                        confidence=0.85,
                                        source_text=sent.text,
                                        chapter=chapter,
                                    )
                                )
                    # Buscar en "era un hombre alto y fornido"
                    elif child.pos_ == "NOUN":
                        # Usar _collect_adjectives para obtener coordinados
                        for adj_token in self._collect_adjectives(child):
                            attr_type = self._classify_attribute(adj_token.text)
                            if attr_type:
                                attributes.append(
                                    self._create_attribute(
                                        entity_name=entity_name,
                                        attr_type=attr_type,
                                        value=adj_token.text.lower(),
                                        confidence=0.80,
                                        source_text=sent.text,
                                        chapter=chapter,
                                    )
                                )

        return attributes

    def _extract_possession(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras posesivas.

        MEJORA: Usa tracking de sujeto por oración en lugar de requerir
        sujeto explícito en cada oración. Esto maneja casos como:
        "María entró en la casa de Juan. Tenía los ojos azules." -> María

        Patrones:
        - "María tenía los ojos azules" -> María.eye_color = azules
        - "Juan tenía el cabello negro" -> Juan.hair_color = negro
        """
        attributes = []

        # Mapear cada oración a su sujeto (igual que _extract_possessive)
        sentence_subjects: dict[int, str | None] = {}
        last_subject = None

        for sent in doc.sents:
            subject = self._find_sentence_subject(sent, entity_names)
            if subject:
                last_subject = subject
            sentence_subjects[sent.start] = last_subject

        # Ahora buscar verbos de posesión en cada oración
        for sent in doc.sents:
            sent_subject = sentence_subjects.get(sent.start)

            for token in sent:
                # Buscar "tener" o "llevar"
                if token.lemma_ not in {"tener", "llevar"} or token.pos_ != "VERB":
                    continue

                # Buscar sujeto explícito primero
                explicit_subject = None
                obj = None

                for child in token.children:
                    if child.dep_ == "nsubj":
                        explicit_subject = child
                    elif child.dep_ in {"obj", "dobj"}:
                        obj = child

                # Determinar la entidad: preferir sujeto explícito, sino usar sujeto de oración
                entity_name = None

                if explicit_subject:
                    subject_text = explicit_subject.text.lower()
                    if subject_text in entity_names:
                        entity_name = explicit_subject.text
                    else:
                        for name in entity_names:
                            if subject_text in name or name in subject_text:
                                entity_name = name
                                break

                # Si no hay sujeto explícito, usar el sujeto de la oración
                if not entity_name:
                    entity_name = sent_subject

                if not entity_name or not obj:
                    continue

                # Verificar si el objeto es una parte del cuerpo
                obj_lemma = obj.lemma_.lower()

                if obj_lemma in BODY_PARTS_TO_ATTR:
                    base_attr_type = BODY_PARTS_TO_ATTR[obj_lemma]
                    type_attr = BODY_PARTS_WITH_TYPE.get(obj_lemma)

                    # Buscar adjetivos que modifican el objeto (incluyendo coordinados)
                    for adj_token in self._collect_adjectives(obj):
                        adj_lower = adj_token.text.lower()

                        # Determinar si es color o tipo
                        if type_attr and adj_lower in PHYSICAL_DESCRIPTORS.get("hair_type", set()):
                            attr_type = type_attr
                        else:
                            attr_type = base_attr_type

                        attributes.append(
                            self._create_attribute(
                                entity_name=entity_name,
                                attr_type=attr_type,
                                value=adj_lower,
                                confidence=0.90,
                                source_text=sent.text,
                                chapter=chapter,
                            )
                        )

        return attributes

    def _extract_adjective_of(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras "X de ENTIDAD".

        Patrones:
        - "los ojos verdes de María" -> María.eye_color = verdes
        - "el pelo rubio de Juan" -> Juan.hair_color = rubio
        """
        attributes = []

        for token in doc:
            # Buscar "de" seguido de nombre
            if token.text.lower() == "de" and token.dep_ == "case":
                # El head de "de" debería ser el nombre
                entity_token = token.head

                entity_name = None
                if entity_token.text.lower() in entity_names:
                    entity_name = entity_token.text
                else:
                    for name in entity_names:
                        if entity_token.text.lower() in name.lower():
                            entity_name = name
                            break

                if not entity_name:
                    continue

                # Buscar la parte del cuerpo (el abuelo de "de")
                parent = entity_token.head

                if parent.lemma_.lower() in BODY_PARTS_TO_ATTR:
                    base_attr_type = BODY_PARTS_TO_ATTR[parent.lemma_.lower()]

                    # Buscar adjetivo que modifica la parte del cuerpo
                    for child in parent.children:
                        if child.pos_ == "ADJ":
                            attributes.append(
                                self._create_attribute(
                                    entity_name=entity_name,
                                    attr_type=base_attr_type,
                                    value=child.text.lower(),
                                    confidence=0.85,
                                    source_text=token.sent.text,
                                    chapter=chapter,
                                )
                            )

        return attributes

    def _find_sentence_subject(
        self,
        sent: Any,
        entity_names: set[str],
    ) -> str | None:
        """
        Encuentra el sujeto de una oración que sea una entidad conocida.

        Prioriza:
        1. Sujetos sintácticos (nsubj) que sean nombres propios
        2. Si no hay sujeto explícito, busca el nombre más cercano al verbo principal

        Args:
            sent: Oración de spaCy
            entity_names: Nombres de entidades conocidas (en minúsculas)

        Returns:
            Nombre de la entidad que es sujeto, o None
        """
        # Estrategia 1: Buscar sujeto sintáctico explícito (nsubj)
        for token in sent:
            if token.dep_ in {"nsubj", "nsubj:pass"}:
                # Verificar si es una entidad conocida
                if token.text.lower() in entity_names:
                    return token.text

                # Buscar coincidencia parcial (para nombres compuestos)
                for name in entity_names:
                    if token.text.lower() in name or name in token.text.lower():
                        return name

        # Estrategia 2: Si no hay sujeto explícito, buscar la raíz del verbo
        # y luego el nombre propio más cercano a la izquierda
        root_verb = None
        for token in sent:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                root_verb = token
                break

        if root_verb:
            # Buscar el nombre propio más cercano antes del verbo
            for token in reversed(list(sent[: root_verb.i - sent.start])):
                if token.pos_ == "PROPN":
                    if token.text.lower() in entity_names:
                        return token.text
                    for name in entity_names:
                        if token.text.lower() in name:
                            return name

        # Estrategia 3: Fallback - primer nombre propio que sea sujeto de la oración
        # IMPORTANTE: Solo devolver PROPN que sea sujeto (nsubj), NO cualquier PROPN
        # ya que podría ser un objeto (ej: "María entró en la casa de Juan" -> Juan no es sujeto)
        for token in sent:
            if token.pos_ == "PROPN" and token.dep_ in {"nsubj", "nsubj:pass"}:
                if token.text.lower() in entity_names:
                    return token.text
                for name in entity_names:
                    if token.text.lower() in name:
                        return name

        # Estrategia 4: Buscar PROPN que sea entidad conocida y NO sea objeto
        # Esto maneja casos donde el parser confunde el rol sintáctico (ej: títulos de capítulo)
        # IMPORTANTE: Excluir objetos (obj, dobj, iobj, obl) porque no son el sujeto
        # Ej: "Sus ojos miraban a María" -> María es obj, no sujeto
        for token in sent:
            if token.pos_ == "PROPN" and token.dep_ not in {"obj", "dobj", "iobj", "obl"}:
                token_lower = token.text.lower()
                # Verificar si es una entidad conocida
                if token_lower in entity_names:
                    return token.text
                # Buscar coincidencia parcial
                for name in entity_names:
                    if token_lower in name:
                        return name

        return None

    def _extract_possessive(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de pronombres posesivos usando análisis sintáctico.

        MEJORA: En lugar de tracking lineal de última entidad,
        usa el sujeto de la oración actual o anterior.

        Patrones:
        - "María entró. Sus ojos azules brillaban" -> María.eye_color = azules
        - "María entró en la casa de Juan. Sus ojos brillaban" -> María (no Juan)

        El algoritmo:
        1. Para cada oración, busca el sujeto sintáctico
        2. Si hay un posesivo, lo asigna al sujeto de la oración actual
        3. Si no hay sujeto en la oración actual, hereda de la anterior
        """
        attributes = []

        # Mapear cada oración a su sujeto
        sentence_subjects: dict[int, str | None] = {}
        last_subject = None

        for sent in doc.sents:
            subject = self._find_sentence_subject(sent, entity_names)
            if subject:
                last_subject = subject
                sentence_subjects[sent.start] = subject
            else:
                # Heredar sujeto de oración anterior si no hay reset
                # Un "reset" ocurre con verbos de movimiento + sujeto nuevo
                sentence_subjects[sent.start] = last_subject

        # Ahora buscar posesivos en cada oración
        for sent in doc.sents:
            sent_subject = sentence_subjects.get(sent.start)

            for token in sent:
                # Buscar posesivos (su, sus)
                if token.text.lower() not in {"su", "sus"} or token.pos_ != "DET":
                    continue

                # El head debería ser el sustantivo
                noun = token.head

                if noun.lemma_.lower() not in BODY_PARTS_TO_ATTR:
                    continue

                # Usar el sujeto de la oración (no last_entity global)
                if not sent_subject:
                    logger.debug(
                        f"No subject found for possessive '{token.text}' in: {sent.text[:50]}..."
                    )
                    continue

                base_attr_type = BODY_PARTS_TO_ATTR[noun.lemma_.lower()]

                # Buscar adjetivo que modifica el sustantivo
                for child in noun.children:
                    if child.pos_ == "ADJ":
                        attributes.append(
                            self._create_attribute(
                                entity_name=sent_subject,
                                attr_type=base_attr_type,
                                value=child.text.lower(),
                                confidence=0.75,  # Mayor confianza con análisis sintáctico
                                source_text=sent.text,
                                chapter=chapter,
                            )
                        )

        return attributes

    def _extract_enumerations(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de enumeraciones de adjetivos.

        Patrones:
        - "Un hombre alto, delgado y moreno"
        - "María, alta y de ojos claros"
        """
        attributes = []

        for token in doc:
            # Buscar conjunciones "y"
            if token.text.lower() == "y" and token.pos_ == "CCONJ":
                # Buscar adjetivos coordinados
                head = token.head
                if head.pos_ != "ADJ":
                    continue

                # Encontrar todos los adjetivos en la coordinación
                coordinated_adjs = [head]

                for child in head.children:
                    if child.pos_ == "ADJ" or child.dep_ == "conj" and child.pos_ == "ADJ":
                        coordinated_adjs.append(child)

                if len(coordinated_adjs) < 2:
                    continue

                # Buscar la entidad asociada
                entity_name = self._find_entity_for_adjectives(head, entity_names, doc)

                if not entity_name:
                    continue

                # Crear atributo para cada adjetivo
                for adj in coordinated_adjs:
                    attr_type = self._classify_attribute(adj.text)
                    if attr_type:
                        attributes.append(
                            self._create_attribute(
                                entity_name=entity_name,
                                attr_type=attr_type,
                                value=adj.text.lower(),
                                confidence=0.75,
                                source_text=head.sent.text,
                                chapter=chapter,
                            )
                        )

        return attributes

    def _extract_prepositional(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras preposicionales.

        Patrones:
        - "con ojos marrones" -> eye_color = marrones
        - "de cabello largo" -> hair_type = largo
        - "con barba espesa y ojos marrones" -> hair_type = espesa, eye_color = marrones

        El sujeto se hereda del contexto de la oración.
        """
        attributes = []

        # Mapear cada oración a su sujeto
        sentence_subjects: dict[int, str | None] = {}
        last_subject = None

        for sent in doc.sents:
            subject = self._find_sentence_subject(sent, entity_names)
            if subject:
                last_subject = subject
            sentence_subjects[sent.start] = last_subject

        # Buscar preposiciones "con" o "de"
        for sent in doc.sents:
            sent_subject = sentence_subjects.get(sent.start)

            for token in sent:
                # Buscar "con" o "de" seguido de parte del cuerpo
                if token.text.lower() not in {"con", "de"} or token.dep_ != "case":
                    continue

                # El head de la preposición es el sustantivo
                noun = token.head

                if noun.lemma_.lower() not in BODY_PARTS_TO_ATTR:
                    # Podría ser parte de una coordinación
                    # "con barba espesa y ojos marrones" -> "ojos" es conj de "barba"
                    continue

                if not sent_subject:
                    continue

                base_attr_type = BODY_PARTS_TO_ATTR[noun.lemma_.lower()]
                type_attr = BODY_PARTS_WITH_TYPE.get(noun.lemma_.lower())

                # Extraer adjetivos directos
                for adj_token in self._collect_adjectives(noun):
                    adj_lower = adj_token.text.lower()

                    # Determinar tipo correcto
                    if type_attr and adj_lower in PHYSICAL_DESCRIPTORS.get("hair_type", set()):
                        attr_type = type_attr
                    else:
                        attr_type = base_attr_type

                    attributes.append(
                        self._create_attribute(
                            entity_name=sent_subject,
                            attr_type=attr_type,
                            value=adj_lower,
                            confidence=0.75,
                            source_text=sent.text,
                            chapter=chapter,
                        )
                    )

                # Buscar también sustantivos coordinados (y ojos marrones)
                for child in noun.children:
                    if child.dep_ == "conj" and child.pos_ == "NOUN":
                        if child.lemma_.lower() in BODY_PARTS_TO_ATTR:
                            conj_attr_type = BODY_PARTS_TO_ATTR[child.lemma_.lower()]
                            for adj in self._collect_adjectives(child):
                                attributes.append(
                                    self._create_attribute(
                                        entity_name=sent_subject,
                                        attr_type=conj_attr_type,
                                        value=adj.text.lower(),
                                        confidence=0.70,
                                        source_text=sent.text,
                                        chapter=chapter,
                                    )
                                )

        return attributes

    def _extract_noun_fragments(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: int | None,
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de fragmentos nominales sin verbo.

        Patrones:
        - "Cabello negro y largo, ojos azules brillantes." (descripción sin verbo)

        Este patrón aparece cuando el narrador lista características
        sin usar un verbo copulativo explícito.

        El sujeto se hereda del contexto de oraciones anteriores.
        """
        attributes = []

        # Mapear cada oración a su sujeto
        sentence_subjects: dict[int, str | None] = {}
        last_subject = None

        for sent in doc.sents:
            subject = self._find_sentence_subject(sent, entity_names)
            if subject:
                last_subject = subject
            sentence_subjects[sent.start] = last_subject

        # Buscar oraciones que son fragmentos nominales
        for sent in doc.sents:
            sent_subject = sentence_subjects.get(sent.start)

            # Encontrar el ROOT de la oración
            root = None
            for token in sent:
                if token.dep_ == "ROOT":
                    root = token
                    break

            if not root:
                continue

            # Verificar si es un fragmento nominal:
            # - ROOT es NOUN o PROPN (no VERB)
            # - ROOT o sus aposiciones son partes del cuerpo
            if root.pos_ not in {"NOUN", "PROPN"}:
                continue

            # Si no hay sujeto heredado, no podemos asignar los atributos
            if not sent_subject:
                continue

            # Buscar partes del cuerpo en el ROOT y sus aposiciones
            body_parts_to_process = []

            # Verificar el ROOT
            root_lemma = root.lemma_.lower() if root.lemma_ else root.text.lower()
            if root_lemma in BODY_PARTS_TO_ATTR:
                body_parts_to_process.append((root, BODY_PARTS_TO_ATTR[root_lemma]))

            # Verificar aposiciones (appos) del ROOT
            for child in root.children:
                if child.dep_ == "appos" and child.pos_ == "NOUN":
                    child_lemma = child.lemma_.lower() if child.lemma_ else child.text.lower()
                    if child_lemma in BODY_PARTS_TO_ATTR:
                        body_parts_to_process.append((child, BODY_PARTS_TO_ATTR[child_lemma]))

            # Extraer atributos de cada parte del cuerpo
            for body_part_token, base_attr_type in body_parts_to_process:
                type_attr = BODY_PARTS_WITH_TYPE.get(body_part_token.lemma_.lower())

                for adj_token in self._collect_adjectives(body_part_token):
                    adj_lower = adj_token.text.lower()

                    # Determinar tipo correcto
                    if type_attr and adj_lower in PHYSICAL_DESCRIPTORS.get("hair_type", set()):
                        attr_type = type_attr
                    else:
                        attr_type = base_attr_type

                    attributes.append(
                        self._create_attribute(
                            entity_name=sent_subject,
                            attr_type=attr_type,
                            value=adj_lower,
                            confidence=0.65,  # Menor confianza por ser inferencia de contexto
                            source_text=sent.text,
                            chapter=chapter,
                        )
                    )

        return attributes

    def _collect_adjectives(self, noun_token: Any) -> list[Any]:
        """
        Recoge todos los adjetivos que modifican un sustantivo,
        incluyendo adjetivos coordinados (X y Y) y modificadores anidados.

        Ejemplos:
        - "cabello largo y negro" -> [largo, negro]
        - "hombre muy alto, delgado como un junco" -> [alto, delgado]
        """
        adjectives = []

        for child in noun_token.children:
            if child.pos_ == "ADJ":
                adjectives.append(child)
                # Buscar adjetivos coordinados (dep=conj) y modificadores anidados (dep=amod)
                for grandchild in child.children:
                    if grandchild.pos_ == "ADJ":
                        # Incluir tanto coordinados (conj) como modificadores (amod)
                        # Ej: "alto, delgado" -> delgado es amod de alto en algunos parses
                        if grandchild.dep_ in {"conj", "amod"}:
                            adjectives.append(grandchild)

        return adjectives

    def _find_subject(self, verb_token: Any) -> Any | None:
        """Encuentra el sujeto de un verbo."""
        # Buscar en hijos directos
        for child in verb_token.children:
            if child.dep_ == "nsubj":
                return child

        # Si el verbo es auxiliar, buscar en el head
        if verb_token.dep_ == "cop":
            for child in verb_token.head.children:
                if child.dep_ == "nsubj":
                    return child

        return None

    def _resolve_pronoun(
        self,
        doc: Any,
        pronoun_token: Any,
        entity_names: set[str],
    ) -> str | None:
        """
        Resuelve un pronombre a la última entidad mencionada.

        Considera el género gramatical del pronombre para mejor precisión:
        - "él" -> busca entidades masculinas
        - "ella" -> busca entidades femeninas
        """
        pronoun_text = pronoun_token.text.lower()
        pronoun_morph = pronoun_token.morph

        # Determinar género del pronombre si spaCy lo proporciona
        pronoun_gender = None
        if pronoun_morph:
            gender_str = pronoun_morph.get("Gender")
            if gender_str:
                pronoun_gender = gender_str[0] if isinstance(gender_str, list) else gender_str

        # Inferir género de pronombres comunes si no hay morph
        if not pronoun_gender:
            masc_pronouns = {"él", "el", "este", "ese", "aquel", "lo", "le"}
            fem_pronouns = {"ella", "esta", "esa", "aquella", "la"}
            if pronoun_text in masc_pronouns:
                pronoun_gender = "Masc"
            elif pronoun_text in fem_pronouns:
                pronoun_gender = "Fem"

        # Buscar hacia atrás la última entidad que coincida con el género
        for token in reversed(list(doc[: pronoun_token.i])):
            token_lower = token.text.lower()

            # Verificar si el token es una entidad conocida
            matched_entity = None
            if token_lower in entity_names:
                matched_entity = token.text
            else:
                for name in entity_names:
                    name_parts = name.lower().split()
                    if token_lower in name_parts or token_lower == name.lower():
                        matched_entity = name
                        break

            if matched_entity:
                # Si tenemos género del pronombre, verificar compatibilidad
                if pronoun_gender and token.pos_ in {"PROPN", "NOUN"}:
                    token_gender_list = token.morph.get("Gender") if token.morph else None
                    if token_gender_list:
                        token_gender = (
                            token_gender_list[0]
                            if isinstance(token_gender_list, list)
                            else token_gender_list
                        )
                        # Solo aceptar si los géneros coinciden o si no sabemos
                        if token_gender != pronoun_gender:
                            continue

                return matched_entity

        return None

    def _find_entity_for_adjectives(
        self,
        adj_token: Any,
        entity_names: set[str],
        doc: Any,
    ) -> str | None:
        """Encuentra la entidad a la que se refieren los adjetivos."""
        # Buscar en el contexto cercano
        for token in adj_token.sent:
            if token.text.lower() in entity_names:
                return token.text
            for name in entity_names:
                if token.text.lower() in name.lower():
                    return name

        return None

    def _classify_attribute(self, value: str) -> AttributeType | None:
        """
        Clasifica un valor de atributo en su tipo correspondiente.
        """
        value_lower = value.lower()

        for attr_type_str, values in PHYSICAL_DESCRIPTORS.items():
            if value_lower in values:
                try:
                    return AttributeType(attr_type_str)
                except ValueError:
                    continue

        return None

    def _separate_compound_attributes(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """Separa atributos compuestos."""
        result = []
        import re

        hair_colors = PHYSICAL_DESCRIPTORS.get("hair_color", set())
        hair_types = PHYSICAL_DESCRIPTORS.get("hair_type", set())

        for attr in attributes:
            # Buscar patrón "X y Y"
            match = re.search(r"(\w+)\s+y\s+(\w+)", attr.value, re.IGNORECASE)

            if match:
                val1 = match.group(1).lower()
                val2 = match.group(2).lower()

                # Determinar tipos
                type1 = None
                type2 = None

                if val1 in hair_colors:
                    type1 = AttributeType.HAIR_COLOR
                elif val1 in hair_types:
                    type1 = AttributeType.HAIR_TYPE

                if val2 in hair_colors:
                    type2 = AttributeType.HAIR_COLOR
                elif val2 in hair_types:
                    type2 = AttributeType.HAIR_TYPE

                if type1 and type2 and type1 != type2:
                    # Separar
                    result.append(
                        self._create_attribute(
                            entity_name=attr.entity_name,
                            attr_type=type1,
                            value=val1,
                            confidence=attr.confidence * 0.95,
                            source_text=attr.source_text,
                            chapter=attr.chapter,
                        )
                    )
                    result.append(
                        self._create_attribute(
                            entity_name=attr.entity_name,
                            attr_type=type2,
                            value=val2,
                            confidence=attr.confidence * 0.95,
                            source_text=attr.source_text,
                            chapter=attr.chapter,
                        )
                    )
                else:
                    result.append(attr)
            else:
                result.append(attr)

        return result

    def _deduplicate(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """Elimina duplicados manteniendo el de mayor confianza."""
        seen: dict[tuple, ExtractedAttribute] = {}

        for attr in attributes:
            key = (
                attr.entity_name.lower(),
                attr.attribute_type,
                attr.value.lower(),
            )

            if key not in seen or attr.confidence > seen[key].confidence:
                seen[key] = attr

        return list(seen.values())
