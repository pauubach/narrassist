# Sesión de Deliberación: Clasificación de Documentos y Estilo Tipográfico

**Fecha propuesta**: [A definir]
**Duración estimada**: 90 minutos
**Formato**: Presencial / Videoconferencia

---

## Participantes requeridos

| Rol | Responsabilidad en esta sesión |
|-----|-------------------------------|
| **PO (Product Owner)** | Decisiones de producto, priorización |
| **UX/UI** | Experiencia de usuario, presentación de opciones |
| **Arquitecto** | Viabilidad técnica, diseño de sistemas |
| **Backend/NLP** | Implementación de clasificadores y detectores |
| **Experto Editorial** | Normas de corrección profesional |
| **Lingüista** | Normas RAE, tipografía española |
| **Usuario tipo** (opcional) | Perspectiva del corrector/editor real |

---

## Documento de referencia

Leer antes de la sesión: [UX_REVIEW_SETTINGS.md](UX_REVIEW_SETTINGS.md)

---

## Agenda

### Bloque 1: Clasificación de Tipo de Documento (30 min)

#### 1.1 Estado actual - PROBLEMA CRÍTICO (10 min)

**Hay dos sistemas desincronizados:**

| Sistema | Archivo | Tipos |
|---------|---------|-------|
| FeatureProfile | `feature_profile/models.py` | 12 tipos |
| Clasificador | `parsers/document_classifier.py` | 7 tipos |

**7 tipos que FeatureProfile espera pero el Clasificador NO detecta:**
- BIOGRAPHY (biografías)
- CELEBRITY (famosos/influencers)
- DIVULGATION (divulgación)
- PRACTICAL (cocina, DIY, guías)
- GRAPHIC (novela gráfica, cómic)
- CHILDREN (infantil/juvenil)
- DRAMA (teatro, guiones)

**2 tipos en Clasificador sin equivalente en FeatureProfile:**
- COOKBOOK → debería ser subtipo de PRACTICAL
- ACADEMIC → debería ser subtipo de ESSAY

#### 1.2 Diseño de indicadores para TODOS los tipos (20 min)

**Objetivo**: Definir los mejores patrones regex para cada tipo de documento.

**Tipos existentes a MEJORAR:**

| Tipo | Indicadores actuales | Propuestas de mejora |
|------|---------------------|----------------------|
| FICTION | dialog_markers, narrative_descriptions, character_actions, narrative_structures | Añadir: escenas, cambios de POV, descripciones sensoriales |
| MEMOIR | first_person_past, autobiographical | Añadir: "recuerdo que", "en aquellos años", fechas personales |
| ESSAY | argumentation, references, abstract_reflection | Añadir: "en conclusión", "por otra parte", citas inline |
| SELF_HELP | direct_advice, abstract_concepts, tips_structure, rhetorical_questions | Añadir: "ejercicio:", "reflexiona sobre", listas de beneficios |
| TECHNICAL | technical_terms, instructions, code_markers | Añadir: diagramas referenciados, comandos, APIs |
| COOKBOOK | ingredients, cooking_instructions | → Migrar a PRACTICAL con subtipo |

**Tipos NUEVOS a implementar:**

| Tipo | Indicadores propuestos | Peso sugerido |
|------|------------------------|---------------|
| **BIOGRAPHY** | "nació en [año]", "su vida", "según [testigo]", "falleció", tercera persona sobre figura pública | 2.0 |
| **CELEBRITY** | "mis seguidores", "mi comunidad", "redes sociales", "mi marca", lifestyle | 2.0 |
| **DIVULGATION** | "los científicos", "estudios demuestran", "la historia nos enseña", datos curiosos | 1.8 |
| **PRACTICAL** | ingredientes/materiales, "paso 1:", "necesitarás", instrucciones procedimentales | 2.5 |
| **GRAPHIC** | onomatopeyas (¡BOOM!, ¡CRASH!), "[viñeta]", "globo de texto", acotaciones visuales | 3.0 |
| **CHILDREN** | vocabulario controlado, repeticiones, exclamaciones simples, preguntas al lector | 2.0 |
| **DRAMA** | PERSONAJE:, (acotación), ESCENA, ACTO, INT./EXT., FADE IN/OUT | 3.0 |

**Preguntas para expertos:**
- ¿Qué patrones son más discriminativos para cada tipo?
- ¿Cómo evitar confusión entre tipos similares (MEMOIR vs BIOGRAPHY, SELF_HELP vs DIVULGATION)?
- ¿Los pesos propuestos son adecuados?

#### 1.3 Pregunta para NLP/Arquitecto (10 min)

> **¿De qué parte del documento tomamos la muestra para clasificar?**

| Opción | Descripción |
|--------|-------------|
| A: Inicio (actual) | Primeros 10,000 chars |
| B: Medio | Chars del 40-50% del texto |
| C: Muestreo múltiple | 3 muestras (10%, 50%, 90%) |
| D: Detectar inicio real | Buscar "Capítulo 1" o similar |

**Contexto**: La Regenta tiene 25,000 chars de preámbulo. Clasificar desde el inicio da 50% confianza, desde el capítulo 1 da 66%.

**Decisión a tomar**: [  ] A  [  ] B  [  ] C  [  ] D  [  ] Otro: ________

#### 1.3 Tipo CHILDREN con grupos de edad (15 min)

