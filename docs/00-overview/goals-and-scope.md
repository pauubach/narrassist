# Objetivos y Alcance

[← Volver a Overview](./README.md) | [← Índice principal](../../README.md)

---

## Usuario Objetivo

**Correctores profesionales** (no escritores)

El sistema está diseñado específicamente para:
- Correctores editoriales que trabajan con manuscritos de ficción
- Profesionales que necesitan garantizar confidencialidad
- Usuarios con tolerancia a tiempos de análisis largos (minutos aceptables)

---

## Datos Técnicos

| Aspecto | Valor |
|---------|-------|
| **Plataforma principal** | macOS (con soporte Windows) |
| **Hardware mínimo** | 16GB RAM |
| **Idioma inicial** | Español |
| **Conexión requerida** | Ninguna (100% offline) |
| **Tolerancia a tiempos** | Alta (minutos aceptables) |

---

## Decisiones Confirmadas

### Sobre falsos positivos

**Decisión del promotor**: Los falsos positivos **NO son un problema**.

El corrector es quien decide si una alerta es correcta o no, y lo indica a la aplicación.

### Porcentajes de confianza

Se mantienen y son **configurables**:
- El corrector puede definir qué porcentaje corresponde a cada color (rojo, naranja, etc.)
- Se pueden configurar umbrales **diferentes por tipo de error**
- Esto permite adaptar la precisión según preferencias del corrector

---

## Alcance del MVP

### Incluido en MVP

| Capacidad | Descripción |
|-----------|-------------|
| Parser DOCX | Extracción de texto preservando estructura |
| Detección de estructura | Capítulos, escenas, diálogos |
| NER básico | Extracción de personajes, lugares |
| Correferencia | Resolución de pronombres → nombres |
| Fusión manual | Unificación de entidades duplicadas |
| Atributos | Extracción de características de personajes |
| Alertas de inconsistencia | Detección de contradicciones |
| Repeticiones | Léxicas y semánticas |
| Perfiles de voz | Métricas estilométricas básicas |
| Hoja de estilo | Exportación de decisiones editoriales |
| CLI | Interfaz de línea de comandos |

### Diferido a fases posteriores

| Capacidad | Razón | Fase |
|-----------|-------|------|
| Timeline automático | Requiere comprensión causal compleja | Fase 2+ |
| Focalización automática | No existe tecnología madura | Fase 2+ |
| LLM integrado | Añade complejidad y requisitos | Opcional |
| UI gráfica (Tauri) | No esencial para validación | Fase 2+ |

---

## Principios de Diseño

### 1. Honestidad sobre limitaciones
No prometer lo que la tecnología no puede dar.

### 2. Útil desde el día uno
El MVP debe funcionar aunque no sea perfecto.

### 3. Híbrido por diseño
Automatización + validación humana siempre.

### 4. Hitos de validación
No avanzar de fase sin confirmar viabilidad.

---

## Propuesta de Valor vs Competencia

| Característica | ProWritingAid | Grammarly | Scrivener | **Este sistema** |
|----------------|---------------|-----------|-----------|------------------|
| Análisis de coherencia narrativa | ❌ | ❌ | ❌ | ✅ |
| Fichas de personajes automáticas | ❌ | ❌ | Manual | ✅ |
| Timeline automático | ❌ | ❌ | Manual | ✅ (Fase 2) |
| Perfiles de voz por personaje | ❌ | ❌ | ❌ | ✅ |
| **100% Offline** | ❌ | ❌ | ✅ | ✅ |
| **Sin subida de archivos** | ❌ | ❌ | ✅ | ✅ |
| Español nativo | Limitado | Limitado | ✅ | ✅ |
| Para correctores profesionales | ❌ | ❌ | Parcial | ✅ |

---

## Siguiente Paso

Ver [Definición MVP](./mvp-definition.md) para el detalle de las 12 capacidades del MVP.
