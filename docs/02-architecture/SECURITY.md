# Política de Seguridad - Aislamiento de Manuscritos

## Principio Fundamental

**Los manuscritos NUNCA deben salir de la máquina del usuario.**

La aplicación está diseñada para funcionar 100% offline, con la única excepción del sistema de verificación de licencias.

---

## Arquitectura de Seguridad

### Acceso a Red

| Componente | Acceso a Internet | Justificación |
|------------|------------------|---------------|
| Verificación de licencias | Sí (único) | Validar licencia activa |
| Modelos NLP (spaCy) | **NO** | Cargados desde `models/` local |
| Modelos embeddings | **NO** | Cargados desde `models/` local |
| Procesamiento de texto | **NO** | Todo local |
| Base de datos | **NO** | SQLite local |

### Medidas Implementadas

#### 1. Modelos Offline Obligatorios

```python
# embeddings.py - Variables de entorno forzadas
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
```

Si los modelos no están en `models/`, la aplicación **falla con error claro** en lugar de intentar descargarlos.

#### 2. Validación de Modelo Local

```python
# spacy_gpu.py y embeddings.py
if model_path is None:
    raise ModelNotLoadedError(
        model_name=...,
        hint="SEGURIDAD: No se permite descarga automática..."
    )
```

#### 3. Sin Dependencias de Red en Runtime

- No hay llamadas HTTP/HTTPS en el código de procesamiento
- No hay telemetría ni analytics
- No hay actualizaciones automáticas

---

## Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    MÁQUINA DEL USUARIO                      │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │Manuscrito│───▶│  Narrative   │───▶│   Alertas    │      │
│  │  .docx   │    │  Assistant   │    │  (locales)   │      │
│  └──────────┘    └──────────────┘    └──────────────┘      │
│                         │                                   │
│                         ▼                                   │
│                  ┌──────────────┐                           │
│                  │   SQLite     │                           │
│                  │   (local)    │                           │
│                  └──────────────┘                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 MODELOS NLP                          │  │
│  │  models/spacy/es_core_news_lg/                       │  │
│  │  models/embeddings/paraphrase-multilingual.../       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ ÚNICA conexión permitida
                            ▼
                    ┌──────────────┐
                    │  Servidor    │
                    │  Licencias   │
                    └──────────────┘
```

---

## Qué NO se transmite

- ❌ Contenido del manuscrito
- ❌ Metadatos del documento
- ❌ Nombres de personajes o entidades detectadas
- ❌ Alertas o inconsistencias encontradas
- ❌ Historial de análisis
- ❌ Estadísticas de uso del documento

## Qué SÍ se transmite (solo licencias)

- ✅ ID de licencia
- ✅ Verificación de validez
- ✅ (Futuro) Fecha de expiración

---

## Verificación de Cumplimiento

### Para desarrolladores

Antes de cada release, verificar:

```bash
# 1. Buscar cualquier llamada HTTP
grep -r "requests\|urllib\|http\|fetch" src/

# 2. Verificar modo offline forzado
grep -r "HF_HUB_OFFLINE\|TRANSFORMERS_OFFLINE" src/

# 3. Verificar que modelos requieren ruta local
grep -r "model_path is None" src/
```

### Checklist de seguridad

- [ ] No hay imports de `requests`, `urllib`, `httpx`, `aiohttp`
- [ ] Variables `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1` están seteadas
- [ ] Modelos fallan si no están en local (no fallback a descarga)
- [ ] No hay telemetría ni analytics
- [ ] No hay auto-updates

---

## Configuración del Usuario

El usuario NO necesita configurar nada especial. La seguridad está habilitada por defecto.

### Variables de entorno (opcionales)

```bash
# Forzar offline (ya es el default)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Deshabilitar cualquier red para modelos
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""
```

---

## Auditoría de Código

### Archivos críticos a revisar

| Archivo | Qué verificar |
|---------|--------------|
| `nlp/embeddings.py` | Variables offline, no descarga |
| `nlp/spacy_gpu.py` | Solo carga local |
| `core/config.py` | No URLs externas |
| `persistence/database.py` | Solo SQLite local |
| `parsers/*.py` | Solo lectura de archivos locales |

### Dependencias a auditar

- `sentence-transformers`: Puede descargar modelos → bloqueado con env vars
- `spacy`: Puede descargar modelos → bloqueado requiriendo ruta local
- `transformers` (indirecta): Puede descargar → bloqueado con env vars
- `torch`: No descarga por defecto ✓

---

## Respuesta a Incidentes

Si se detecta una filtración de datos:

1. **Inmediato**: Deshabilitar la funcionalidad afectada
2. **Investigar**: Determinar qué datos se filtraron
3. **Notificar**: Informar a usuarios afectados
4. **Corregir**: Parchar y verificar
5. **Documentar**: Actualizar esta política

---

## Contacto

Para reportar vulnerabilidades de seguridad, contactar al autor del TFM.
