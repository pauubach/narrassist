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

**Tipos soportados**:
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

**Cómo funciona**:
1. Analiza primeros 10,000 caracteres
2. Busca patrones regex por categoría
3. Pondera coincidencias con pesos
4. Retorna tipo + confianza + configuración recomendada

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

### Documento de referencia

Este documento ([UX_REVIEW_SETTINGS.md](docs/ux/UX_REVIEW_SETTINGS.md)) contiene:
- Análisis del problema
- Propuesta de diseño UX
- Propuesta técnica de implementación
- Ejemplos de comportamiento esperado
