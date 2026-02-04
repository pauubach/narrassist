# Revisión UX: Configuración, Correcciones y Filtros

**Fecha**: 2026-01-28
**Estado**: Para deliberación con equipo

**Participantes necesarios**: PO, UX, UI, Arquitecto, Experto Editorial, Lingüista, Usuarios tipo

---

## 0. Problema Principal: Sistema de Correcciones Editoriales

### Situación actual

El sistema de "presets de corrección" tiene problemas fundamentales de diseño:

1. **No detecta el tipo de documento automáticamente**
   - El usuario debe configurar manualmente el preset
   - No aprovecha el análisis NLP que ya detecta el tipo de documento

2. **No respeta la consistencia interna del documento**
   - Si un manuscrito usa guión simple (`-`) consistentemente en TODO el documento
   - ¿Tiene sentido sugerir cambiar TODOS los guiones a raya (`—`)?
   - El sistema debería ofrecer una opción "definido por el documento"

3. **Configuración confusa**
   - No queda claro si es para "nuevos proyectos" o "documento actual"
   - El usuario ve un "resumen" pero no sabe cómo editarlo

### Propuesta de diseño

```
┌─────────────────────────────────────────────────────────────────┐
│  Estilo tipográfico                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Para cada tipo de documento, define qué estilo aplicar:        │
│                                                                  │
│  ┌─────────────┬──────────────────────────────────────────────┐ │
│  │ Narrativa   │ [Detectar del documento ▼]                   │ │
│  │             │  ○ Detectar del documento (respetar estilo)  │ │
│  │             │  ○ Raya (—) para diálogos                    │ │
│  │             │  ○ Guión (-) para diálogos                   │ │
│  │             │  ○ Comillas angulares «»                     │ │
│  │             │  ○ Comillas inglesas ""                      │ │
│  ├─────────────┼──────────────────────────────────────────────┤ │
│  │ Autoayuda   │ [Detectar del documento ▼]                   │ │
│  ├─────────────┼──────────────────────────────────────────────┤ │
│  │ Técnico     │ [Detectar del documento ▼]                   │ │
│  └─────────────┴──────────────────────────────────────────────┘ │
│                                                                  │
│  ℹ️ "Detectar del documento" respetará el estilo que ya usa     │
│     el manuscrito, sugiriendo solo corregir inconsistencias.    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Comportamiento propuesto

| Configuración | Comportamiento |
|---------------|----------------|
| **Detectar del documento** (default) | Analiza qué usa el documento. Si usa `-` consistentemente, NO sugiere cambiar a `—`. Solo alerta si hay MEZCLA de estilos. |
| **Raya (—)** | Siempre sugiere usar raya, aunque el documento use guión consistentemente. |
| **Guión (-)** | Siempre sugiere usar guión, aunque el documento use raya. |

### Preguntas para deliberación

| Rol | Pregunta |
|-----|----------|
| **PO** | ¿Los usuarios quieren que el sistema "imponga" un estilo o que "respete" el estilo del documento? |
| **Experto Editorial** | ¿Cuál es la práctica estándar en corrección profesional? ¿Se respeta el estilo del autor o se normaliza? |
| **Lingüista** | ¿Qué reglas de tipografía aplican según el tipo de documento (narrativa vs técnico vs autoayuda)? |
| **UX** | ¿Cómo comunicamos esta flexibilidad sin abrumar al usuario? |
| **Arquitecto** | ¿Cómo implementamos la detección automática del estilo del documento? |

---

## 1. Filtros de Entidades - ¿Útil o sobrecarga?

### ¿Qué hace actualmente?

La sección "Filtros de Entidades" permite:
1. **Patrones del sistema** (57 patrones): Activar/desactivar filtros para palabras comunes
   - Artículos determinados: El, La, Las, Los
   - Artículos indeterminados: Un, Una
   - Marcadores temporales, expresiones comunes, etc.

2. **Rechazos globales**: Lista de entidades que el usuario ha rechazado manualmente

### Preguntas para el equipo

| Pregunta | Para quién |
|----------|------------|
| ¿Qué problema del usuario resuelve mostrar 57 checkboxes de filtrado? | PO |
| ¿Alguien ha pedido poder desactivar el filtro del artículo "El"? | PO |
| ¿Un corrector/editor entiende qué es un "patrón de filtrado de entidades"? | UX, Usuarios |
| ¿Con qué frecuencia un usuario cambiaría estos filtros? | Usuarios |

### Opciones de diseño

| Opción | Descripción | Beneficio |
|--------|-------------|-----------|
| **A: Eliminar de UI** | Los filtros funcionan automáticamente | Menos sobrecarga cognitiva |
| **B: Configuración avanzada** | Ocultar bajo acordeón colapsable | Disponible sin molestar |
| **C: Simplificar** | 3-4 toggles por categoría en vez de 57 checkboxes | Mismo control, menos ruido |

**Recomendación**: Opción A. El sistema debería "simplemente funcionar".

---

## 2. Problema de Espacio Desaprovechado

### Estado: ✅ CSS corregido

Se añadió CSS para `.setting-item.column` que hace que el contenido use todo el ancho:

```css
.setting-item.column {
  flex-direction: column;
  gap: 1rem;
}
```

### Pendiente: Revisión general

La vista de Configuración se está haciendo muy larga. ¿Debería consolidarse o reorganizarse?

**Pregunta para UX/UI**: ¿Merece la pena tener la configuración separada en tantas secciones?

---

## 3. Tutorial Desactualizado

### Problema detectado

El tutorial muestra **7 pestañas**:
- Texto, Entidades, Relaciones, Alertas, Timeline, Estilo, Resumen

Pero el workspace tiene **8 pestañas** (falta **Glosario**).

### Archivo a corregir

`frontend/src/components/TutorialDialog.vue` líneas 117-127

```vue
<!-- Actual (incorrecto) -->
<span class="tab">Texto</span>
<span class="tab">Entidades</span>
<span class="tab">Relaciones</span>
<span class="tab">Alertas</span>
<span class="tab">Timeline</span>
<span class="tab">Estilo</span>
<span class="tab">Resumen</span>
<!-- Falta: Glosario -->
```

**Nota**: Las tabs son dinámicas según tipo de documento, así que el texto "7 pestañas" también debe actualizarse.

---

## 4. Otros problemas detectados

### 4.1 Resumen de configuración sin acción

**Problema**: Se muestra "Resumen de configuración" pero no hay forma de editarlo.

**Solución propuesta**: Añadir botón "Personalizar" que abra un diálogo de edición.

### 4.2 Texto ambiguo "preset seleccionado"

**Problema**: Usuario pregunta "¿A qué documento se refiere?"

**Solución propuesta**: Clarificar que es para **nuevos proyectos**:
```
"Configuración base para nuevos proyectos"
"Esta configuración se aplicará cuando crees un nuevo proyecto.
 Cada proyecto puede tener su propia configuración."
