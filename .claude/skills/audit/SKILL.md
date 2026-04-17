---
name: audit
description: "Auditoría profunda de un módulo, feature o área usando el Comité de Expertos documentado en CLAUDE.md (5 subagentes en paralelo + 4 agentes custom + Árbitro opus). Invocar cuando el usuario diga 'audita el módulo X', 'revisa a fondo', 'comité de expertos', 'panel de revisión', 'análisis completo de X'. Ejemplos: 'audita el módulo de correferencias', 'comité de expertos sobre los parsers', 'revisa a fondo el pipeline NLP antes de la release'."
---

# /audit — Auditoría profunda (Comité de Expertos)

Wrappea el Comité de Expertos ya documentado en `CLAUDE.md` → sección "Comité de Expertos para Auditorías".

## Cuándo usar

- Antes de una release mayor.
- Al terminar una feature grande (>700 líneas de diff).
- Cuando el usuario sospecha deuda técnica acumulada en un área.
- Periódicamente para módulos críticos (NLP pipeline, parsers, exporters, auth de licencias).

## Argumentos

- `<módulo>` — scope de la auditoría. Ejemplos: `parsers`, `nlp/coreference_resolver`, `frontend/AlertsDashboard`.
- `--light` — reducir a 2 subagentes (Arquitecto + Árbitro) para módulos no críticos.

## Flujo — modo normal

### Paso 1 — Leer contexto

- `CLAUDE.md` sección del módulo (si existe).
- `docs/02-architecture/SECURITY.md` si el módulo toca manuscritos.
- Los 3-10 archivos principales del módulo (inline, no subagente).

### Paso 2 — Lanzar 5 subagentes en paralelo

En **un solo mensaje**, 5 tool calls paralelos (usar `subagent_type: "Explore"` y `subagent_type: "Plan"` según corresponda, y `general-purpose` con rol explícito para el resto):

#### 🔵 Backend NLP (Explore, sonnet)
```
Revisar: pipeline NLP, manejo de errores (Result pattern), uso correcto de enums
(.value vs enum), cadenas de correferencias, POS tagging, integración con
spaCy/sentence-transformers/Ollama. Listar: violaciones de patrones,
oportunidades de extracción, módulos sobredimensionados (>500 líneas).
```

#### 🟣 Frontend Vue (Explore, sonnet)
```
Revisar: XSS risks (v-html), manejo de error en componentes, gestión de estado
(Pinia/composables), accesibilidad (aria-*), componentes >300 líneas, duplicación
de lógica de formato. Listar hallazgos con ruta:línea.
```

#### 🔴 Seguridad (Explore, sonnet) — perspectiva .claude/agents/manuscript-security.md
```
Revisar con perspectiva Manuscript Security (ver .claude/agents/manuscript-security.md):
checklist completo de aislamiento. Prioridad: 
1. Filtraciones directas (requests/httpx a hosts no permitidos).
2. Logging de texto de manuscrito.
3. Parsers sin validate_file().
4. Llamadas a Ollama sin sanitize_for_llm().
5. Endpoints FastAPI que devuelvan contenido de manuscrito a URL externa.
Bloquear si encuentra cualquier 🔴.
```

#### 🧪 Tests/Coverage (Explore, sonnet)
```
Revisar: gaps de cobertura, edge cases sin testear, tests marcados @heavy que
deberían estar en el camino crítico, tests marcados @xfail que quizás ya no
fallan, fixtures compartidas no usadas. Output: tabla Archivo | ¿Tiene test? |
¿Cubre edge cases? | Riesgo (🔴/🟡/🟢).
```

#### 🏛️ Arquitectura (Plan, sonnet)
```
Revisar patrones arquitectónicos, consistencia (Result pattern, singletons
thread-safe, validación en parsers), principios SOLID, acoplamientos indeseados
entre capas (core ↔ nlp ↔ parsers). Proponer refactors con ROI alto.
```

### Paso 3 — ⚖️ Árbitro (Agent opus)

El Árbitro adopta las perspectivas de los 4 agentes custom del proyecto (ver `.claude/agents/`):

```
subagent_type: "general-purpose"
model: "opus"
prompt: "Actúa como ÁRBITRO del Comité de Expertos. Adopta estas perspectivas:

1. QA Senior — testing, edge cases, cobertura, regresiones.
2. Lingüista Computacional (.claude/agents/nlp-linguist.md) — pro-drop, voseo,
   NER en español, correferencias, calibración de umbrales.
3. Corrector Editorial 15+ años (.claude/agents/narrative-reviewer.md) — accionabilidad
   de alertas, señal/ruido, flujo de trabajo editorial real.
4. Arquitecto Python/FastAPI — Result pattern, singletons, acoplamientos, SOLID.
5. Manuscript Security (.claude/agents/manuscript-security.md) — aislamiento,
   path traversal, logs, sanitize_for_llm().
6. Frontend Engineer (Vue/Tauri) — componentes, estado, accesibilidad, no v-html.
7. Product Owner — priorización, ROI, valor real para escritores/correctores.
8. Prompt Engineer (.claude/agents/prompt-engineer.md) — prompts Ollama, injection,
   chunking, temperatura, few-shot.

Inputs de los 5 subagentes:
<pegar los 5 outputs>

Tu output:
1. Tabla consolidada | Hallazgo | Fuente | Severidad 🔥/⚠️/🧹 | Tipo bug/tech-debt/security/UX | Confianza ✅/🟡/🔺 | Acción propuesta |
2. Priorización: top-5 acciones con mayor ROI para el usuario.
3. Veredicto global: ✅ Saludable / ⚠️ Necesita atención / ❌ Riesgo alto.
4. Riesgos que no se vieron pero que el panel detecta: 2-3 bullets."
```

## Flujo — modo `--light`

Saltarse paso 2 excepto 🏛️ Arquitectura + 🔴 Seguridad. Árbitro como siempre en Opus.

## Output final

Informe en Markdown con:
- Resumen ejecutivo (3-5 líneas).
- Tabla consolidada.
- Top-5 acciones priorizadas.
- Veredicto.

**No implementar** los fixes en este skill — para eso el usuario invocará skills concretos después (`/test`, ediciones directas, `/refactor`).
