# ADR-004: Arquitectura Offline-First

## Estado

**Aceptada** — 2025-12-20 (v0.1.0)

## Contexto

**Requisito fundamental**: Privacidad absoluta de los manuscritos.

Los correctores profesionales trabajan con:
- Manuscritos no publicados de autores
- Contenido confidencial (memorias, ensayos sensibles)
- Material sujeto a NDAs (Non-Disclosure Agreements)

**Riesgo inaceptable**: Enviar texto del manuscrito a internet.

Análisis de arquitecturas alternativas:

| Arquitectura | Privacidad | Latencia | Costo | Disponibilidad | Performance |
|--------------|------------|----------|-------|----------------|-------------|
| **Cloud-first** | ❌ Datos en servidor | ⚡ Rápido | 💰💰 Alto | ☁️ Requiere internet | 🚀 Escalable |
| **Hybrid** | ⚠️ Parcial | ⚡ Media | 💰 Medio | ☁️ Requiere internet | 🚀 Escalable |
| **Offline-first** | ✅ Total | ⚡⚡ Muy rápido | ✅ Gratis | 📴 Siempre disponible | 💻 Local |

**Ejemplos de violación de privacidad**:
- **Grammarly**: Envía texto completo a servidores en EE.UU. (leak de OpenAI, 2023)
- **Google Docs**: Texto indexado para publicidad (ToS)
- **ChatGPT API**: OpenAI retiene datos 30 días (puede entrenar modelos)

**Principio de diseño**: *"El manuscrito nunca debe salir del ordenador del usuario, bajo ninguna circunstancia."*

## Decisión

Implementar arquitectura **offline-first** con los siguientes principios:

### 1. Procesamiento 100% Local

```
┌──────────────────────────────────────┐
│    Tauri App (Escritorio)            │
│  ┌────────────────────────────────┐  │
│  │  Frontend Vue 3                │  │
│  │  (localhost:5173 en dev)       │  │
│  └────────────┬───────────────────┘  │
│               │ HTTP (IPC en prod)   │
│  ┌────────────▼───────────────────┐  │
│  │  FastAPI Backend               │  │
│  │  (localhost:8000)              │  │
│  └────────────┬───────────────────┘  │
│               │                      │
│  ┌────────────▼───────────────────┐  │
│  │  spaCy + NLP local             │  │
│  └────────────┬───────────────────┘  │
│               │                      │
│  ┌────────────▼───────────────────┐  │
│  │  Ollama (localhost:11434)      │  │
│  └────────────────────────────────┘  │
│                                      │
│  Todo corre en 127.0.0.1             │
└──────────────────────────────────────┘
         │
         ▼
   ~/.narrative_assistant/
   ├── data/projects.db (SQLite local)
   ├── models/ (spaCy, embeddings)
   └── backups/
```

**Todas las conexiones son localhost** — nunca se hace request a internet durante el análisis.

### 2. Modelo de Datos Local

- **Base de datos**: SQLite (~/.narrative_assistant/data/projects.db)
- **Modelos NLP**: Cache local (~/.narrative_assistant/models/)
- **Ollama models**: Cache local (~/.ollama/models/)
- **Backups**: Local (~/.narrative_assistant/backups/)

**No hay sincronización cloud** — ni siquiera como opción.

### 3. Conexión a Internet: Solo Descarga Inicial

Internet se usa ÚNICAMENTE para:

| Recurso | Cuándo | Destino | Qué se envía |
|---------|--------|---------|--------------|
| **Modelos NLP** | Primera ejecución | HuggingFace Hub | ❌ Nada (solo GET) |
| **Ollama models** | Setup inicial | ollama.com | ❌ Nada (solo GET) |
| **Licencias** | Validación | *(futuro)* | ❌ Solo hash de activación |

**Nunca se envía**:
- ❌ Texto del manuscrito
- ❌ Entidades detectadas
- ❌ Alertas o correcciones
- ❌ Metadata del proyecto
- ❌ Telemetría o analytics

### 4. Validación de Seguridad