```

---

## 5. Plan de acción

| Prioridad | Tarea | Responsable | Estado |
|-----------|-------|-------------|--------|
| **Alta** | Deliberar sobre sistema de correcciones editoriales | Equipo completo | Pendiente |
| **Alta** | Corregir tutorial (8 tabs, no 7) | FE | Pendiente |
| Media | Decidir qué hacer con filtros de entidades | PO + UX | Pendiente |
| Media | Añadir botón "Personalizar" al resumen | FE | Pendiente |
| ~~Media~~ | ~~Añadir CSS para `.setting-item.column`~~ | ~~FE~~ | ✅ Hecho |
| Baja | Revisar longitud de vista de configuración | UX + FE | Pendiente |

---

## 6. Análisis Técnico: Detección Automática

### Estado actual del sistema

#### Ya implementado: Detección de tipo de documento

El sistema YA detecta automáticamente el tipo de documento en:
`src/narrative_assistant/parsers/document_classifier.py`

**Tipos actualmente en el clasificador** (`document_classifier.py`):
| Tipo | Descripción | Indicadores |
|------|-------------|-------------|
| `fiction` | Novela, cuento, relato | Diálogos, descripciones, acciones |
| `self_help` | Autoayuda | Consejos directos, conceptos abstractos |
| `essay` | Ensayo | Argumentación, referencias |
| `technical` | Manual técnico | Términos técnicos, código |
| `memoir` | Memorias | Primera persona, autobiográfico |
| `cookbook` | Recetas | Ingredientes, instrucciones cocina |
| `academic` | Paper académico | Citas (Autor, año) |
| `unknown` | No clasificado | Confianza < 25% |

#### ⚠️ PROBLEMA MAYOR: Desincronización entre FeatureProfile y Clasificador

El sistema tiene **dos definiciones diferentes** de tipos de documento:

| Sistema | Ubicación | Tipos |
|---------|-----------|-------|
| **FeatureProfile** | `feature_profile/models.py` | 12 tipos |
| **DocumentClassifier** | `parsers/document_classifier.py` | 7 tipos |

**Tipos en FeatureProfile que NO detecta el Clasificador (7 faltantes):**

| Tipo | Código | Descripción | Indicadores sugeridos |
|------|--------|-------------|----------------------|
| **BIOGRAPHY** | BIO | Biografías de terceros | "nació en", "su vida", "según testigos" |
| **CELEBRITY** | CEL | Libros famosos/influencers | "mis fans", "mi comunidad", "redes sociales" |
| **DIVULGATION** | DIV | Divulgación científica/histórica | "los científicos descubrieron", "la historia nos enseña" |
| **PRACTICAL** | PRA | Cocina, jardinería, DIY, guías | Ingredientes, instrucciones paso a paso |
| **GRAPHIC** | GRA | Novela gráfica, cómic, manga | Onomatopeyas, viñetas, globos de texto |
| **CHILDREN** | INF | Infantil/juvenil | Vocabulario simple, repeticiones, ilustraciones |
| **DRAMA** | DRA | Teatro, guiones cine/TV | Acotaciones, nombres en mayúscula, FADE IN |

**Tipos en Clasificador que NO están en FeatureProfile (2 huérfanos):**

| Tipo actual | Debería ser |
|-------------|-------------|
| `COOKBOOK` | Subtipo de `PRACTICAL` (PRA_COC) |
| `ACADEMIC` | Subtipo de `ESSAY` (ENS_ACA) |

### Grupos de edad para CHILDREN (literatura infantil/juvenil)

| Grupo | Código | Edad | Características |
|-------|--------|------|-----------------|
| Board Book | BOARD_BOOK | 0-3 años | Oraciones muy cortas, vocabulario básico |
| Picture Book | PICTURE_BOOK | 3-5 años | Educación Infantil, frases simples |
| Early Reader | EARLY_READER | 5-8 años | Primeros lectores, repetición deseable |
| Middle Grade | MIDDLE_GRADE | 6-10 años | Primaria (1º-4º) |
| Tween | TWEEN | 8-12 años | Primaria (4º-6º) |
| Young Adult | YOUNG_ADULT | 12+ años | Secundaria+ |

### Subtipos ya definidos en FeatureProfile

El sistema ya define subtipos para cada categoría:
- **FICTION**: FIC_LIT (literaria), FIC_GEN (género), FIC_HIS (histórica), FIC_COR (cuento), FIC_MIC (micro)
- **MEMOIR**: MEM_AUT (autobiografía), MEM_PAR (parciales), MEM_DIA (diario)
- **SELF_HELP**: AUT_DES (desarrollo), AUT_PRO (productividad), AUT_BIE (bienestar), AUT_REL (relaciones)
- etc.

**Acción requerida**:
1. Sincronizar `DocumentType` entre ambos archivos
2. Añadir indicadores para los 7 tipos faltantes
3. Mapear COOKBOOK → PRACTICAL, ACADEMIC → ESSAY
4. Implementar detección de subtipos
5. Integrar grupos de edad de CHILDREN con métricas de legibilidad

**Cómo funciona actualmente**:
1. Analiza primeros 10,000 caracteres
2. Busca patrones regex por categoría
3. Pondera coincidencias con pesos
4. Retorna tipo + confianza + configuración recomendada

#### ⚠️ Problema detectado: Preámbulos largos

**Caso real**: *La Regenta* tiene ~25,000 caracteres de preámbulo (índice, prólogo, notas editoriales) antes del contenido narrativo. El clasificador analiza solo caracteres 0-10,000, obteniendo **50% confianza**. Al analizar desde el capítulo 1, obtiene **66% confianza**.

**Pregunta para expertos NLP/Arquitecto**:

> ¿Deberíamos analizar 10,000 caracteres del **medio** del libro en lugar del inicio para evitar:
> - Índices y tablas de contenido
> - Títulos y portadas
> - Preámbulos y prólogos editoriales
> - Dedicatorias y agradecimientos
> - Notas del traductor

| Opción | Descripción | Pros | Contras |
|--------|-------------|------|---------|
| **A: Inicio** (actual) | Primeros 10,000 chars | Simple | Afectado por preámbulos |
| **B: Medio** | Chars del 40-50% del texto | Contenido real | Podría caer en "relleno" |
| **C: Muestreo múltiple** | 3 muestras (10%, 50%, 90%) | Representativo | Más lento, más complejo |
| **D: Detectar inicio real** | Buscar primer capítulo/sección | Inteligente | Requiere patrones adicionales |

**Decisión pendiente**: Validar con pruebas en corpus variado de documentos.

#### No implementado: Detección de estilo tipográfico

El detector de tipografía (`corrections/detectors/typography.py`) **compara contra un estilo configurado**, pero NO detecta qué estilo usa el documento.

**Lo que falta**:
```python
# Propuesta: TypographyStyleAnalyzer
class TypographyStyleAnalyzer:
    """Detecta el estilo tipográfico dominante del documento."""

    def analyze(self, text: str) -> TypographyStyleProfile:
        """
        Retorna:
        - dialogue_dash: 'em' | 'en' | 'hyphen' | 'mixed'
        - quote_style: 'angular' | 'curly' | 'straight' | 'mixed'
        - counts: {em: 45, en: 2, hyphen: 0} -> dominante es 'em'
        - consistency: 0.95 (95% usa el mismo estilo)
        """
