# Diseño UX: Chat con LLM sobre el Documento

## Resumen Ejecutivo

Este documento analiza la viabilidad, usabilidad y utilidad de añadir un área de chat donde el usuario pueda hacer preguntas al LLM usando el documento como contexto.

---

## 1. Usuario Tipo y Casos de Uso

### 1.1 Perfil del Usuario

| Aspecto | Descripción |
|---------|-------------|
| **Rol** | Corrector literario profesional, editor, escritor |
| **Experiencia técnica** | Media-baja (no es desarrollador) |
| **Contexto de uso** | Revisión de manuscritos largos (50K-200K palabras) |
| **Objetivo principal** | Detectar inconsistencias, analizar personajes, verificar coherencia |

### 1.2 Casos de Uso Principales

1. **Preguntas sobre personajes**
   - "¿Cuántas veces aparece María en el capítulo 3?"
   - "¿Qué relación tiene Pedro con Ana?"
   - "¿En qué capítulos se menciona la casa de la abuela?"

2. **Verificación de consistencia**
   - "¿El color de ojos de Juan es consistente en toda la novela?"
   - "¿Hay contradicciones en la descripción del pueblo?"

3. **Análisis narrativo**
   - "¿Cuál es el arco emocional de la protagonista?"
   - "Resume los eventos del capítulo 5"

4. **Consultas específicas del documento**
   - "¿Qué dice el párrafo donde se describe la boda?"
   - "Busca todas las menciones de 'venganza'"

---

## 2. Análisis de Viabilidad Técnica

### 2.1 Recursos Necesarios

| Componente | Requisito | Estado |
|------------|-----------|--------|
| **LLM Local** | Ollama con llama3.2/mistral | Ya disponible |
| **Contexto** | RAG o ventana de contexto | Requiere implementación |
| **Embeddings** | sentence-transformers | Ya disponible |
| **Vector Store** | FAISS/Chroma para búsqueda semántica | Requiere implementación |

### 2.2 Limitaciones Técnicas

1. **Ventana de contexto limitada**: Los modelos tienen límites (4K-8K tokens para modelos pequeños)
2. **Latencia**: Las respuestas pueden tardar 5-30 segundos según el modelo y hardware
3. **Precisión**: Los modelos locales son menos precisos que GPT-4/Claude
4. **Memoria**: Requiere RAM adicional para embeddings + modelo LLM

### 2.3 Viabilidad: **ALTA**

La infraestructura base ya existe. Se necesita:
- Implementar RAG (Retrieval Augmented Generation)
- Crear índice de embeddings del documento
- Diseñar UI/UX del chat

---

## 3. Propuestas de Diseño

### Opción A: Panel Lateral Fijo

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                                        │
├────────────────────────────────────┬────────────────────────────┤
│                                    │                            │
│                                    │    💬 Asistente            │
│     Visor de Documento             │  ─────────────────────     │
│     (contenido del manuscrito)     │  [Historial de chat]       │
│                                    │                            │
│                                    │  Usuario: ¿Quién es Ana?   │
│                                    │                            │
│                                    │  IA: Ana Ozores es la      │
│                                    │  protagonista, conocida    │
│                                    │  como "La Regenta"...      │
│                                    │                            │
│                                    │  ─────────────────────     │
│                                    │  [________________] [➤]    │
├────────────────────────────────────┴────────────────────────────┤
│  Status Bar                                                      │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Siempre visible y accesible
- No interrumpe el flujo de lectura
- Contexto visual del documento mientras se chatea
- Familiar (similar a Copilot, ChatGPT sidebar)

**Contras:**
- Reduce espacio horizontal para el documento
- En pantallas pequeñas puede ser incómodo
- Puede distraer si no se necesita

**Esfuerzo de implementación:** Medio

---

### Opción B: Panel Inferior Colapsable

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                   Visor de Documento                             │
│                   (contenido del manuscrito)                     │
│                                                                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ▼ Asistente IA                                         [─] [×] │
├─────────────────────────────────────────────────────────────────┤
│  [Historial compacto]                                           │
│  [_________________________________________] [Enviar]           │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- No reduce ancho del documento
- Se puede colapsar cuando no se usa
- Similar a consolas de desarrollo (familiar para algunos)

**Contras:**
- Reduce altura del documento cuando está abierto
- Menos espacio para historial de chat
- Menos visible, puede olvidarse que existe