**Auditorías obligatorias**:
- ✅ No hay llamadas a `fetch()`, `axios.post()`, `requests.post()` con datos de usuario
- ✅ No hay SDKs de analytics (Google Analytics, Mixpanel, Sentry)
- ✅ No hay auto-updates (actualización manual controlada por el usuario)
- ✅ Logs solo en disco local, nunca remote logging

**Código prohibido**:
```python
# ❌ PROHIBIDO - enviar datos a internet
import requests
requests.post("https://api.example.com", json={"text": manuscript_text})

# ❌ PROHIBIDO - analytics
import analytics
analytics.track("document_analyzed", {"word_count": 50000})

# ❌ PROHIBIDO - remote logging
import sentry_sdk
sentry_sdk.capture_message("Analysis started")
```

**Código permitido**:
```python
# ✅ PERMITIDO - descarga de modelos
from huggingface_hub import snapshot_download
snapshot_download("spacy/es_core_news_lg")

# ✅ PERMITIDO - localhost
import requests
requests.get("http://localhost:11434/api/tags")  # Ollama local
```

### 5. Transparencia con el Usuario

- **PRIVACY.md**: Documento claro sobre privacidad
- **UI prominente**: Badge "🔒 Offline" en interfaz
- **Logs auditables**: Usuario puede revisar logs para verificar que no hay network calls

## Consecuencias

### Positivas ✅

1. **Privacidad absoluta**: Manuscritos nunca salen del PC, cumple NDAs
2. **Confianza del usuario**: Correctores profesionales pueden usar la herramienta sin riesgo legal
3. **Costo cero**: No hay costos de servidor, base de datos cloud, ni APIs
4. **Latencia mínima**: Todo corre en localhost (sub-100ms)
5. **Sin vendor lock-in**: Usuario controla sus datos 100%
6. **Funciona sin internet**: Ideal para escribir en lugares sin WiFi (aviones, cafés)
7. **No hay downtime**: No depende de servidores externos

### Negativas ⚠️

1. **Requisitos de hardware**:
   - Mínimo 8 GB RAM para modelos NLP
   - 3-6 GB de espacio en disco
   - CPU/GPU suficiente para procesamiento
2. **Setup inicial**:
   - Requiere internet para descargar modelos (~1 GB)
   - Usuario debe instalar Ollama si quiere análisis LLM
3. **Sin colaboración cloud**:
   - No hay "compartir proyecto" entre correctores
   - Backups son responsabilidad del usuario
4. **Performance variable**:
   - Depende del hardware del usuario
   - No hay escalado elástico en la nube
5. **Actualizaciones manuales**:
   - Usuario debe descargar e instalar nuevas versiones

### Mitigaciones

- **Instalador self-contained**: Tauri bundle incluye Python embebido + dependencias
- **Auto-descarga de modelos**: `download_models.py` automatiza el setup inicial
- **Fallbacks**: Si LLM no disponible, sistema funciona con heurísticas
- **Backups automáticos**: Sistema crea backups antes de cada análisis
- **Documentación clara**: Manual de usuario explica requisitos de hardware

## Notas de Implementación

Ver:
- `PRIVACY.md` — política de privacidad (a crear)
- `src/narrative_assistant/core/model_manager.py` — descarga de modelos con validación
- `scripts/download_models.py` — setup inicial de modelos
- `api-server/main.py` — FastAPI corre solo en localhost
- `frontend/src/composables/useApi.ts` — todas las llamadas a localhost

**Auditoría de red**:
```bash
# Verificar que no hay llamadas externas durante análisis
grep -r "https://" src/ frontend/src/ | grep -v "localhost" | grep -v "127.0.0.1"

# Revisar imports de librerías de analytics
grep -r "sentry\|mixpanel\|analytics\|google-analytics" src/ frontend/

# Verificar que FastAPI solo escucha localhost
grep "uvicorn.run" api-server/main.py
# → host="127.0.0.1" SIEMPRE, nunca 0.0.0.0
```

## Referencias

- [Tauri Security](https://tauri.app/v1/guides/building/security/) — Arquitectura offline-first
- [GDPR Compliance](https://gdpr.eu/) — Privacidad de datos europeos
- [Grammarly Data Leak (2023)](https://thehackernews.com/2023/02/grammarly-patches-bug-that-exposed.html)
- Implementado desde v0.1.0, auditado en v0.10.9