```

### Propuesta de implementación

#### Fase 1: Detectar estilo tipográfico del documento

```python
# En corrections/detectors/typography_analyzer.py (NUEVO)

@dataclass
class TypographyStyleProfile:
    dialogue_dash: Literal['em', 'en', 'hyphen', 'mixed']
    dialogue_dash_counts: dict[str, int]
    dialogue_dash_consistency: float  # 0.0 - 1.0

    quote_style: Literal['angular', 'curly', 'straight', 'mixed']
    quote_counts: dict[str, int]
    quote_consistency: float

    @property
    def is_consistent(self) -> bool:
        """True si el documento usa un estilo consistente."""
        return (
            self.dialogue_dash_consistency > 0.9 and
            self.quote_consistency > 0.9
        )
```

#### Fase 2: Opción "Detectar del documento"

```python
# En corrections/config.py

class TypographyConfig:
    # Actual
    dialogue_dash: str = "em"  # 'em', 'en', 'hyphen'

    # Propuesto
    dialogue_dash: str = "auto"  # 'em', 'en', 'hyphen', 'auto'
    # 'auto' = detectar del documento y solo alertar inconsistencias
```

#### Fase 3: Integrar en el flujo

```
Documento → DocumentClassifier → Tipo (fiction, self_help...)
         → TypographyStyleAnalyzer → Estilo (em_dash, angular_quotes...)
         → TypographyDetector (con estilo detectado o configurado)
         → Solo alertas de INCONSISTENCIAS si config='auto'