**Esfuerzo de implementación:** Medio

---

### Opción C: Modal/Diálogo Flotante

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                     [💬]              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│            ┌──────────────────────────────┐                     │
│            │  💬 Asistente IA         [×] │                     │
│  Documento │  ───────────────────────────  │                     │
│            │  [Historial de chat]         │                     │
│            │                              │                     │
│            │  [__________________] [➤]    │                     │
│            └──────────────────────────────┘                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- No afecta layout permanente
- Puede moverse y redimensionarse
- Solo aparece cuando se necesita
- Máximo espacio para documento cuando no se usa

**Contras:**
- Puede tapar contenido relevante
- Requiere abrir/cerrar constantemente
- Pierde contexto visual al cerrar
- Menos inmediato

**Esfuerzo de implementación:** Bajo

---

### Opción D: Integración en Workspace con Pestaña

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                                        │
├─────────────────────────────────────────────────────────────────┤
│  [Texto] [Entidades] [Alertas] [Relaciones] [💬 Asistente]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Vista de la pestaña seleccionada                              │
│                                                                  │
│   (Si es Asistente: chat a pantalla completa con                │
│    opción de ver documento en split view)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Consistente con la navegación existente
- Espacio completo para el chat
- Clara separación de funcionalidades

**Contras:**
- No permite ver documento y chat simultáneamente (sin split)
- Requiere cambiar de pestaña constantemente
- Pierde contexto del documento

**Esfuerzo de implementación:** Bajo

---

### Opción E: Barra de Comandos (Command Palette Style)

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌─────────────────────────────────────────────────┐          │
│    │ 🔍 Pregunta al asistente...                     │          │
│    │ ─────────────────────────────────────────────── │          │
│    │ > ¿Quién es el protagonista?                    │          │
│    │ > ¿Cuántos capítulos tiene?                     │          │
│    │ > Resume el capítulo 3                          │          │
│    └─────────────────────────────────────────────────┘          │
│                                                                  │
│                     Visor de Documento                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Muy rápido de invocar (Ctrl+K o similar)
- No ocupa espacio permanente
- Familiar para usuarios técnicos
- Sugerencias de preguntas frecuentes

**Contras:**
- No mantiene historial visible
- Menos apropiado para conversaciones largas
- Curva de aprendizaje para usuarios no técnicos

**Esfuerzo de implementación:** Medio-Alto

---

## 4. Recomendación

### Contexto: Layout Actual de la Aplicación

