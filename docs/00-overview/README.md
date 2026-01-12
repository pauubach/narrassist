# Resumen Ejecutivo

[← Volver al índice principal](../../README.md)

---

## Visión del Proyecto

**Asistente de Corrección Narrativa y Estilo (Offline)**: Una herramienta de análisis narrativo con IA que funciona **100% offline**, garantizando la confidencialidad del manuscrito.

### Propuesta de Valor Única

> Es la **única** herramienta de análisis narrativo con IA para español que:
> - Funciona completamente offline (sin subir manuscritos a la nube)
> - Está diseñada para correctores profesionales (no escritores)
> - Detecta inconsistencias narrativas complejas (focalización, timeline, voz)

---

## Datos Básicos

| Aspecto | Valor |
|---------|-------|
| **Usuario objetivo** | Correctores profesionales |
| **Plataforma principal** | macOS (con soporte Windows) |
| **Hardware mínimo** | 16GB RAM |
| **Idioma inicial** | Español |
| **Tolerancia a tiempos** | Alta (minutos aceptables) |

---

## Principio Fundamental: Trazabilidad Universal

> **Todo dato mostrado debe tener una fuente verificable.**

Cada pieza de información extraída o inferida debe indicar exactamente de dónde proviene en el texto original.

### Por qué es esencial

1. **Verificabilidad**: El corrector puede comprobar cada afirmación con un clic
2. **Confianza**: Distinguir datos extraídos automáticamente vs añadidos manualmente
3. **Corrección de errores**: Si el NLP se equivoca, el usuario sabe qué revisar
4. **Contexto editorial**: El corrector necesita ver el contexto original

### Implementación por tipo de dato

| Tipo de información | Formato de fuente | Ejemplo |
|---------------------|-------------------|---------|
| Atributo de personaje | Cap.X, pág.Y, línea Z | "Ojos verdes" → Cap.2, pág.56, lín.12 |
| Lugar mencionado | Cap.X, pág.Y | "Casa Mendoza" → Cap.4, pág.89 |
| Evento temporal | Cap.X, pág.Y | "Boda de María" → Cap.12, pág.245 |
| Hecho establecido | Cap.X, pág.Y | "María no sabe conducir" → Cap.3, pág.67 |
| Diálogo | Cap.X, pág.Y, hablante | "—Nunca te perdonaré" → Cap.8, pág.156, María |
| Métrica estilística | Rango de capítulos | "Long. oraciones: 18.3" → Cap.1-34 |

---

## Documentos de esta Sección

| Documento | Descripción |
|-----------|-------------|
| [Objetivos y Alcance](./goals-and-scope.md) | Usuario objetivo, tolerancia a errores, decisiones confirmadas |
| [Definición MVP](./mvp-definition.md) | 12 capacidades del MVP ampliado |
| [Correcciones y Riesgos](./corrections-and-risks.md) | **Expectativas realistas de NLP** - Leer antes de implementar |

---

## Siguiente Paso

Si es tu primera vez, lee [Correcciones y Riesgos](./corrections-and-risks.md) antes de comenzar los STEPs.

Luego, ve directamente a [STEP 0.1: Configuración del Entorno](../../steps/phase-0/step-0.1-environment.md).