El sistema de FeatureProfile define 6 grupos de edad para literatura infantil:

| Grupo | Edad | Características esperadas |
|-------|------|---------------------------|
| Board Book | 0-3 años | <10 palabras por página |
| Picture Book | 3-5 años | Frases simples, repetición |
| Early Reader | 5-8 años | Vocabulario controlado |
| Middle Grade | 6-10 años | Narrativa con complejidad media |
| Tween | 8-12 años | Temas pre-adolescentes |
| Young Adult | 12+ años | Temas maduros, prosa compleja |

**Preguntas**:
- ¿Qué indicadores textuales distinguen cada grupo?
- ¿Cómo integramos con métricas de legibilidad (Fernández-Huerta, SOL)?
- ¿Prioridad de implementación vs otros tipos?

**Decisión a tomar**: Prioridad [  ] Alta  [  ] Media  [  ] Baja

---

### Bloque 2: Estilo Tipográfico de Diálogos (40 min)

#### 2.1 El problema (10 min)

Demostración del caso:
1. Usuario abre documento con 100 diálogos usando guión simple (`-`)
2. Sistema sugiere cambiar TODOS a raya (`—`)
3. ¿Es esto útil o molesto?

#### 2.2 Opciones de diseño (10 min)

| Opción | Comportamiento |
|--------|----------------|
| **A: Imponer estilo** (actual) | Siempre sugiere el estilo configurado |
| **B: Detectar y respetar** | Detecta el estilo del documento, solo alerta inconsistencias |
| **C: Híbrido** | Default = detectar, con opción de forzar estilo |

**Pregunta para PO**: ¿Los usuarios quieren que el sistema "imponga" o "respete"?

#### 2.3 Debate: Doble guión (--) como opción válida (15 min)

El doble guión (`--`) es convención de máquinas de escribir, usado en obras clásicas digitalizadas.

**Pregunta para Experto Editorial y Lingüista**:

> ¿El sistema debe incluir `--` como opción válida de diálogo o siempre sugerir corregirlo a raya (`—`)?

| Posición | Argumentos |
|----------|------------|
| **Aceptar `--`** | Respeta estilo original, consistencia interna |
| **Siempre corregir** | RAE recomienda raya, `--` es obsoleto |
| **Modo clásico opcional** | Default = corregir, opción de aceptar |

**Decisión a tomar**: [  ] Aceptar  [  ] Corregir siempre  [  ] Modo opcional

#### 2.4 Viabilidad técnica (5 min)

- `DocumentClassifier` ya existe y funciona
- Falta implementar `TypographyStyleAnalyzer`
- Estimación de esfuerzo: [A definir por Backend/NLP]

---

### Bloque 3: Testing Adversarial / GAN-style (15 min)

#### 3.1 Concepto (5 min)

Los tests adversariales generan casos difíciles para encontrar debilidades del sistema.

#### 3.2 Plan de tests para clasificación (10 min)

**Categorías propuestas**:
1. Documentos híbridos (memoir + self_help)
2. Textos cortos/ambiguos (<500 palabras)
3. Falsos positivos (técnico con ejemplos narrativos)
4. Edge cases culturales (clásicos con `--`)
5. CHILDREN por grupo de edad (límites difusos)

**Decisión a tomar**: ¿Aprobar creación de `test_document_classification_adversarial.py`?
[  ] Sí  [  ] No  [  ] Postergar

---

### Bloque 4: Decisiones y Asignaciones (5 min)

#### Resumen de decisiones

| Tema | Decisión | Responsable | Deadline |
|------|----------|-------------|----------|
| Muestreo de texto | | | |
| Tipo CHILDREN | | | |
| Estilo tipográfico | | | |
| Doble guión `--` | | | |
| Tests adversariales | | | |

#### Siguientes pasos

1. [ ] Implementar decisión de muestreo
2. [ ] Añadir indicadores CHILDREN al clasificador
3. [ ] Crear TypographyStyleAnalyzer
4. [ ] Crear test_document_classification_adversarial.py
5. [ ] Actualizar UI con nuevas opciones

---

## Notas de la sesión (2026-01-28)

### Decisiones tomadas

| Tema | Decisión | Detalles |
|------|----------|----------|
| **Muestreo de texto** | **C: Múltiple** | 3 muestras (10%, 50%, 90%) para mayor representatividad |
| **Indicadores** | **Ampliar con corpus** | Buscar libros de libre acceso para cada tipo |
| **Doble guión (--)** | **Añadir como opción** | Incluir en lista de estilos válidos junto a raya |
| **Tests adversariales** | **Sí, crear** | Para document classification y otras funcionalidades |

### Acciones asignadas

| Acción | Responsable | Estado |
|--------|-------------|--------|
| Implementar muestreo múltiple (10%, 50%, 90%) | Backend/NLP | Pendiente |
| Buscar corpus de libros libres por tipo | Backend/NLP | En progreso |
| Consultar expertos NLP/Editorial/Lingüística | Sistema | En progreso |
| Crear test_document_classification_adversarial.py | Backend/NLP | Pendiente |
| Añadir `--` como opción válida en TypographyConfig | Backend | Pendiente |
| Identificar otros algoritmos para tests adversariales | Arquitecto | Pendiente |

---

**Acta preparada por**: Sistema automatizado
**Última actualización**: 2026-01-28