**IMPORTANTE:** La aplicación ya tiene DOS paneles laterales:

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar                                                        │
├──────────────┬────────────────────────────┬─────────────────────┤
│              │                            │                     │
│  SIDEBAR     │     ÁREA CENTRAL           │    INSPECTOR        │
│  IZQUIERDO   │     (contenido principal)  │    DERECHO          │
│              │                            │                     │
│  - Capítulos │     Visor de documento     │  - Detalles de      │
│  - Alertas   │     o pestaña activa       │    entidad          │
│  - Personajes│                            │  - Detalles de      │
│              │                            │    alerta           │
│  (200-400px) │     (flexible)             │  (250-500px)        │
│              │                            │                     │
└──────────────┴────────────────────────────┴─────────────────────┘
```

Añadir un TERCER panel lateral no es viable: reduciría excesivamente el espacio central para el documento.

### Opción Recomendada: **D (Pestaña en Sidebar) + B (Panel Inferior) como alternativa**

**Justificación:**

1. **Integración con el layout existente:**
   - El sidebar izquierdo ya tiene pestañas (Capítulos, Alertas, Personajes)
   - Añadir una pestaña "💬 Asistente" es consistente con el diseño actual
   - No requiere cambios estructurales en el layout

2. **Para el usuario tipo** (corrector literario):
   - Necesita consultar el documento mientras pregunta
   - Las preguntas suelen ser iterativas ("¿y en qué capítulo?" "¿qué más dice sobre él?")
   - Cambiar entre pestañas del sidebar es un flujo natural

3. **Alternativa: Panel Inferior Colapsable (Opción B)**
   - Si el usuario necesita ver capítulos/alertas Y chatear simultáneamente
   - Panel inferior que aparece bajo el área central
   - Se puede colapsar cuando no se usa
   - Similar a la consola de desarrollo (familiar para algunos usuarios)

4. **Implementación gradual:**
   - Fase 1: Pestaña en sidebar (más simple, integrado)
   - Fase 2: Panel inferior opcional para usuarios que lo prefieran
   - Fase 3: Integración con selección de texto

### ¿Por qué NO Panel Lateral (Opción A)?

- La app YA tiene dos paneles laterales ocupando ~450-900px
- En pantallas de 1920px, quedarían solo ~1000px para el documento + chat
- En pantallas de 1366px (laptops comunes), sería inutilizable
- Rompe la coherencia visual del diseño existente

---

## 5. Funcionalidades Propuestas

### 5.1 MVP (Mínimo Viable)

| Funcionalidad | Prioridad | Complejidad |
|---------------|-----------|-------------|
| Input de texto para preguntas | Alta | Baja |
| Respuesta del LLM | Alta | Media |
| Indicador de "pensando..." | Alta | Baja |
| Historial de la sesión | Media | Baja |
| Copiar respuesta | Media | Baja |

### 5.2 Versión Completa

| Funcionalidad | Prioridad | Complejidad |
|---------------|-----------|-------------|
| RAG con búsqueda semántica | Alta | Alta |
| Citas con enlaces al documento | Alta | Media |
| Seleccionar texto → preguntar sobre él | Alta | Media |
| Sugerencias de preguntas | Media | Media |
| Exportar conversación | Baja | Baja |
| Múltiples conversaciones | Baja | Media |

### 5.3 Interacciones Especiales

1. **Click en entidad → "Háblame de [nombre]"**
2. **Seleccionar párrafo → "¿Hay inconsistencias aquí?"**
3. **Click en alerta → "Explica esta alerta"**

---

## 6. Consideraciones de UX

### 6.1 Indicadores de Estado

```
Estados del chat:
- 🟢 Listo para preguntar
- 🟡 Buscando en documento... (RAG)
- 🟡 Generando respuesta... (LLM)
- 🔴 Error (con mensaje claro)
```

### 6.2 Gestión de Expectativas

- Mostrar tiempo estimado de respuesta
- Indicar que es un modelo local (puede no ser perfecto) pero tiene la ventaja de que nada se sube a internet
- Permitir cancelar preguntas largas
- Mostrar qué partes del documento se usaron como contexto

### 6.3 Accesibilidad

- Soporte completo de teclado
- Alto contraste para mensajes
- Tamaño de texto configurable
- Screen reader compatible

---

## 7. Estimación de Esfuerzo

| Fase | Componentes | Descripción |
|------|-------------|-------------|
| **Fase 1: Pestaña Sidebar** | UI en sidebar existente, integración Ollama | Chat básico como nueva pestaña del sidebar izquierdo |
| **Fase 2: Panel Inferior** | Layout colapsable, persistencia historial | Alternativa para ver chat + otras pestañas simultáneamente |
| **Fase 3: RAG** | Embeddings index, búsqueda semántica | Contexto inteligente del documento |
| **Fase 4: Integraciones** | Selección de texto, citas clickeables | Flujo bidireccional documento ↔ chat |

---

## 8. Conclusión: ¿Merece la Pena?

### Argumentos a Favor

1. **Diferenciador competitivo**: Pocas herramientas de corrección ofrecen esto
2. **Valor añadido significativo**: Ahorra tiempo en consultas manuales
3. **Infraestructura existente**: Ya tenemos Ollama y embeddings
4. **Usuario lo pide**: Demanda real del mercado
5. **Extensibilidad**: Base para futuras funciones de IA

### Argumentos en Contra

1. **Complejidad**: Añade código y puntos de fallo
2. **Expectativas**: Los usuarios pueden esperar calidad GPT-4
3. **Recursos**: Requiere más RAM y CPU
4. **Mantenimiento**: Modelos LLM evolucionan rápidamente

### Veredicto: **SÍ MERECE LA PENA**

**Recomendación:** Implementar en fases, empezando por MVP modal. Validar con usuarios antes de invertir en RAG completo.

---

## 9. Próximos Pasos

1. [ ] Validar diseño con usuarios reales (mockups)
2. [ ] Definir prompts del sistema para el LLM
3. [ ] Implementar MVP (Fase 1)
4. [ ] Testing con documentos reales
5. [ ] Iterar según feedback

---

*Documento creado: 2026-01-20*
*Autor: Claude Code (asistente IA)*
*Versión: 1.0*
