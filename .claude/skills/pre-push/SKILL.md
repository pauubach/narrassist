---
name: pre-push
description: "Validación completa antes de 'git push': /check completo + revisión multi-agente 3 perspectivas (Abogado / Escéptico con perspectiva manuscript-security / Árbitro) sobre todos los commits a pushear. Invocar cuando el usuario diga 'vamos a pushear', 'revisa antes de push', 'pre-push', 'antes de subir a GitHub'. Ejemplos: 'revisa todo antes de pushear', 'pre-push de los últimos 3 commits', 'valida el push del feature de exportación'."
---

# /pre-push — Validación completa antes del push

## Flujo

### Paso 1 — /check completo

Ejecutar `/check` en modo completo (no solo affected): lint + types + tests completos en ambos stacks. Si algo falla → **parar**, el push se aborta.

### Paso 2 — Medir scope del push

```bash
git fetch origin
git log --oneline @{u}..HEAD  # commits a pushear
git diff @{u}..HEAD --stat
git diff @{u}..HEAD | wc -l
```

### Paso 3 — Review multi-agente (obligatorio, por política de auto-memoria)

**Los 3 agentes revisan TODOS los commits a pushear.** En un único mensaje, 2 tool calls en paralelo (Abogado + Escéptico). Después, secuencialmente, el Árbitro.

#### 🟢 Abogado (Agent sonnet)
```
subagent_type: "general-purpose"
model: "sonnet"
prompt: "Actúa como ABOGADO DEFENSOR del siguiente cambio.
Tu rol: argumentar a favor del cambio, resaltar fortalezas,
dar contexto que ayude a pesar críticas. No suavices problemas
reales, pero asegúrate de que los puntos fuertes estén
articulados. Revisa TODOS los commits.

Commits a revisar:
<git log --oneline @{u}..HEAD>

Diff completo:
<git diff @{u}..HEAD>

Contexto del proyecto: <leer CLAUDE.md + docs/ARCHITECTURE si existe>

Output: 5-10 bullet points con fortalezas concretas (archivos/líneas)."
```

#### 🔴 Escéptico (Agent sonnet) — perspectiva .claude/agents/manuscript-security.md
```
subagent_type: "general-purpose"
model: "sonnet"
prompt: "Actúa como REVIEWER ESCÉPTICO MUY CRÍTICO adoptando la perspectiva de
Manuscript Security (ver .claude/agents/manuscript-security.md).

Prioridad de revisión (en este orden):
1. SEGURIDAD (🔴 = bloquea el push):
   - ¿Algún cambio envía datos de manuscritos fuera de localhost?
   - ¿Hay llamadas a requests/httpx a hosts no en la allowlist?
   - ¿Parsers sin validate_file() antes de abrir archivos?
   - ¿Llamadas a Ollama sin sanitize_for_llm()?
   - ¿Logging que incluya texto de manuscrito?
2. CORRECCIÓN:
   - Result pattern roto en operaciones fallibles.
   - Type hints faltantes en funciones públicas.
   - # type: ignore / # noqa / eslint-disable introducidos.
3. TESTS: ¿cambios sin test de regresión?
4. ACOPLAMIENTOS: nuevas dependencias entre capas.

Commits a revisar:
<git log --oneline @{u}..HEAD>

Diff completo:
<git diff @{u}..HEAD>

Output: tabla | Hallazgo | Archivo:línea | Severidad (🔥/⚠️/🧹) | Tipo (security/bug/test/coupling) | Explicación |"
```

### Paso 4 — ⚖️ Árbitro (Agent opus, SIEMPRE explícito)

```
subagent_type: "general-purpose"
model: "opus"
prompt: "Actúa como ÁRBITRO NEUTRAL. Tienes el output del Abogado
y del Escéptico sobre el mismo diff. Tu rol: filtrar falsos positivos,
pesar severidad real, decidir qué bloquea el push y qué es sugerencia.

Output Abogado:
<pegar>

Output Escéptico:
<pegar>

Diff:
<git diff @{u}..HEAD>

Tu output:
1. Tabla: | Hallazgo | Fuente (A/E/Ambos) | Severidad | Confianza ✅ Consenso / 🟡 Mayoría / 🔺 Disputado | Acción |
2. Veredicto: ✅ PUSH OK / ⚠️ PUSH CON RESERVAS / ❌ NO PUSH
3. Si hay [BLOQUEA] con ✅ Consenso → ❌ NO PUSH y listar qué arreglar antes."
```

### Paso 5 — Actualización de docs

Si el diff toca módulos documentados en `docs/`:
- Revisar si los docs afectados están desincronizados.
- Si hay drift → señalarlo al usuario como follow-up (no bloquea el push, pero no se olvida).

### Paso 6 — Presentar veredicto al usuario

```
## Pre-push verdict

Checks: ✅ lint + types + tests (backend + frontend)
Commits a pushear: N
Líneas cambiadas: N

Review multi-agente: <✅ | ⚠️ | ❌>

Hallazgos bloqueantes:
  - ...

Hallazgos sugeridos:
  - ...

Docs desactualizados:
  - ...

¿Procedo con el push?
```

**NUNCA** `git push` sin OK explícito del usuario. **NUNCA** `--force` a `master` sin instrucción directa del usuario.
