# Fase 1: MVP Core

[← Volver a Roadmap](./README.md) | [← Índice principal](../../README.md)

---

## Objetivo

Implementar las capacidades mínimas que aportan valor a los correctores profesionales.

**Prioridad**: P0-P1
**Duración estimada**: 50-80 horas

---

## Capacidades del MVP (11 total)

| # | Capacidad | Tipo | STEPs |
|---|-----------|------|-------|
| 1 | Estructura del documento | Infraestructura | 1.1, 1.2 |
| 2 | Extracción de entidades + coref | Infraestructura | 1.3, 2.1 |
| 3 | Consistencia nombres/grafías | Alerta automática | 3.1 |
| 4 | Sugerencia de atributos | Propuesta + validación | 2.3, 2.4 |
| 5 | Inconsistencias de atributos | Alerta automática | 3.2 |
| 6 | Timeline con ordenación parcial | Híbrido | 4.1-4.3 |
| 7 | Perfiles de voz + alertas | Alerta automática | 5.1-5.4 |
| 8 | Verificación de focalización | Declaración + verificación | 6.1-6.2 |
| 9 | Repeticiones léxicas y semánticas | Alerta automática | 3.3 |
| 10 | Cambios bruscos de registro | Alerta automática | 5.3-5.4 |
| 11 | Exportación hoja de estilo | Documentación | 7.1-7.3 |

---

## STEPs de la Fase 1

### Bloque 1: Parseo y Estructura

| STEP | Nombre | Complejidad | Horas |
|------|--------|-------------|-------|
| [1.1](../../steps/phase-1/step-1.1-docx-parser.md) | Parser DOCX | S | 2-4h |
| [1.2](../../steps/phase-1/step-1.2-structure-detector.md) | Detector de estructura | M | 4-6h |
| [1.3](../../steps/phase-1/step-1.3-ner-pipeline.md) | Pipeline NER | M | 6-8h |
| [1.4](../../steps/phase-1/step-1.4-dialogue-detector.md) | Detector de diálogos | M | 4-6h |

### Bloque 2: Entidades y Atributos

| STEP | Nombre | Complejidad | Horas |
|------|--------|-------------|-------|
| [2.1](../../steps/phase-2/step-2.1-coreference.md) | Correferencia básica | M | 6-8h |
| [2.2](../../steps/phase-2/step-2.2-entity-fusion.md) | Fusión de entidades | M | 4-6h |
| [2.3](../../steps/phase-2/step-2.3-attribute-extraction.md) | Extracción de atributos | L | 8-12h |
| [2.4](../../steps/phase-2/step-2.4-attribute-consistency.md) | Consistencia de atributos | M | 4-6h |

### Bloque 3: Alertas Básicas

| STEP | Nombre | Complejidad | Horas |
|------|--------|-------------|-------|
| [3.1](../../steps/phase-3/step-3.1-name-variants.md) | Variantes de grafía | S | 3-4h |
| [3.2](../../steps/phase-3/step-3.2-lexical-repetitions.md) | Repeticiones léxicas | M | 4-6h |
| [3.3](../../steps/phase-3/step-3.3-semantic-repetitions.md) | Repeticiones semánticas | M | 6-8h |

---

## Tecnologías del MVP

| Componente | Tecnología | Uso |
|------------|------------|-----|
| NER español | `es_core_news_lg` (spaCy) | Extracción de entidades |
| Correferencia | Coreferee | Resolución de pronombres |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | Similitud semántica |
| Estilometría | Métricas estadísticas | Perfiles de voz, registro |
| Persistencia | SQLite | Memoria narrativa |
| LLM local | Opcional (Llama, Qwen) | Desambiguación compleja |

---

## Limitaciones Conocidas del MVP

### NER
- **F1 esperado**: 60-70% en textos literarios
- **Problema**: Modelos entrenados en texto periodístico
- **Mitigación**: Gazetteers dinámicos + validación manual

### Correferencia
- **F1 esperado**: 45-55%
- **Problema crítico**: Pro-drop hace ~40-50% de sujetos invisibles
- **Mitigación**: Fusión manual OBLIGATORIA

### Focalización
- **Viabilidad**: BAJA
- **Tasa de error**: >50% por pro-drop
- **Mitigación**: Solo verificar sujetos EXPLÍCITOS

---

## Interfaz MVP: CLI

El MVP se entrega con interfaz de línea de comandos:

```bash
# Crear proyecto
narrative-assistant new "Mi Novela" --language es

# Importar documento
narrative-assistant import mi_novela.docx

# Ejecutar análisis
narrative-assistant analyze

# Ver alertas
narrative-assistant alerts --severity high

# Exportar hoja de estilo
narrative-assistant export style-guide --format md
```

---

## Criterios de Aceptación del MVP

1. ✅ Puede importar documentos DOCX
2. ✅ Detecta capítulos y escenas
3. ✅ Extrae entidades (personajes, lugares)
4. ✅ Resuelve correferencias básicas
5. ✅ Permite fusión manual de entidades
6. ✅ Detecta variantes de grafía
7. ✅ Detecta repeticiones léxicas
8. ✅ Genera alertas con niveles de confianza
9. ✅ Exporta hoja de estilo básica
10. ✅ Funciona en hardware de 16GB RAM

---

## Wireframe del MVP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NARRATIVE ASSISTANT - CLI                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  $ narrative-assistant alerts                                               │
│                                                                              │
│  📊 ALERTAS ENCONTRADAS: 23                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 🔴 CRÍTICO (2)                                                          │ │
│  │    • Cap 3: "ojos verdes" vs Cap 7: "ojos azules" [María]              │ │
│  │    • Cap 5: Acceso a pensamientos de personaje no focal                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ 🟠 ALTO (5)                                                             │ │
│  │    • Cap 2: "Martínez" / "Martinez" - posible inconsistencia           │ │
│  │    • Cap 4: Repetición de "sin embargo" (3 veces en 100 palabras)      │ │
│  │    • ...                                                                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ 🟡 MEDIO (8)                                                            │ │
│  │    • ...                                                                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ 🟢 BAJO (5)                                                             │ │
│  │    • ...                                                                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ 🔵 INFO (3)                                                             │ │
│  │    • ...                                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Usa 'narrative-assistant alert <id>' para ver detalles                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Siguiente Paso

Ver [Fases 2-7: Post-MVP](./phases-2-7-post-mvp.md) para el desarrollo posterior.
