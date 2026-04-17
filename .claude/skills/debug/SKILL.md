---
name: debug
description: "Investigación estructurada de un bug: aislar el problema con un subagente Explore, diagnosticar causa raíz, proponer fix mínimo, escribir test de regresión. Invocar cuando el usuario diga 'estoy debuggeando X', 'por qué falla esto', 'investiga este bug', 'no entiendo por qué pasa Y', 'el test falla pero no sé por qué', 'hay un crash en producción'. Ejemplos: 'por qué falla test_multiple_discourse_markers_filtered', 'el NER no detecta este personaje', 'hay un UnicodeDecodeError en el parser de EPUB'."
---

# /debug — Investigación estructurada de bug

## Flujo

### 1. Capturar el síntoma

Pedir al usuario (o inferir del contexto):
- ¿Qué input produce el fallo?
- ¿Qué output esperaba vs. qué output ve?
- ¿Stack trace, log, alerta concreta?
- ¿Se reproduce siempre o intermitente?

Si falta contexto clave → preguntar antes de buscar a ciegas.

### 2. Aislar con subagente Explore

```
subagent_type: "Explore"
model: "sonnet"
thoroughness: "medium"
prompt: "Investigar un bug en narrassist.

Síntoma: <descripción>
Input problemático: <ejemplo>
Output esperado vs. real: <...>

Tu tarea:
1. Localizar el/los archivos responsables de esta funcionalidad.
2. Trazar el flujo de datos desde el punto de entrada hasta el síntoma.
3. Identificar 2-3 hipótesis concretas sobre dónde está el bug (ruta:línea).
4. Para cada hipótesis, indicar cómo validarla/descartarla.

NO proponer fix aún. Solo diagnóstico."
```

### 3. Validar hipótesis

Con las hipótesis del Explore:
- Leer los archivos concretos.
- Ejecutar scripts de reproducción mínimos si aplica.
- Si el bug toca NLP: probar con un texto mínimo que dispare el fallo.
- Si el bug toca DB: consultar con SQLite directamente (`sqlite3 ~/.narrative_assistant/app.db`).
- Si el bug toca API: `curl` al endpoint local.

### 4. Diagnóstico

Presentar al usuario:
```
## Diagnóstico

Bug: <descripción precisa>
Archivo: <ruta:línea>
Causa raíz: <explicación>

Fix propuesto:
  <diff o pseudo-código>

Test de regresión propuesto:
  <ubicación + caso>
```

### 5. Aplicar fix (con confirmación)

Esperar OK → editar.

### 6. Test de regresión (MANDATORY)

**No cerrar el bug sin test de regresión.** Invocar `/test` para añadir un caso que falle sin el fix y pase con él.

### 7. Verificar con /check

Ejecutar `/check` completo → confirmar que nada más se rompió.

## Anti-patrones a evitar

- **NO** añadir `# noqa` o `# type: ignore` como "fix" — eso oculta el problema.
- **NO** añadir `try: except: pass` sin log específico — oculta el bug, no lo arregla.
- **NO** proponer fixes defensivos ("por si acaso") que no están justificados por el bug real.
- **NO** fixear más cosas aparte del bug reportado en el mismo commit — si descubres otros bugs, abrir seguimiento aparte.
