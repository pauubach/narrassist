---
name: review-pr
description: "Revisión de un Pull Request con el mismo 3-agente model que /pre-push (Abogado + Escéptico + Árbitro) usando el MCP de GitHub para leer el diff real. Invocar cuando el usuario diga 'revisa el PR #N', 'dame feedback del PR', 'haz code review del PR', 'revisa antes de mergear'."
---

# /review-pr — Revisión de Pull Request con 3 agentes

## Cuándo usar

- Antes de hacer merge de un PR externo o de un colaborador.
- Para review formal de tu propio PR antes de solicitar aprobación.
- Como alternativa a `/pre-push` cuando el diff ya está en GitHub.

## Argumentos

- `#N` — número del PR (obligatorio)
- `--light` — solo Escéptico + Árbitro (omitir Abogado), para PRs de corrección rápida
- `--publish` — publicar el veredicto del Árbitro como comentario en el PR (**siempre pedir confirmación antes**)

## Flujo

### Paso 1 — Cargar datos del PR

```
mcp__github__get_pull_request(pullNumber: N)
mcp__github__get_pull_request_files(pullNumber: N)
mcp__github__get_pull_request_comments(pullNumber: N)
mcp__github__get_pull_request_status(pullNumber: N)
```

Extraer: título, descripción, archivos cambiados, checks, comentarios existentes.

### Paso 2 — CI status

Mostrar tabla de checks (igual que `/ci-status`). Si hay fallos bloqueantes → avisar pero continuar el review (el review puede identificar la causa).

### Paso 3 — Review 3 agentes

En **un único mensaje**, 2 tool calls paralelos:

#### 🟢 Abogado (general-purpose, sonnet)
```
Actúa como ABOGADO DEFENSOR del PR #N.

PR: <título + descripción>
Archivos: <lista de archivos cambiados con +/- stats>
Diff: <diff completo de get_pull_request_files>

Tu rol: identificar y articular los puntos fuertes del PR.
¿Qué problema resuelve bien? ¿Qué decisiones de diseño son correctas?
¿Hay tests adecuados para los cambios? ¿Sigue los patrones del proyecto?

Output: 5-8 bullets con fortalezas concretas (archivo:línea donde aplica).
```

#### 🔴 Escéptico (general-purpose, sonnet) — usa perspectiva de manuscript-security
```
Actúa como REVIEWER ESCÉPTICO.

PR: <título + descripción>
Diff: <diff completo>

Áreas de foco (en este orden de prioridad):
1. Seguridad: ¿algún cambio envía datos de manuscritos a internet? ¿path traversal?
   ¿XSS en frontend (v-html con datos de usuario)? Ver .claude/rules/security.md.
2. Corrección: ¿Result pattern roto? ¿type hints faltantes en funciones públicas?
   ¿# type: ignore / # noqa / eslint-disable introducidos?
3. Tests: ¿los cambios tienen tests? ¿edge cases cubiertos?
4. Acoplamientos: ¿nuevas dependencias entre capas (core ↔ nlp ↔ parsers)?

Output: tabla | Hallazgo | Archivo:línea | Severidad 🔥/⚠️/🧹 | Tipo |
```

#### ⚖️ Árbitro (general-purpose, opus) — secuencial tras los anteriores
```
Actúa como ÁRBITRO de code review.

Output Abogado: <pegar>
Output Escéptico: <pegar>
PR diff: <resumir si es muy largo>

Tu output:
1. Tabla: | Hallazgo | Fuente | Severidad | Confianza ✅/🟡/🔺 | Acción |
2. Veredicto: ✅ APPROVE / ⚠️ REQUEST CHANGES / ❌ BLOCK
3. Si ⚠️: listar cambios mínimos para aprobar.
4. Si ❌: listar qué bloquea exactamente.
```

### Paso 4 — Publicar (solo con `--publish` y OK explícito del usuario)

Mostrar al usuario el texto que se publicará. Esperar confirmación **explícita**. Entonces:

```
mcp__github__add_issue_comment(issueNumber: N, body: "<veredicto del Árbitro>")
```

O para review formal:
```
mcp__github__create_pull_request_review(pullNumber: N, event: "COMMENT"|"APPROVE"|"REQUEST_CHANGES", body: "<veredicto>")
```

**NUNCA** publicar sin confirmación explícita del usuario.

## Output final

Tabla de hallazgos + veredicto del Árbitro. Si `--publish` no se pasa, mostrar solo localmente.
