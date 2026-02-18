# Architecture Decision Records (ADR)

Este directorio contiene las decisiones arquitectónicas clave del proyecto Narrative Assistant.

## Formato

Cada ADR sigue la estructura estándar:

- **Título**: Descripción breve de la decisión
- **Estado**: Aceptada, Propuesta, Rechazada, Reemplazada
- **Contexto**: Situación que motivó la decisión
- **Decisión**: Qué se decidió hacer
- **Consecuencias**: Impactos positivos y negativos

## Índice de Decisiones

| ADR | Título | Estado | Fecha |
|-----|--------|--------|-------|
| [ADR-001](001-sqlite-database.md) | Usar SQLite como base de datos | Aceptada | 2025-12-20 |
| [ADR-002](002-llm-local.md) | LLM local con Ollama para análisis semántico | Aceptada | 2026-01-15 |
| [ADR-003](003-multi-model-ner.md) | NER multi-modelo con votación | Aceptada | 2026-01-15 |
| [ADR-004](004-offline-first.md) | Arquitectura offline-first | Aceptada | 2025-12-20 |
| [ADR-005](005-primevue-ui.md) | PrimeVue para componentes de UI | Aceptada | 2026-01-10 |

## Contexto del Proyecto

**Narrative Assistant** es una herramienta de corrección de manuscritos para correctores profesionales que prioriza:

1. **Privacidad total**: Los manuscritos nunca salen del ordenador del usuario
2. **Precisión**: Análisis NLP avanzado para español
3. **Usabilidad**: Interfaz accesible para no-técnicos
4. **Performance**: Procesamiento eficiente de documentos grandes (100k+ palabras)

Estas prioridades guían todas las decisiones arquitectónicas.