```

### Preguntas para el equipo técnico

| Rol | Pregunta |
|-----|----------|
| **Backend/NLP** | ¿El análisis de estilo tipográfico debe hacerse en el pipeline de análisis o como paso separado? |
| **Arquitecto** | ¿Dónde almacenamos el perfil tipográfico detectado? ¿En Project? ¿En FeatureProfile? |
| **AI/NLP** | ¿Podemos usar embeddings para detectar "estilo editorial" más allá de tipografía? |
| **Lingüista** | ¿Qué reglas de tipografía son "obligatorias" vs "preferencia del autor"? |

### Debate: Doble guión (--) como marcador de diálogo

#### Contexto histórico

El doble guión (`--`) es una convención tipográfica de la era de las **máquinas de escribir**, cuando no existía el carácter de raya (`—`). Obras clásicas como *La Regenta* de Clarín fueron digitalizadas manteniendo este formato.

| Carácter | Código | Nombre | Uso tradicional |
|----------|--------|--------|-----------------|
| `—` | U+2014 | Em dash (raya) | Diálogos en español moderno |
| `–` | U+2013 | En dash | Rangos numéricos |
| `-` | U+002D | Hyphen | Palabras compuestas |
| `--` | (2x U+002D) | Double hyphen | **Simulación de raya en máquinas de escribir** |

#### Pregunta para expertos editoriales y lingüistas

> **¿El sistema debe incluir `--` como opción válida de diálogo o siempre sugerir corregirlo?**

| Posición | Argumentos |
|----------|------------|
| **Incluir como válido** | - Respeta el estilo original de obras digitalizadas<br>- Permite consistencia interna del documento<br>- El autor eligió ese estilo conscientemente |
| **Siempre corregir a raya** | - RAE y Fundéu recomiendan raya (`—`) para diálogos<br>- `--` es un "hack" tipográfico obsoleto<br>- Estándar editorial moderno requiere raya |
| **Híbrido** | - Por defecto: sugerir raya<br>- Opción de "modo clásico" que acepta `--`<br>- Detectar si es texto digitalizado antiguo |

#### Impacto técnico

El clasificador de documentos ya detecta `--` como indicador de diálogo (añadido 2026-01-28):

```python
# document_classifier.py línea 61
"dialog_markers": [
    r'--\s*[A-ZÁÉÍÓÚÑ¡¿]',  # Doble guión (clásico español)
    r'[—–]\s*[A-ZÁÉÍÓÚÑ¡¿]',  # Raya/guión medio
    ...
]
```

**Decisión pendiente**: ¿El `TypographyStyleAnalyzer` propuesto debe considerar `--` como un estilo válido o como error a corregir?

### Ejemplos de comportamiento esperado

#### Caso 1: Documento consistente con guión corto
```
Entrada: Documento con 100 diálogos usando "-"
Config: dialogue_dash = "auto"
Resultado: 0 alertas (el documento es consistente)
```

#### Caso 2: Documento con mezcla de estilos
```
Entrada: 80 diálogos con "—", 20 con "-"
Config: dialogue_dash = "auto"
Resultado: 20 alertas sugiriendo cambiar "-" a "—" (el dominante)
```

#### Caso 3: Config forzada a raya
```
Entrada: 100 diálogos usando "-"
Config: dialogue_dash = "em"
Resultado: 100 alertas sugiriendo cambiar a "—"
```

---

## 7. Próximos pasos

### Decisiones ya tomadas

| Decisión | Resultado |
|----------|-----------|
| Filtros de entidades | **Eliminar de UI** - funcionará automáticamente |
| CSS espacio desaprovechado | ✅ Corregido |
| Tutorial tabs | ✅ Actualizado a 8 tabs |

### Sesión de deliberación necesaria

**Tema principal**: Sistema de correcciones editoriales y detección de estilo

**Participantes**:
- PO (decisiones de producto)
- UX/UI (experiencia de usuario)
- Arquitecto (diseño técnico)
- Backend/NLP (implementación)
- Experto Editorial (reglas de corrección)
- Lingüista (normas tipográficas)

**Agenda propuesta**:

1. **Revisión del problema** (10 min)
   - Mostrar caso: documento con 100 guiones cortos
   - ¿Debe sugerir cambiar todos a raya?

2. **Opciones de diseño** (15 min)
   - A: Imponer estilo configurado (actual)
   - B: Detectar y respetar estilo del documento
   - C: Híbrido (detectar + opción de forzar)

3. **Perspectiva editorial** (10 min)
   - ¿Qué hacen los correctores profesionales?
   - ¿Cuándo se normaliza vs cuándo se respeta?

4. **Viabilidad técnica** (10 min)
   - DocumentClassifier ya existe
   - Falta TypographyStyleAnalyzer
   - Esfuerzo estimado de implementación

5. **Decisión y plan** (15 min)
   - Votar enfoque
   - Definir MVP
   - Asignar responsables

---

## 8. Testing Adversarial (GAN-style) para funcionalidades NLP

### Concepto

Los tests GAN-style generan ejemplos adversariales diseñados para engañar al sistema, forzándolo a mejorar continuamente. Cada iteración:
1. **Generator**: Crea ejemplos difíciles que el sistema clasifica incorrectamente
2. **Discriminator**: El sistema intenta clasificar correctamente
3. **Feedback loop**: Los fallos informan mejoras en el modelo

### Funcionalidades candidatas para testing adversarial

| Funcionalidad | Prioridad | Estado actual | Ejemplos adversariales |
|---------------|-----------|---------------|------------------------|
| **Detección tipo documento** | 🔴 Alta | Sin tests | Documentos híbridos (memoir + self_help), textos cortos ambiguos |
| **Detección diálogos** | 🔴 Alta | Básico | Diálogos sin marcadores, diálogo indirecto, monólogos interiores |
| **Correferencia** | 🟡 Media | Con tests | Pronombres ambiguos, cambios de foco narrativo |
| **NER (entidades)** | 🟡 Media | Con tests | Nombres que son palabras comunes ("Victoria", "Esperanza") |
| **Atribución speaker** | 🟡 Media | Con tests | Diálogos múltiples, turnos implícitos |
| **Localización personajes** | 🟡 Media | Con tests | Lugares metafóricos, viajes implícitos |
| **Análisis temporal** | 🟢 Baja | Con tests | Flashbacks, múltiples líneas temporales |

### Tests adversariales para detección de tipo de documento

**Categorías propuestas**:

1. **Híbridos genuinos**
   - Memoir que lee como novela
   - Self-help con narrativa ficcional
   - Ensayo con personajes históricos detallados

2. **Textos cortos/ambiguos**
   - Prólogos sin contexto
   - Fragmentos de 500 palabras
   - Textos sin diálogos (narrativa descriptiva)

3. **Falsos positivos**
   - Documentos técnicos con ejemplos narrativos
   - Recetas con historias personales
   - Academic papers sobre literatura

4. **Edge cases culturales**
   - Literatura clásica (La Regenta, Quijote) con `--`
   - Textos latinoamericanos vs españoles
   - Traducciones (influencia de otro idioma)

5. **Infantil por edad** (nuevo tipo)
   - Board book (0-3): muy pocas palabras
   - Picture book (3-5): frases simples
   - Middle grade vs Young Adult: límite difuso

### Archivos de tests adversariales existentes

```
tests/adversarial/
├── test_coreference_adversarial.py      # 70+ casos
├── test_ner_adversarial.py              # 60+ casos
├── test_vital_status_adversarial.py     # 50+ casos
├── test_emotional_coherence_adversarial.py
├── test_character_location_adversarial.py   # 70+ casos
├── test_speaker_attribution_adversarial.py  # 60+ casos
└── test_document_classification_adversarial.py  # ❌ PENDIENTE
```

### Próximos pasos para testing

| Tarea | Prioridad | Responsable |
|-------|-----------|-------------|
| Crear `test_document_classification_adversarial.py` | Alta | Backend/NLP |
| Añadir casos para `CHILDREN` por grupo de edad | Alta | Backend/NLP |
| Integrar en CI pipeline | Media | DevOps |
| Documentar proceso de mejora con adversariales | Baja | Documentación |

### Documento de referencia

Este documento ([UX_REVIEW_SETTINGS.md](docs/ux/UX_REVIEW_SETTINGS.md)) contiene:
- Análisis del problema
- Propuesta de diseño UX
- Propuesta técnica de implementación
- Ejemplos de comportamiento esperado
- Plan de testing adversarial
