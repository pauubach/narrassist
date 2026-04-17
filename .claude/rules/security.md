---
description: "Reglas de seguridad del proyecto: aislamiento de manuscritos, path traversal, sanitización de inputs LLM, permisos de red. Aplicar al editar parsers, clientes LLM, sistemas de licencias, I/O de archivos o cualquier código que haga requests de red."
globs: ["src/narrative_assistant/parsers/**/*.py", "src/narrative_assistant/llm/**/*.py", "src/narrative_assistant/core/**/*.py", "api-server/**/*.py"]
---

# Seguridad — Reglas inviolables

## Principio cero: aislamiento de manuscritos

**Los manuscritos NUNCA salen de la máquina del usuario.** Este es el contrato con el usuario y lo diferencia de cualquier asistente de escritura basado en cloud.

### Hosts permitidos

| Host | Uso | Cuándo |
|---|---|---|
| `localhost` / `127.0.0.1:11434` | Ollama LLM | Siempre, análisis del manuscrito |
| `localhost` / `127.0.0.1` (otros puertos) | API server interno, Tauri IPC | Siempre |
| `huggingface.co`, `cdn-lfs.huggingface.co` | Descarga inicial modelos | Solo primera vez, vía `ModelManager` |
| `spacy.io`, `github.com/explosion` | Descarga inicial spaCy | Solo primera vez |
| Endpoint oficial de licencias del proyecto | Verificación de licencias | Al activar / refrescar |

### Hosts PROHIBIDOS en código nuevo

- `api.openai.com`, `api.anthropic.com`, cualquier LLM cloud.
- Servicios de analytics (`google-analytics`, `segment`, `mixpanel`, `posthog`, `sentry`).
- Crash reporters remotos.
- Cualquier host que reciba texto del manuscrito como input.

### Cómo validar

Si un PR introduce código que hace `requests.get/post`, `httpx.AsyncClient`, `urllib.request`, `fetch` (frontend), `axios`, etc.:
1. Verificar que el host destino está en la tabla de permitidos.
2. Verificar que el **body** no contiene `manuscript`, `text`, `content` del usuario.
3. Si lo contiene → **RECHAZAR** el cambio.

## Path traversal en parsers

**TODO** parser de archivos (DOCX, TXT, PDF, EPUB) debe validar la ruta ANTES de abrir:

```python
from narrative_assistant.parsers.sanitization import validate_file_path

def parse(self, path: Path) -> Result[RawDocument]:
    validation = validate_file_path(path, allowed_extensions={".docx"})
    if validation.is_failure:
        return validation
    # ... continuar
```

Chequeos obligatorios:
- Ruta resuelve dentro de un directorio permitido (no `../../etc/passwd`).
- Extensión coincide con el parser.
- Tamaño < límite (evita DoS por archivo gigante).
- Magic bytes del archivo coinciden con la extensión (evita uploads maliciosos).

## Sanitización anti-prompt-injection

Cuando el texto del manuscrito se envía a Ollama vía prompt:

- **SIEMPRE** pasar por `src/narrative_assistant/llm/sanitization.py` → `sanitize_for_llm()`.
- Marcar fronteras claras: delimitadores `<manuscript>...</manuscript>` en el prompt.
- Prompts centralizados en `src/narrative_assistant/llm/prompts.py` — no crear prompts ad-hoc en detectores.
- Cadenas de usuario NUNCA pueden reescribir el "system prompt".

## Telemetría y logging

- **PROHIBIDA** telemetría o analytics de cualquier tipo.
- Logs locales solo (rotación con `logging.handlers.RotatingFileHandler`).
- **NUNCA** loggear texto completo del manuscrito en niveles `INFO`/`DEBUG` si esos logs pueden acabar en CI o crash reports. Si hace falta debug local, usar nivel `DEBUG` + opt-in del usuario.

## Auto-updates

- **PROHIBIDOS** auto-updates silenciosos de modelos, dependencias, o del binario.
- El usuario decide cuándo actualizar (manual `pip install -U`, `ollama pull`, descarga de nueva release).

## Ollama y LLM local

- Cliente Ollama → siempre `http://localhost:11434` configurable vía `NA_OLLAMA_HOST` (debe seguir apuntando a host local; si alguien configura un host remoto, advertir fuertemente en el setup).
- **NUNCA** fallback a LLM cloud si Ollama no está disponible — el usuario debe saber que no hay análisis LLM disponible.

## Frontend (Tauri + Vue)

- Configurar Tauri allowlist con el mínimo de APIs necesarias.
- `dangerous-remote-url-ipc-access` → **off**.
- `withGlobalTauri` → **off** salvo debug.
- No cargar recursos externos en el `index.html` (CSS, fuentes) que delaten la actividad del usuario.

## Code review checklist (para /pre-push)

Cuando el Escéptico de `/pre-push` revise, debe marcar BLOQUEANTE si detecta:
- [ ] Nuevo `requests` / `httpx` / `fetch` a host no permitido.
- [ ] Manuscrito o fragmento de él enviado como body a un endpoint externo.
- [ ] Falta `validate_file_path` en nuevo parser.
- [ ] `sanitize_for_llm` ausente al construir prompt.
- [ ] Logging de texto de manuscrito en `INFO`+.
- [ ] `# type: ignore`, `# noqa`, `@ts-ignore` añadidos.
- [ ] Dependencia nueva que hace phone-home (analytics, crash reports, auto-updates).
